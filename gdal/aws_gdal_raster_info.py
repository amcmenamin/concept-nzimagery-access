"""Run GDAL raster info on NZ public datasets from AWS S3.

This script uses the new GDAL raster info command (GDAL 3.11+) to analyze
imagery directly from AWS S3 without downloading. Supports both Cloud Optimized
GeoTIFFs (COGs) and other raster formats.

Install dependencies:
        pip install gdal >= 3.11

Examples:
        # Get basic raster info as text
        python aws_gdal_raster_info.py

        # Get raster info as JSON with statistics
        python aws_gdal_raster_info.py --format json --stats

        # Analyze specific file
        python aws_gdal_raster_info.py --dataset elevation --path "some/path/file.tif"

        # Get info with min-max calculations
        python aws_gdal_raster_info.py --min-max

        # Get comprehensive analysis with all metadata
        python aws_gdal_raster_info.py --format json --stats --hist --min-max

        # List available files first
        python aws_gdal_raster_info.py --list-prefix

        # Analyze multiple files from a directory
        python aws_gdal_raster_info.py --analyze-all --limit 5

        # Check if files are valid COGs
        python aws_gdal_raster_info.py --check-cog
"""

from __future__ import annotations

import argparse
import json
import pprint
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

try:
    from osgeo import gdal

    HAS_GDAL_PYTHON = True
except ImportError:
    print("Warning: GDAL Python bindings not available. Will use command line only.")
    HAS_GDAL_PYTHON = False

try:
    import obstore as obs
    from obstore.store import S3Store

    HAS_OBSTORE = True
except ImportError:
    print("Warning: obstore not available. Install with: pip install obstore")
    HAS_OBSTORE = False


@dataclass(frozen=True)
class DatasetInfo:
    bucket: str
    region: str


NZ_DATASETS: dict[str, DatasetInfo] = {
    "imagery": DatasetInfo(bucket="nz-imagery", region="ap-southeast-2"),
    "elevation": DatasetInfo(bucket="nz-elevation", region="ap-southeast-2"),
    "coastal": DatasetInfo(bucket="nz-coastal", region="ap-southeast-2"),
}


def build_s3_url(bucket: str, path: str) -> str:
    """Build S3 URL for GDAL access."""
    return f"/vsis3/{bucket}/{path}"


def build_vsi_aws_url(bucket: str, path: str, region: str) -> str:
    """Build VSI AWS URL with region for GDAL access."""
    return f"/vsiaws/{bucket}/{path}"


def setup_gdal_aws_config(region: str) -> None:
    """Configure GDAL for unsigned AWS S3 access."""
    gdal.SetConfigOption("AWS_REGION", region)
    gdal.SetConfigOption("AWS_NO_SIGN_REQUEST", "YES")
    # Don't set AWS_REQUEST_PAYER for public buckets
    gdal.SetConfigOption("GDAL_DISABLE_READDIR_ON_OPEN", "YES")
    gdal.SetConfigOption("CPL_VSIL_CURL_ALLOWED_EXTENSIONS", ".tif,.tiff")


def get_public_store(bucket: str, region: str) -> Optional[S3Store]:
    """Create an unsigned S3 store for public AWS Open Data buckets."""
    if not HAS_OBSTORE:
        return None
    return S3Store(
        bucket=bucket,
        region=region,
        skip_signature=True,
    )


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


def run_gdal_raster_info_cli(
    url: str,
    *,
    format_type: str = "text",
    min_max: bool = False,
    stats: bool = False,
    approx_stats: bool = False,
    hist: bool = False,
    checksum: bool = False,
    show_gcp: bool = True,
    show_metadata: bool = True,
    show_colortable: bool = True,
    show_filelist: bool = True,
    metadata_domain: str = "",
) -> dict[str, Any] | str:
    """Run gdal raster info using command line interface."""
    cmd = ["gdal", "raster", "info"]

    # Format option
    if format_type.lower() == "json":
        cmd.extend(["--format", "json"])

    # Analysis options
    if min_max:
        cmd.append("--min-max")
    if stats:
        cmd.append("--stats")
    if approx_stats:
        cmd.append("--approx-stats")
    if hist:
        cmd.append("--hist")
    if checksum:
        cmd.append("--checksum")

    # Suppression options
    if not show_gcp:
        cmd.append("--no-gcp")
    if not show_metadata:
        cmd.append("--no-md")
    if not show_colortable:
        cmd.append("--no-ct")
    if not show_filelist:
        cmd.append("--no-fl")

    # Metadata domain
    if metadata_domain:
        cmd.extend(["--mdd", metadata_domain])

    # Input file
    cmd.extend(["--input", url])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)

        if format_type.lower() == "json":
            return json.loads(result.stdout)
        else:
            return result.stdout

    except subprocess.CalledProcessError as e:
        print(f"Error running gdal raster info: {e}")
        print(f"Command: {' '.join(cmd)}")
        print(f"Stderr: {e.stderr}")
        return {} if format_type.lower() == "json" else ""
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON output: {e}")
        return {}
    except FileNotFoundError:
        print(
            "Error: gdal command not found. Make sure GDAL 3.11+ is installed and in PATH."
        )
        return {} if format_type.lower() == "json" else ""


def run_gdal_raster_info_python(
    url: str, region: str = "ap-southeast-2"
) -> dict[str, Any]:
    """Run gdal raster info using Python API (GDAL bindings)."""
    if not HAS_GDAL_PYTHON:
        print("GDAL Python bindings not available. Use --use-cli flag.")
        return {}

    try:
        # Setup AWS configuration for GDAL
        setup_gdal_aws_config(region)

        # Open dataset to get basic info (fallback approach)
        # Note: The new gdal.Run("raster", "info") may not be available in all GDAL versions
        dataset = gdal.Open(url)
        if not dataset:
            return {"error": f"Failed to open dataset: {url}"}

        # Build basic info dictionary manually
        info_dict = {
            "description": url,
            "driverShortName": dataset.GetDriver().ShortName,
            "driverLongName": dataset.GetDriver().LongName,
            "size": [dataset.RasterXSize, dataset.RasterYSize],
            "coordinateSystem": {"wkt": dataset.GetProjection()},
            "geoTransform": dataset.GetGeoTransform(),
            "bands": [],
        }

        # Add band information
        for i in range(1, dataset.RasterCount + 1):
            band = dataset.GetRasterBand(i)
            band_info = {
                "band": i,
                "block": band.GetBlockSize(),
                "type": gdal.GetDataTypeName(band.DataType),
                "colorInterpretation": gdal.GetColorInterpretationName(
                    band.GetColorInterpretation()
                ),
                "noDataValue": band.GetNoDataValue(),
            }
            info_dict["bands"].append(band_info)

        dataset = None  # Close dataset
        return info_dict

    except Exception as e:
        print(f"Error running GDAL Python raster info: {e}")
        return {"error": str(e)}


def check_file_is_cog(url: str, region: str = "ap-southeast-2") -> dict[str, Any]:
    """Check if a file is a valid Cloud Optimized GeoTIFF."""
    if not HAS_GDAL_PYTHON:
        print("GDAL Python bindings required for COG validation.")
        return {}

    try:
        setup_gdal_aws_config(region)

        # Open dataset to check COG properties
        dataset = gdal.Open(url)
        if not dataset:
            return {"is_cog": False, "error": "Failed to open dataset"}

        result = {
            "is_cog": True,  # We'll verify this
            "has_overviews": False,
            "is_tiled": False,
            "overview_count": 0,
            "block_size": None,
            "compression": None,
        }

        # Check if it's tiled
        band = dataset.GetRasterBand(1)
        block_x, block_y = band.GetBlockSize()
        result["block_size"] = (block_x, block_y)
        result["is_tiled"] = (
            block_x < dataset.RasterXSize or block_y < dataset.RasterYSize
        )

        # Check for overviews
        for i in range(1, dataset.RasterCount + 1):
            band = dataset.GetRasterBand(i)
            overview_count = band.GetOverviewCount()
            result["overview_count"] = max(result["overview_count"], overview_count)

        result["has_overviews"] = result["overview_count"] > 0

        # Check compression
        metadata = dataset.GetMetadata("IMAGE_STRUCTURE")
        result["compression"] = metadata.get("COMPRESSION", "None")

        # Simple COG heuristic: tiled + overviews + reasonable tile size
        result["is_cog"] = (
            result["is_tiled"]
            and result["has_overviews"]
            and 256 <= min(block_x, block_y) <= 1024
        )

        dataset = None  # Close dataset
        return result

    except Exception as e:
        return {"is_cog": False, "error": str(e)}


def analyze_raster(
    bucket: str,
    path: str,
    region: str,
    *,
    format_type: str = "text",
    min_max: bool = False,
    stats: bool = False,
    approx_stats: bool = False,
    hist: bool = False,
    use_cli: bool = False,
    check_cog: bool = False,
) -> dict[str, Any] | str:
    """Analyze a single raster file using GDAL raster info."""
    print(f"Analyzing: s3://{bucket}/{path}")

    # Build appropriate URL for GDAL
    if use_cli or not HAS_GDAL_PYTHON:
        url = build_s3_url(bucket, path)
        result = run_gdal_raster_info_cli(
            url,
            format_type=format_type,
            min_max=min_max,
            stats=stats,
            approx_stats=approx_stats,
            hist=hist,
        )
    else:
        url = build_s3_url(bucket, path)
        result = run_gdal_raster_info_python(url, region)

    # Optional COG validation
    if check_cog:
        cog_info = check_file_is_cog(url, region)
        if isinstance(result, dict):
            result["cog_validation"] = cog_info
        else:
            result += f"\n\nCOG Validation: {cog_info}"

    return result


def analyze_multiple_files(
    bucket: str,
    prefix: str,
    region: str,
    *,
    limit: int = 0,
    format_type: str = "text",
    file_extensions: tuple[str, ...] = (".tif", ".tiff"),
    **kwargs,
) -> list[dict[str, Any]]:
    """Analyze multiple raster files from an S3 prefix."""
    if not HAS_OBSTORE:
        print("obstore required for listing files. Install with: pip install obstore")
        return []

    store = get_public_store(bucket, region)
    if not store:
        return []

    print(f"Finding raster files in: s3://{bucket}/{prefix}")

    # List raster files
    all_paths = list_objects(
        store, prefix, limit=limit * 2 if limit > 0 else 0
    )  # Get extra to filter
    raster_paths = (
        [
            path
            for path in all_paths
            if any(path.lower().endswith(ext) for ext in file_extensions)
        ][:limit]
        if limit > 0
        else [
            path
            for path in all_paths
            if any(path.lower().endswith(ext) for ext in file_extensions)
        ]
    )

    if not raster_paths:
        print("No raster files found.")
        return []

    print(f"Found {len(raster_paths)} raster files to analyze")

    results = []
    for i, path in enumerate(raster_paths, 1):
        print(f"\n--- File {i}/{len(raster_paths)} ---")
        try:
            result = analyze_raster(
                bucket, path, region, format_type=format_type, **kwargs
            )

            analysis = {
                "path": path,
                "url": f"s3://{bucket}/{path}",
                "success": True,
                "info": result,
            }
            results.append(analysis)

        except Exception as e:
            print(f"Error analyzing {path}: {e}")
            analysis = {
                "path": path,
                "url": f"s3://{bucket}/{path}",
                "success": False,
                "error": str(e),
            }
            results.append(analysis)

    return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run GDAL raster info on NZ public AWS datasets.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Dataset selection
    parser.add_argument(
        "--dataset",
        choices=sorted(NZ_DATASETS.keys()),
        default="imagery",
        help="NZ dataset to access (default: imagery).",
    )
    parser.add_argument(
        "--bucket", default="", help="Override bucket name directly (optional)."
    )
    parser.add_argument(
        "--region", default="", help="Override AWS region directly (optional)."
    )
    parser.add_argument(
        "--path",
        default="taranaki/taranaki_2022-2023_0.1m/rgb/2193/BH28_500_095032.tiff",
        help="Object key/path to specific raster file.",
    )

    # Listing mode
    parser.add_argument(
        "--list-prefix",
        action="store_true",
        help="List available raster files under --path prefix.",
    )
    parser.add_argument(
        "--analyze-all",
        action="store_true",
        help="Analyze all raster files under --path prefix.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limit number of files to process (0 = no limit).",
    )

    # Output format
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text).",
    )

    # Analysis options
    parser.add_argument(
        "--min-max", action="store_true", help="Compute minimum and maximum values."
    )
    parser.add_argument(
        "--stats", action="store_true", help="Compute complete statistics."
    )
    parser.add_argument(
        "--approx-stats", action="store_true", help="Compute approximate statistics."
    )
    parser.add_argument("--hist", action="store_true", help="Compute histogram.")
    parser.add_argument(
        "--check-cog",
        action="store_true",
        help="Check if file is a valid Cloud Optimized GeoTIFF.",
    )

    # Technical options
    parser.add_argument(
        "--use-cli",
        action="store_true",
        help="Use command line gdal instead of Python bindings.",
    )
    parser.add_argument(
        "--file-extensions",
        nargs="+",
        default=[".tif", ".tiff"],
        help="File extensions to consider as rasters.",
    )

    return parser.parse_args()


def main() -> int:
    """Main entry point."""
    args = parse_args()

    # Determine bucket and region
    if args.bucket and args.region:
        bucket, region = args.bucket, args.region
    else:
        dataset_info = NZ_DATASETS[args.dataset]
        bucket = args.bucket or dataset_info.bucket
        region = args.region or dataset_info.region

    print(f"Dataset: {args.dataset}")
    print(f"Bucket: {bucket}")
    print(f"Region: {region}")
    print(f"Using: {'CLI' if args.use_cli else 'Python API'}")
    print()

    try:
        if args.list_prefix:
            # List available files
            if not HAS_OBSTORE:
                print(
                    "Error: obstore required for listing. Install with: pip install obstore"
                )
                return 1

            store = get_public_store(bucket, region)
            if not store:
                return 1

            print(f"Listing raster files in: s3://{bucket}/{args.path}")
            files = list_objects(
                store,
                args.path,
                endswith="",  # Don't filter here
                limit=args.limit,
            )

            # Filter for raster files
            raster_files = [
                f
                for f in files
                if any(f.lower().endswith(ext) for ext in args.file_extensions)
            ]

            print(f"Found {len(raster_files)} raster files:")
            for file_path in raster_files:
                print(f"  {file_path}")

        elif args.analyze_all:
            # Analyze multiple files
            results = analyze_multiple_files(
                bucket,
                args.path,
                region,
                limit=args.limit,
                format_type=args.format,
                file_extensions=tuple(args.file_extensions),
                min_max=args.min_max,
                stats=args.stats,
                approx_stats=args.approx_stats,
                hist=args.hist,
                use_cli=args.use_cli,
                check_cog=args.check_cog,
            )

            # Output results
            if args.format == "json":
                print(json.dumps(results, indent=2))
            else:
                for result in results:
                    print(f"\n{'=' * 60}")
                    print(f"File: {result['path']}")
                    if result["success"]:
                        if isinstance(result["info"], dict):
                            pprint.pprint(result["info"])
                        else:
                            print(result["info"])
                    else:
                        print(f"ERROR: {result['error']}")

        else:
            # Analyze single file
            result = analyze_raster(
                bucket,
                args.path,
                region,
                format_type=args.format,
                min_max=args.min_max,
                stats=args.stats,
                approx_stats=args.approx_stats,
                hist=args.hist,
                use_cli=args.use_cli,
                check_cog=args.check_cog,
            )

            if args.format == "json":
                if isinstance(result, dict):
                    print(json.dumps(result, indent=2))
                else:
                    print(json.dumps({"output": result}, indent=2))
            else:
                if isinstance(result, dict):
                    pprint.pprint(result)
                else:
                    print(result)

    except KeyboardInterrupt:
        print("\nAborted by user.")
        return 130
    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
