#!/usr/bin/env python3
"""Find and download NZ imagery intersecting a study area using obstore + GeoPandas.

This script ports the ArcPy-based workflow to:
- Read study areas from a GeoPackage layer (instead of a file geodatabase)
- Read NZ imagery catalog + item metadata from S3 using obstore
- Test intersections with GeoPandas/Shapely
- Download matching imagery assets locally

Example:
    python find_and_download_imagery.py \
        --study-gpkg c:/data/imagery/study_areas.gpkg \
        --study-layer study_area1 \
        --output-dir c:/data/imagery \
        --region wellington/wellington \
        --date 2021 \
        --gsd 0.3m \
        --rgbnir
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import posixpath

import geopandas as gpd
import obstore as obs
from obstore.store import S3Store
from shapely.geometry import box


DEFAULT_BUCKET = "nz-imagery"
DEFAULT_REGION = "ap-southeast-2"
DEFAULT_CATALOG_KEY = "catalog.json"


def get_public_store(bucket: str, region: str) -> S3Store:
    """Create an unsigned S3 store for public AWS Open Data buckets."""
    return S3Store(bucket=bucket, region=region, skip_signature=True)


def coerce_to_python_bytes(value: object) -> bytes:
    """Convert obstore byte wrappers/memory views to native Python bytes."""
    if isinstance(value, (bytes, bytearray, memoryview)):
        return bytes(value)

    to_bytes = getattr(value, "to_bytes", None)
    if callable(to_bytes):
        converted = to_bytes()
        if isinstance(converted, (bytes, bytearray, memoryview)):
            return bytes(converted)

    return bytes(value)


def read_json_from_s3(store: S3Store, key: str) -> dict:
    """Read a JSON object from S3 and return it as a dict."""
    response = obs.get(store, key)
    payload_obj = response.bytes() if hasattr(response, "bytes") else response
    payload = coerce_to_python_bytes(payload_obj)
    data = json.loads(payload.decode("utf-8"))
    return data


def get_s3_paths_from_catalog(store: S3Store, catalog_key: str) -> list[str]:
    """Extract child collection prefixes from the root NZ imagery catalog."""
    catalog_data = read_json_from_s3(store, catalog_key)

    s3_paths: list[str] = []
    for link in catalog_data.get("links", []):
        if link.get("rel") != "child":
            continue
        href = link.get("href", "")
        # Example href:
        # ./auckland/auckland-coast_2023_0.05m/rgb/2193/collection.json
        s3_path = href.replace("collection.json", "")
        s3_path = s3_path.replace("./", "").strip("/")
        if s3_path:
            s3_paths.append(s3_path)

    return sorted(set(s3_paths))


def apply_path_filters(
    s3_paths: list[str],
    region_filter: str,
    date_filter: str,
    gsd_filter: str,
    use_rgbnir: bool,
) -> list[str]:
    """Filter S3 prefixes using region/date/gsd and rgbnir flags."""
    region_filter = region_filter.lower().strip() if region_filter else ""
    date_filter = date_filter.lower().strip() if date_filter else ""
    gsd_filter = gsd_filter.lower().strip() if gsd_filter else ""

    if region_filter:
        s3_paths = [path for path in s3_paths if region_filter in path.lower()]

    if date_filter:
        s3_paths = [path for path in s3_paths if date_filter in path.lower()]

    if gsd_filter:
        s3_paths = [path for path in s3_paths if gsd_filter in path.lower()]

    if use_rgbnir:
        # Keep only RGBNIR collections. Also normalize legacy rgb paths if present.
        s3_paths = [path for path in s3_paths if "rgbnir" in path.lower()]
    else:
        # Exclude rgbnir paths if not requested.
        s3_paths = [path for path in s3_paths if "rgbnir" not in path.lower()]

    return s3_paths


def list_json_item_keys(store: S3Store, prefix: str) -> list[str]:
    """List JSON item keys directly under a collection prefix."""
    keys: list[str] = []
    for chunk in obs.list(store, prefix=prefix.rstrip("/") + "/"):
        for item in chunk:
            key = item["path"]
            if not key.endswith(".json"):
                continue
            if key.endswith("collection.json") or key.endswith("catalog.json"):
                continue
            keys.append(key)
    return keys


def build_geom_from_bbox(item_bbox: list[float]):
    """Convert [xmin, ymin, xmax, ymax] in EPSG:4326 to EPSG:2193 shapely geometry."""
    if len(item_bbox) != 4:
        raise ValueError("Expected 4-value bbox [xmin, ymin, xmax, ymax]")

    xmin, ymin, xmax, ymax = item_bbox
    bbox_geom = box(xmin, ymin, xmax, ymax)
    bbox_2193 = gpd.GeoSeries([bbox_geom], crs="EPSG:4326").to_crs("EPSG:2193").iloc[0]
    return bbox_2193


def resolve_raster_key(folder_prefix: str, href: str) -> str:
    """Resolve an item asset href to an S3 key path."""
    href = (href or "").strip()
    if not href:
        return ""

    if href.startswith("s3://"):
        # s3://bucket/key -> key
        parts = href.split("/", 3)
        if len(parts) == 4:
            return parts[3]
        return ""

    if href.startswith("/"):
        return href.lstrip("/")

    return posixpath.join(folder_prefix.strip("/"), href.lstrip("./"))


def download_key(store: S3Store, key: str, local_path: Path) -> int:
    """Download an S3 key to local filesystem. Returns bytes written."""
    data = obs.get(store, key).bytes()
    local_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_bytes(data)
    return len(data)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Find NZ imagery that intersects a study area and download matching rasters."
    )
    parser.add_argument(
        "--study-gpkg",
        default="c:\\data\\imagery\\study_areas.gpkg",
        help="Path to input study area GeoPackage.",
    )
    parser.add_argument(
        "--study-layer",
        default="study_area1",
        help="Layer name in the GeoPackage containing polygon study areas.",
    )
    parser.add_argument(
        "--output-dir",
        default="c:\\data\\imagery",
        help="Local output root directory for downloaded rasters.",
    )
    parser.add_argument("--bucket", default=DEFAULT_BUCKET, help="S3 bucket name.")
    parser.add_argument("--aws-region", default=DEFAULT_REGION, help="AWS region.")
    parser.add_argument(
        "--catalog-key",
        default=DEFAULT_CATALOG_KEY,
        help="Catalog key in bucket (default: catalog.json).",
    )
    parser.add_argument("--region", default="wellington/wellington", help="Case-insensitive path region filter.")
    parser.add_argument("--date", default="2021", help="Case-insensitive year/date path filter.")
    parser.add_argument("--gsd", default="0.3m", help="Case-insensitive GSD path filter.")
    parser.add_argument(
        "--rgbnir",
        default=True,
        help="Use only rgbnir paths.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    study_gpkg = Path(args.study_gpkg)
    output_dir = Path(args.output_dir)
    include_download_json = True

    if not study_gpkg.exists():
        raise FileNotFoundError(f"Study GeoPackage not found: {study_gpkg}")

    # Read and normalize study polygons to NZTM2000 for intersection checks.
    study_gdf = gpd.read_file(study_gpkg, layer=args.study_layer)
    if study_gdf.empty:
        print("No study polygons found in the selected layer.")
        return 0

    if study_gdf.crs is None:
        raise ValueError(
            "Study layer has no CRS. Define CRS in the GeoPackage before running this script."
        )

    study_2193 = study_gdf.to_crs("EPSG:2193")
    study_union = study_2193.geometry.union_all()

    store = get_public_store(bucket=args.bucket, region=args.aws_region)

    s3_paths = get_s3_paths_from_catalog(store, args.catalog_key)
    s3_paths = apply_path_filters(
        s3_paths=s3_paths,
        region_filter=args.region,
        date_filter=args.date,
        gsd_filter=args.gsd,
        use_rgbnir=args.rgbnir,
    )

    if not s3_paths:
        print("No catalog paths matched the provided filters.")
        return 0

    downloaded_keys: set[str] = set()
    matched_items = 0

    for folder_prefix in s3_paths:
        json_keys = list_json_item_keys(store, folder_prefix)

        for json_key in json_keys:
            try:
                item_json = read_json_from_s3(store, json_key)
            except Exception as ex:
                print(f"Skipping unreadable JSON {json_key}: {ex}")
                continue

            bbox = item_json.get("bbox")
            if not bbox:
                continue

            try:
                item_geom_2193 = build_geom_from_bbox(bbox)
            except Exception as ex:
                print(f"Skipping invalid bbox in {json_key}: {ex}")
                continue

            if not study_union.intersects(item_geom_2193):
                print (f"No intersection for {json_key}, skipping.")
                continue

            assets = item_json.get("assets", {})
            raster_href = (
                assets.get("visual", {}).get("href")
                or assets.get("image", {}).get("href")
                or assets.get("data", {}).get("href")
            )
            raster_key = resolve_raster_key(folder_prefix, raster_href)
            if not raster_key:
                continue

            if raster_key in downloaded_keys:
                continue

            output_name = os.path.basename(raster_key)
            local_dest = output_dir / folder_prefix / output_name

            try:
                print(f"Downloading {raster_key} to {local_dest}...")
                size = download_key(store, raster_key, local_dest)

                if include_download_json:
                    json_path = raster_key.replace(".tiff", ".json")
                    json_output = Path(str(local_dest).replace(".tiff", ".json"))
                    download_key(
                        store=store, key=json_path, local_path=json_output
                    )

            except Exception as ex:
                print(f"Failed download for {raster_key}: {ex}")
                continue

            downloaded_keys.add(raster_key)
            matched_items += 1
            size_mb = size / (1024 * 1024)
            print(f"Downloaded {raster_key} -> {local_dest} ({size_mb:.2f} MB)")

    print(
        f"Complete. Matched items: {matched_items}, unique rasters downloaded: {len(downloaded_keys)}"
    )
    return 0


if __name__ == "__main__":
    main()
