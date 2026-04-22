"""Read LINZ public datasets from AWS S3 using obstore.

Install dependency:
        pip install obstore

Examples:
        # List images in a directory
        python imagery_aws_read.py --list-prefix --endswith .tiff

        # Download a single file
        python imagery_aws_read.py --bucket nz-elevation --path "some/path/file.tiff" --output sample.tiff

        # Download all images from a directory
        python imagery_aws_read.py --download-all --output-dir my_images

        # Download all images with limit
        python imagery_aws_read.py --download-all --limit 10 --output-dir sample_images

        # Download specific image types only
        python imagery_aws_read.py --download-all --image-extensions .tif .jpg

        # Read just file headers
        python imagery_aws_read.py --header-only --range-length 2048

        # Use programmatically
        from imagery_aws_read import download_dataset_images
        files = download_dataset_images("imagery", "taranaki/", "downloads", limit=5)
"""

from __future__ import annotations
import os
import time
import argparse
from dataclasses import dataclass

import obstore as obs
from obstore.store import S3Store


@dataclass(frozen=True)
class DatasetInfo:
    bucket: str
    region: str


LINZ_DATASETS: dict[str, DatasetInfo] = {
    "imagery": DatasetInfo(bucket="nz-imagery", region="ap-southeast-2"),
    "elevation": DatasetInfo(bucket="nz-elevation", region="ap-southeast-2"),
    "coastal": DatasetInfo(bucket="nz-coastal", region="ap-southeast-2"),
}


def get_public_store(bucket: str, region: str) -> S3Store:
    """Create an unsigned S3 store for public AWS Open Data buckets."""
    return S3Store(
        bucket=bucket,
        region=region,
        skip_signature=True,
    )


def download_object(store: S3Store, path: str, output_file: str) -> int:
    """Download a full object from S3 to a local file.

    Returns the number of bytes written.
    """
    response = obs.get(store, path)
    data = response.bytes()
    with open(output_file, "wb") as file_handle:
        file_handle.write(data)
    return len(data)


def read_object_range(store: S3Store, path: str, length: int) -> bytes:
    """Read a byte range from the start of an object (useful for COG headers)."""
    buffer = obs.get_range(store, path, start=0, length=length)
    return bytes(buffer)


def list_objects(
    store: S3Store,
    prefix: str,
    *,
    endswith: str = "",
    limit: int = 0,
) -> list[str]:
    """List object paths under a prefix, optionally filtering by suffix and limit."""
    paths: list[str] = []
    stream = obs.list(store, prefix=prefix)

    for chunk in stream:
        for item in chunk:
            path = item["path"]
            if endswith and not path.endswith(endswith):
                continue
            paths.append(path)
            if limit > 0 and len(paths) >= limit:
                return paths

    return paths


def download_all_images(
    store: S3Store,
    prefix: str,
    output_dir: str = "downloads",
    *,
    image_extensions: tuple[str, ...] = (".tif", ".tiff", ".jpg", ".jpeg", ".png"),
    limit: int = 0,
) -> list[str]:
    """Download all image files from a given S3 prefix to a local directory.

    Args:
            store: S3Store instance
            prefix: S3 path prefix to search for images
            output_dir: Local directory to save downloaded images
            image_extensions: File extensions to consider as images
            limit: Maximum number of images to download (0 = no limit)

    Returns:
            List of successfully downloaded file paths
    """
    import os
    from pathlib import Path
    import time

    # Ensure output directory exists
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Get list of image files
    print(f"Scanning for images in: {prefix}")
    all_paths = list_objects(store=store, prefix=prefix, limit=limit)

    # Filter for image files
    image_paths = [
        path
        for path in all_paths
        if any(path.lower().endswith(ext) for ext in image_extensions)
    ]

    if not image_paths:
        print("No image files found.")
        return []

    print(f"Found {len(image_paths)} image files to download")

    downloaded_files = []
    failed_downloads = []

    for i, image_path in enumerate(image_paths, 1):
        try:
            # Extract filename from S3 path
            filename = os.path.basename(image_path)
            output_path = os.path.join(output_dir, filename)

            # Skip if file already exists
            if os.path.exists(output_path):
                print(f"[{i}/{len(image_paths)}] Skipping existing file: {filename}")
                downloaded_files.append(output_path)
                continue

            print(f"[{i}/{len(image_paths)}] Downloading: {filename}")
            start_time = time.time()

            size = download_object(
                store=store, path=image_path, output_file=output_path
            )

            elapsed = time.time() - start_time
            size_mb = size / (1024 * 1024)
            speed_mbps = size_mb / elapsed if elapsed > 0 else 0

            print(
                f"  ✓ Downloaded {size_mb:.2f} MB in {elapsed:.1f}s ({speed_mbps:.2f} MB/s)"
            )
            downloaded_files.append(output_path)

        except Exception as e:
            print(f"  ✗ Failed to download {image_path}: {e}")
            failed_downloads.append(image_path)

    print(f"\nDownload Summary:")
    print(f"  Successfully downloaded: {len(downloaded_files)} files")
    print(f"  Failed downloads: {len(failed_downloads)} files")

    if failed_downloads:
        print(f"  Failed files:")
        for failed_path in failed_downloads:
            print(f"    - {failed_path}")

    return downloaded_files


# gisborne/gisborne_2025_0.05m/rgb/2193/BG43_1000_2229.tiff
# taranaki/taranaki_2022-2023_0.1m/rgb/2193/


def download_dataset_images(
    dataset_name: str = "imagery",
    path_prefix: str = "gisborne/gisborne_2025_0.05m/rgb/2193/",
    output_dir: str = "downloads",
    limit: int = 0,
) -> list[str]:
    """Convenience function to download all images from a LINZ dataset.

    Args:
            dataset_name: One of 'imagery', 'elevation', 'coastal'
            path_prefix: S3 path prefix to search for images
            output_dir: Local directory to save downloaded images
            limit: Maximum number of images to download (0 = no limit)

    Returns:
            List of successfully downloaded file paths

    Example:
            >>> files = download_dataset_images(
            ...     dataset_name="imagery",
            ...     path_prefix="taranaki/taranaki_2022-2023_0.1m/rgb/2193/",
            ...     output_dir="my_images",
            ...     limit=10
            ... )
            >>> print(f"Downloaded {len(files)} images")
    """
    if dataset_name not in LINZ_DATASETS:
        raise ValueError(
            f"Unknown dataset: {dataset_name}. Choose from: {list(LINZ_DATASETS.keys())}"
        )

    dataset = LINZ_DATASETS[dataset_name]
    store = get_public_store(bucket=dataset.bucket, region=dataset.region)

    return download_all_images(
        store=store,
        prefix=path_prefix,
        output_dir=output_dir,
        limit=limit,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Access LINZ public AWS datasets (imagery/elevation/coastal) via obstore."
    )
    parser.add_argument(
        "--dataset",
        choices=sorted(LINZ_DATASETS.keys()),
        default="imagery",
        help="Known LINZ dataset alias (default: imagery).",
    )
    parser.add_argument(
        "--bucket",
        default="",
        help="Override bucket name directly (optional).",
    )
    parser.add_argument(
        "--region",
        default="",
        help="Override AWS region directly (optional).",
    )
    parser.add_argument(
        "--path",
        default="gisborne/gisborne_2025_0.05m/rgb/2193/BG43_1000_2229.tiff",
        help="Object key/path inside the bucket.",
    )
    parser.add_argument(
        "--list-prefix",
        action="store_true",
        help="List object keys under --path (treat --path as a prefix/folder).",
    )
    parser.add_argument(
        "--endswith",
        default="",
        help="Optional suffix filter for --list-prefix (for example: .tiff).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Optional max number of listed objects (0 means no limit).",
    )
    parser.add_argument(
        "--output",
        default="linz_sample.tiff",
        help="Local output filename for full download.",
    )
    parser.add_argument(
        "--header-only",
        action="store_true",
        help="Only read the first N bytes instead of downloading the full object.",
    )
    parser.add_argument(
        "--range-length",
        type=int,
        default=1024,
        help="Byte length for --header-only mode (default: 1024).",
    )
    parser.add_argument(
        "--download-all",
        action="store_true",
        help="Download all image files from the specified path prefix.",
    )
    parser.add_argument(
        "--output-dir",
        default="downloads",
        help="Directory to save downloaded files when using --download-all (default: downloads).",
    )
    parser.add_argument(
        "--image-extensions",
        nargs="+",
        default=[".tif", ".tiff", ".jpg", ".jpeg", ".png"],
        help="File extensions to consider as images for --download-all (default: .tiff .tiff .jpg .jpeg .png).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    dataset = LINZ_DATASETS[args.dataset]
    bucket = args.bucket or dataset.bucket
    region = args.region or dataset.region
    # path = args.path
    # output_dir = args.output_dir
    # output = args.output
    path = "wellington/wellington_2025_0.2m/rgbnir/2193/BM36_5000_1010.tiff"
    output_dir = r"c:\data\imagery"
    output = "BM36_5000_1010_RGBI.tiff"

    store = get_public_store(bucket=bucket, region=region)

    print(f"Using bucket={bucket}, region={region}")
    print(f"Target path: {path}")

    try:
        if args.download_all:
            # Download all images from the specified prefix
            prefix = path if path.endswith("/") else f"{path}/"
            print(f"Downloading all images under prefix: {prefix}")
            downloaded_files = download_all_images(
                store=store,
                prefix=prefix,
                output_dir=output_dir,
                image_extensions=tuple(args.image_extensions),
                limit=args.limit,
            )
            if downloaded_files:
                print(f"\nDownloaded files saved to: {output_dir}")
            else:
                print("No files were downloaded.")
        elif args.list_prefix:
            # Ensure folder-style prefixes also match nested keys as expected.
            prefix = path if path.endswith("/") else f"{path}/"
            print(f"Listing objects under prefix: {prefix}")
            paths = list_objects(
                store=store,
                prefix=prefix,
                endswith=args.endswith,
                limit=args.limit,
            )
            if not paths:
                print("No objects found.")
            else:
                for path in paths:
                    print(path)
                print(f"Total objects listed: {len(paths)}")
        elif args.header_only:
            header = read_object_range(store=store, path=path, length=args.range_length)
            print(f"Read {len(header)} bytes from start of object.")
            print(f"First 32 bytes (hex): {header[:32].hex()}")
        else:
            print("Starting download...")
            starttime = time.time()
            size = download_object(
                store=store, path=path, output_file=os.path.join(output_dir, output)
            )
            duration = time.time() - starttime
            print(f"Download completed in {duration:.2f} seconds")
            print(f"Successfully downloaded to {os.path.join(output_dir, output)}")
            print(f"Size: {size / (1024 * 1024):.2f} MB")
    except Exception as exc:
        print(f"Error accessing LINZ data: {exc}")
        return 1

    return 0


if __name__ == "__main__":
    main()
