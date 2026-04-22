#!/usr/bin/env python3
"""
Create GeoParquet files from catalog data by reading collection.json files and extracting bbox geometry.

This script:
1. Reads the parquet catalog ordered by type
2. For each unique type, creates a new geoparquet file
3. Reads collection.json files from S3 to get bbox information
4. Creates geometry from bbox and adds to the dataframe
5. Saves as geoparquet files

Dependencies:
    pip install obstore pandas pyarrow geopandas shapely

Usage:
    python create_collection_geoparquet.py
"""

from __future__ import annotations

import json
import os
from typing import Dict, Any, Optional
from dataclasses import dataclass
import time

import setup_gdal_env  # Configure GDAL environment
import pandas as pd
from shapely.geometry import box
import obstore as obs
from obstore.store import S3Store

# Try to import optional dependencies
try:
    import duckdb

    HAS_DUCKDB = True
except ImportError:
    HAS_DUCKDB = False
    print("Info: DuckDB not available. Using pandas for processing.")


@dataclass(frozen=True)
class DatasetInfo:
    bucket: str
    region: str


# LINZ dataset configurations
LINZ_DATASETS: Dict[str, DatasetInfo] = {
    "imagery": DatasetInfo(bucket="nz-imagery", region="ap-southeast-2"),
    "elevation": DatasetInfo(bucket="nz-elevation", region="ap-southeast-2"),
    "coastal": DatasetInfo(bucket="nz-coastal", region="ap-southeast-2"),
}


def extract_path_components(href: str) -> Dict[str, str]:
    """
    Extract region and sub_region components from href path.

    Args:
        href: Collection href path (e.g., "./bay-of-plenty/bay-of-plenty_2015-2016_0.125m/rgb/2193/collection.json")

    Returns:
        Dictionary with region and sub_region fields
    """
    # Remove leading ./ and trailing /collection.json
    clean_path = href.replace("./", "").replace("/collection.json", "")

    # Split into parts
    parts = clean_path.split("/")

    # Extract region from the first part of the path (left of first /)
    region = parts[0].replace("-", " ") if len(parts) > 0 else ""

    # Extract sub_region from the second part of the path (after first / to first _)
    sub_region = ""
    if len(parts) > 1:
        second_part = parts[1]
        underscore_pos = second_part.find("_")
        if underscore_pos != -1:
            sub_region = second_part[:underscore_pos].replace("-", " ")
        else:
            sub_region = second_part.replace("-", " ")

    return {"region": region, "sub_region": sub_region}


def get_public_store(bucket: str, region: str) -> S3Store:
    """Create an unsigned S3 store for public AWS Open Data buckets."""
    return S3Store(
        bucket=bucket,
        region=region,
        skip_signature=True,
    )


def read_collection_json(
    store: S3Store, collection_href: str
) -> Optional[Dict[str, Any]]:
    """
    Read and parse a collection.json file from S3.

    Args:
        store: S3Store instance
        collection_href: Relative path to collection.json (e.g., "./auckland/auckland-central_2023_0.06m/rgb/2193/collection.json")

    Returns:
        Parsed JSON data or None if failed
    """
    try:
        # Clean the href path
        clean_path = collection_href.replace("./", "").replace("\\", "/")

        print(f"   Reading: {clean_path}")
        if "rgbnir" in clean_path:
            print("  RGBNIR files")

        # Get the object from S3
        response = obs.get(store, clean_path)
        content = response.bytes()

        # Parse JSON - handle obstore.Bytes class properly
        if hasattr(content, "to_bytes"):
            # obstore.Bytes class - convert to standard bytes
            bytes_data = content.to_bytes()
            collection_data = json.loads(bytes_data.decode("utf-8"))
        elif isinstance(content, bytes):
            # Standard bytes object
            collection_data = json.loads(content.decode("utf-8"))
        else:
            # Fallback for other types
            collection_data = json.loads(str(content))
        return collection_data

    except Exception as e:
        print(f"   Error reading {collection_href}: {e}")
        return None


def extract_bbox_geometry(collection_data: Dict[str, Any]) -> Optional[Any]:
    """
    Extract bbox from collection data and create a Shapely geometry.

    Args:
        collection_data: Parsed collection.json data

    Returns:
        Shapely geometry object or None
    """
    try:
        # Look for bbox in the collection data
        bbox = None

        # Check different possible locations for bbox
        if "extent" in collection_data:
            if "spatial" in collection_data["extent"]:
                if "bbox" in collection_data["extent"]["spatial"]:
                    bbox_array = collection_data["extent"]["spatial"]["bbox"]
                    # bbox could be nested array
                    if bbox_array and len(bbox_array) > 0:
                        bbox = (
                            bbox_array[0]
                            if isinstance(bbox_array[0], list)
                            else bbox_array
                        )

        # Also check top level bbox
        if not bbox and "bbox" in collection_data:
            bbox = collection_data["bbox"]

        if bbox and len(bbox) >= 4:
            # Create box geometry from bbox [minx, miny, maxx, maxy]
            minx, miny, maxx, maxy = bbox[0], bbox[1], bbox[2], bbox[3]
            return box(minx, miny, maxx, maxy)

        return None

    except Exception as e:
        print(f"   Error extracting bbox: {e}")
        return None


def process_catalog_to_csv(
    catalog_parquet_path: str, output_dir: str = "c:/temp", bucket: str = "nz-imagery"
) -> None:
    """
    Process catalog parquet file and create CSV files by type.

    Args:
        catalog_parquet_path: Path to the catalog parquet file
        output_dir: Directory to save CSV files
        bucket: S3 bucket name to read collection files from
    """
    print(f"Reading catalog from: {catalog_parquet_path}")

    # Read the parquet file
    if HAS_DUCKDB:
        # Use DuckDB for efficient processing
        conn = duckdb.connect()
        df = conn.execute(
            f"SELECT * FROM parquet_scan('{catalog_parquet_path}') ORDER BY type"
        ).df()
        conn.close()
    else:
        # Use pandas
        df = pd.read_parquet(catalog_parquet_path)
        df = df.sort_values("type")

    print(f"Loaded {len(df)} records from catalog")
    print(f"Data types found: {df['type'].value_counts().to_dict()}")

    # Get unique types
    unique_types = df["type"].unique()
    print(f"Processing {len(unique_types)} unique data types: {list(unique_types)}")

    # Create S3 store for reading collection files
    dataset_info = LINZ_DATASETS.get(
        "imagery", LINZ_DATASETS["imagery"]
    )  # Default to imagery
    store = get_public_store(bucket, dataset_info.region)

    # Process each type
    for data_type in unique_types:
        if not data_type:  # Skip empty types
            continue

        print(f"\n🔄 Processing type: '{data_type}'")

        # Filter data for this type
        type_df = df[df["type"] == data_type].copy().reset_index(drop=True)

        print(f"   Found {len(type_df)} records for type '{data_type}'")

        # Lists to store additional metadata
        collection_metadata = []

        # Process each collection in this type
        for idx, row in type_df.iterrows():
            href = row["href"]

            print(
                f"   Processing {idx + 1}/{len(type_df)}: {row.get('title', 'Unknown')}"
            )

            # Read collection.json file
            collection_data = read_collection_json(store, href)

            if collection_data:
                # Extract path components for region and sub_region
                path_components = extract_path_components(href)

                # Extract additional metadata
                links_count = len(collection_data.get("links", []))
                metadata = {
                    "region": path_components["region"],
                    "sub_region": path_components["sub_region"],
                    "collection_id": collection_data.get("id", ""),
                    "collection_title": collection_data.get("title", ""),
                    "collection_description": collection_data.get("description", ""),
                    "license": collection_data.get("license", ""),
                    "image_count": links_count,
                }
                collection_metadata.append(metadata)
            else:
                # Failed to read collection - extract what we can from href
                path_components = extract_path_components(href)
                collection_metadata.append(
                    {
                        "region": path_components["region"],
                        "sub_region": path_components["sub_region"],
                        "collection_id": "",
                        "collection_title": "",
                        "collection_description": "",
                        "license": "",
                        "image_count": 0,
                    }
                )

        # Add collection metadata columns (skip geometry)
        metadata_df = pd.DataFrame(collection_metadata)
        for col in metadata_df.columns:
            type_df[col] = metadata_df[col]

        # Filter out records that failed to process (where collection_metadata is empty)
        valid_records_mask = type_df["collection_id"] != ""
        final_df = type_df[valid_records_mask].copy()

        print(
            f"   Successfully processed {len(final_df)}/{len(type_df)} records with metadata"
        )

        if len(final_df) > 0:
            # Save as CSV
            output_filename = f"nz_imagery_collections_{data_type}.csv"
            output_path = os.path.join(output_dir, output_filename)

            print(f"   Saving to: {output_path}")
            final_df.to_csv(output_path, index=False)

            # Display summary
            print(f"   ✅ Saved {len(final_df)} records to {output_filename}")
            print(f"   📊 Columns: {list(final_df.columns)}")
        else:
            print(
                f"   ⚠️  No valid metadata found for type '{data_type}' - skipping CSV creation"
            )


def main():
    """Main processing function."""
    # Configuration
    catalog_parquet_path = r"c:\temp\nzimage_catalog_info.parquet"
    output_dir = r"c:\temp"

    print("=" * 60)
    print("CREATING CSV FILES FROM CATALOG")
    print("=" * 60)

    # Check if catalog file exists
    if not os.path.exists(catalog_parquet_path):
        print(f"❌ Catalog file not found: {catalog_parquet_path}")
        print(
            "Run process_catalog_to_parquet.py first to create the catalog parquet file."
        )
        return

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    start_time = time.time()

    try:
        process_catalog_to_csv(
            catalog_parquet_path=catalog_parquet_path,
            output_dir=output_dir,
            bucket="nz-imagery",  # Could make this configurable
        )

        elapsed_time = time.time() - start_time
        print(f"\n✅ Processing completed in {elapsed_time:.2f} seconds")
        print(f"📁 GeoParquet files saved to: {output_dir}")

    except Exception as e:
        print(f"❌ Error during processing: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
