"""Download catalog.json from NZ public datasets using obstore.

This script downloads the catalog.json file from the root of NZ AWS S3 buckets
to a specified output location.

Install dependency:
        pip install obstore

Examples:
        # Download imagery catalog to current directory
        python download_catalog.py --dataset imagery

        # Download to specific location
        python download_catalog.py --dataset elevation --output-dir /path/to/catalogs

        # Download with custom filename
        python download_catalog.py --dataset coastal --output imagery_catalog.json

        # Use specific bucket/region (bypass dataset presets)
        python download_catalog.py --bucket nz-imagery --region ap-southeast-2 --output my_catalog.json
"""

from __future__ import annotations
import os
import time
import argparse
from dataclasses import dataclass
from pathlib import Path

import obstore as obs
from obstore.store import S3Store


@dataclass(frozen=True)
class DatasetInfo:
    bucket: str
    region: str
    name: str


NZ_DATASETS: dict[str, DatasetInfo] = {
    "imagery": DatasetInfo(
        bucket="nz-imagery", region="ap-southeast-2", name="NZ Imagery"
    ),
    "elevation": DatasetInfo(
        bucket="nz-elevation", region="ap-southeast-2", name="NZ Elevation"
    ),
    "coastal": DatasetInfo(
        bucket="nz-coastal", region="ap-southeast-2", name="NZ Coastal"
    ),
}


def get_public_store(bucket: str, region: str) -> S3Store:
    """Create an unsigned S3 store for public AWS Open Data buckets."""
    return S3Store(
        bucket=bucket,
        region=region,
        skip_signature=True,
    )


def download_catalog(
    bucket: str, region: str, output_path: str, catalog_name: str = "catalog.json"
) -> bool:
    """Download catalog.json from the root of an S3 bucket.

    Args:
            bucket: S3 bucket name
            region: AWS region
            output_path: Local file path to save the catalog
            catalog_name: Name of the catalog file in bucket (default: catalog.json)

    Returns:
            True if successful, False otherwise
    """
    try:
        # Create the store
        store = get_public_store(bucket=bucket, region=region)

        print(f"Connecting to bucket: {bucket} (region: {region})")
        print(f"Downloading catalog: {catalog_name}")

        # Download the catalog file from the root
        start_time = time.time()
        response = obs.get(store, catalog_name)
        data = response.bytes()

        # Ensure output directory exists
        output_dir = os.path.dirname(output_path)
        if output_dir:
            Path(output_dir).mkdir(parents=True, exist_ok=True)

        # Write to file
        with open(output_path, "wb") as file_handle:
            file_handle.write(data)

        elapsed = time.time() - start_time
        size_kb = len(data) / 1024

        print(f"✓ Successfully downloaded catalog ({size_kb:.2f} KB in {elapsed:.2f}s)")
        print(f"✓ Saved to: {output_path}")

        return True

    except Exception as e:
        print(f"✗ Error downloading catalog: {e}")
        return False


def check_catalog_exists(
    bucket: str, region: str, catalog_name: str = "catalog.json"
) -> bool:
    """Check if catalog.json exists at the root of the bucket.

    Args:
            bucket: S3 bucket name
            region: AWS region
            catalog_name: Name of the catalog file to check

    Returns:
            True if catalog exists, False otherwise
    """
    try:
        store = get_public_store(bucket=bucket, region=region)

        # Try to read just the first byte to check existence
        obs.get_range(store, catalog_name, start=0, length=1)
        return True

    except Exception:
        return False


def list_available_catalogs(bucket: str, region: str) -> list[str]:
    """List JSON files at the root of the bucket (potential catalogs).

    Args:
            bucket: S3 bucket name
            region: AWS region

    Returns:
            List of JSON file names found at the root
    """
    try:
        store = get_public_store(bucket=bucket, region=region)

        # List objects with empty prefix (root level)
        json_files = []
        stream = obs.list(store, prefix="")

        for chunk in stream:
            for item in chunk:
                path = item["path"]
                # Only include JSON files at the root (no slashes in path)
                if "/" not in path and path.lower().endswith(".json"):
                    json_files.append(path)

        return json_files

    except Exception as e:
        print(f"Error listing files: {e}")
        return []


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download catalog.json from NZ public AWS datasets via obstore."
    )

    # Dataset selection
    parser.add_argument(
        "--dataset",
        choices=sorted(NZ_DATASETS.keys()),
        help="NZ dataset to download catalog from. If not specified, must provide --bucket and --region.",
    )

    # Manual bucket/region override
    parser.add_argument(
        "--bucket",
        help="S3 bucket name (overrides dataset selection).",
    )
    parser.add_argument(
        "--region",
        help="AWS region (overrides dataset selection).",
    )

    # Output options
    parser.add_argument(
        "--output",
        help="Output filename (e.g., 'imagery_catalog.json'). If not specified, uses catalog.json in output-dir.",
    )
    parser.add_argument(
        "--output-dir",
        default=".",
        help="Directory to save the catalog file (default: current directory).",
    )

    # Catalog file name
    parser.add_argument(
        "--catalog-name",
        default="catalog.json",
        help="Name of the catalog file in the bucket (default: catalog.json).",
    )

    # Utility actions
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check if catalog exists without downloading.",
    )
    parser.add_argument(
        "--list-catalogs",
        action="store_true",
        help="List all JSON files at the root of the bucket.",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    # Determine bucket and region
    if args.dataset:
        if args.dataset not in NZ_DATASETS:
            print(
                f"Error: Unknown dataset '{args.dataset}'. Available: {list(NZ_DATASETS.keys())}"
            )
            return 1
        dataset = NZ_DATASETS[args.dataset]
        bucket = args.bucket or dataset.bucket
        region = args.region or dataset.region
        dataset_name = dataset.name
    elif args.bucket and args.region:
        bucket = args.bucket
        region = args.region
        dataset_name = f"{bucket} (custom)"
    else:
        print("Error: Must specify either --dataset or both --bucket and --region")
        return 1

    print(f"Target dataset: {dataset_name}")
    print(f"Bucket: {bucket}")
    print(f"Region: {region}")
    print()

    # Handle utility actions
    if args.check:
        print(f"Checking for {args.catalog_name}...")
        if check_catalog_exists(bucket, region, args.catalog_name):
            print(f"✓ {args.catalog_name} exists in {bucket}")
        else:
            print(f"✗ {args.catalog_name} not found in {bucket}")
        return 0

    if args.list_catalogs:
        print("Searching for JSON files at bucket root...")
        catalogs = list_available_catalogs(bucket, region)
        if catalogs:
            print(f"Found {len(catalogs)} JSON file(s):")
            for catalog in catalogs:
                print(f"  - {catalog}")
        else:
            print("No JSON files found at bucket root")
        return 0

    # Determine output path
    if args.output:
        if os.path.isabs(args.output):
            output_path = args.output
        else:
            output_path = os.path.join(args.output_dir, args.output)
    else:
        # Use catalog name as filename
        filename = args.catalog_name
        output_path = os.path.join(args.output_dir, filename)

    # Download the catalog
    print(f"Output path: {output_path}")
    print()

    success = download_catalog(
        bucket=bucket,
        region=region,
        output_path=output_path,
        catalog_name=args.catalog_name,
    )

    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
