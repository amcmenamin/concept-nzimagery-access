#!/usr/bin/env python3
"""
Process collection CSV files to read individual item JSON files and create geoparquet.

This script:
1. Reads the CSV file created by create_collection_geoparquet.py
2. For each collection, reads the collection.json file
3. Finds all links with "rel": "item"
4. Reads each item JSON file and extracts metadata and bbox
5. Converts bbox to geometry and creates a GeoDataFrame
6. Exports as geoparquet for spatial analysis

Dependencies:
    pip install pandas geopandas shapely obstore

Usage:
    python process_collection_items.py
"""

from __future__ import annotations

import json
import os
import pandas as pd
from pathlib import Path
from typing import Dict, Any, Optional, List
import time
from urllib.parse import urlparse

import setup_gdal_env  # Configure GDAL environment
import geopandas as gpd
from shapely.geometry import box
import obstore as obs
from obstore.store import S3Store


def get_public_store(bucket: str, region: str = "ap-southeast-2") -> S3Store:
    """Create an unsigned S3 store for public AWS Open Data buckets."""
    return S3Store(
        bucket=bucket,
        region=region,
        skip_signature=True,
    )


def read_json_from_s3(store: S3Store, s3_path: str) -> Optional[Dict[str, Any]]:
    """
    Read and parse a JSON file from S3.

    Args:
        store: S3Store instance
        s3_path: S3 path to the JSON file

    Returns:
        Parsed JSON data or None if failed
    """
    try:
        print(f"      Reading: {s3_path}")

        # Get the object from S3
        response = obs.get(store, s3_path)
        content = response.bytes()

        # Parse JSON - handle obstore.Bytes class properly
        if hasattr(content, "to_bytes"):
            # obstore.Bytes class - convert to standard bytes
            bytes_data = content.to_bytes()
            json_data = json.loads(bytes_data.decode("utf-8"))
        elif isinstance(content, bytes):
            # Standard bytes object
            json_data = json.loads(content.decode("utf-8"))
        else:
            # Fallback for other types
            json_data = json.loads(str(content))

        return json_data

    except Exception as e:
        print(f"      Error reading {s3_path}: {e}")
        return None


def url_to_s3_path(url: str) -> str:
    """Convert HTTPS URL to S3 path."""
    # Extract path from URL
    parsed = urlparse(url)
    # Remove leading slash
    return parsed.path.lstrip("/")


def process_collection_items(
    collection_href: str, store: S3Store
) -> List[Dict[str, Any]]:
    """
    Process a single collection to extract all item metadata.

    Args:
        collection_href: URL to the collection.json file
        store: S3Store instance

    Returns:
        List of item metadata dictionaries
    """
    items_data = []

    try:
        # Convert URL to S3 path
        collection_s3_path = url_to_s3_path(collection_href)

        print(f"   Processing collection: {collection_s3_path}")

        # Read collection.json
        collection_data = read_json_from_s3(store, collection_s3_path)
        if not collection_data:
            return items_data

        # Find item links
        links = collection_data.get("links", [])
        item_links = [link for link in links if link.get("rel") == "item"]

        print(f"   Found {len(item_links)} item links")

        # Process each item
        for idx, item_link in enumerate(item_links, 1):
            item_href = item_link.get("href", "")
            if not item_href:
                continue

            print(f"   Processing item {idx}/{len(item_links)}: {item_href}")

            # Convert relative URL to absolute if needed
            if item_href.startswith("./"):
                # Resolve relative to collection directory
                collection_dir = "/".join(collection_s3_path.split("/")[:-1])
                item_s3_path = item_href.replace("./", f"{collection_dir}/")
            elif item_href.startswith("http"):
                # Already absolute URL
                item_s3_path = url_to_s3_path(item_href)
            else:
                # Assume relative to collection directory
                collection_dir = "/".join(collection_s3_path.split("/")[:-1])
                item_s3_path = f"{collection_dir}/{item_href}"

            # Read item JSON
            item_data = read_json_from_s3(store, item_s3_path)
            if item_data:
                # Extract bbox and create geometry
                bbox = item_data.get("bbox", [])
                geometry = None
                if bbox and len(bbox) >= 4:
                    # Create box geometry from bbox [minx, miny, maxx, maxy]
                    minx, miny, maxx, maxy = bbox[0], bbox[1], bbox[2], bbox[3]
                    geometry = box(minx, miny, maxx, maxy)

                # Extract relevant metadata from item
                item_metadata = {
                    "collection_href": collection_href,
                    "item_href": item_href,
                    "item_id": item_data.get("id", ""),
                    "item_type": item_data.get("type", ""),
                    "stac_version": item_data.get("stac_version", ""),
                    "datetime": item_data.get("properties", {}).get("datetime", ""),
                    "start_datetime": item_data.get("properties", {}).get(
                        "start_datetime", ""
                    ),
                    "end_datetime": item_data.get("properties", {}).get(
                        "end_datetime", ""
                    ),
                    "gsd": item_data.get("properties", {}).get("gsd", ""),
                    "proj_epsg": item_data.get("properties", {}).get("proj:epsg", ""),
                    "proj_transform": str(
                        item_data.get("properties", {}).get("proj:transform", [])
                    ),
                    "proj_shape": str(
                        item_data.get("properties", {}).get("proj:shape", [])
                    ),
                    "geometry": geometry,
                }

                # Extract bbox if available
                bbox = item_data.get("bbox", [])
                if bbox and len(bbox) >= 4:
                    item_metadata.update(
                        {
                            "bbox_minx": bbox[0],
                            "bbox_miny": bbox[1],
                            "bbox_maxx": bbox[2],
                            "bbox_maxy": bbox[3],
                        }
                    )
                else:
                    item_metadata.update(
                        {
                            "bbox_minx": None,
                            "bbox_miny": None,
                            "bbox_maxx": None,
                            "bbox_maxy": None,
                        }
                    )

                # Extract assets info
                assets = item_data.get("assets", {})
                item_metadata["asset_count"] = len(assets)

                # List asset keys (e.g., visual, red, green, blue, nir)
                item_metadata["asset_types"] = ",".join(assets.keys()) if assets else ""

                items_data.append(item_metadata)

    except Exception as e:
        print(f"   Error processing collection {collection_href}: {e}")

    return items_data


def main():
    """Main processing function."""
    # Configuration
    csv_input_path = r"c:\temp\nz_imagery_collections_rgbnir.csv"  # Change as needed
    output_dir = r"c:\temp"

    print("=" * 60)
    print("PROCESSING COLLECTION ITEMS")
    print("=" * 60)

    # Check if CSV file exists
    if not os.path.exists(csv_input_path):
        print(f"❌ CSV file not found: {csv_input_path}")
        print(
            "Run create_collection_geoparquet.py first to create the collection CSV files."
        )
        return

    # Load the CSV file
    print(f"Loading CSV: {csv_input_path}")
    df = pd.read_csv(csv_input_path)
    print(f"Loaded {len(df)} collections")

    # Create S3 store
    store = get_public_store("nz-imagery")

    # Process collections
    all_items_data = []

    start_time = time.time()

    for idx, row in df.iterrows():
        href = row["href"]
        collection_title = row.get("collection_title", "Unknown")

        print(f"\n🔄 Processing collection {idx + 1}/{len(df)}: {collection_title}")

        # Convert href to full URL if needed
        if href.startswith("./"):
            collection_url = f"https://nz-imagery.s3.ap-southeast-2.amazonaws.com/{href.replace('./', '')}"
        else:
            collection_url = href

        # Process this collection's items
        items_data = process_collection_items(collection_url, store)

        # Add collection context to each item
        for item in items_data:
            item.update(
                {
                    "collection_id": row.get("collection_id", ""),
                    "collection_title": row.get("collection_title", ""),
                    "region": row.get("region", ""),
                    "sub_region": row.get("sub_region", ""),
                    "type": row.get("type", ""),
                    "crs": row.get("crs", ""),
                }
            )

        all_items_data.extend(items_data)
        print(f"   Collected {len(items_data)} items from this collection")

    # Create GeoDataFrame from all items
    if all_items_data:
        # Create DataFrame first
        items_df = pd.DataFrame(all_items_data)

        # Filter out items without geometry
        valid_geom_mask = items_df["geometry"].notna()
        items_with_geom = items_df[valid_geom_mask].copy()

        print(
            f"\n📊 Found {len(items_with_geom)}/{len(items_df)} items with valid geometry"
        )

        if len(items_with_geom) > 0:
            # Create GeoDataFrame
            geo_df = gpd.GeoDataFrame(
                items_with_geom, geometry="geometry", crs="EPSG:4326"
            )

            # Save results as geoparquet
            output_filename = f"nz_imagery_items_{Path(csv_input_path).stem}.parquet"
            output_path = os.path.join(output_dir, output_filename)

            print(f"📊 Saving {len(geo_df)} items with geometry to: {output_path}")
            geo_df.to_parquet(output_path, index=False)

            # Also save CSV without geometry for reference
            csv_output_filename = f"nz_imagery_items_{Path(csv_input_path).stem}.csv"
            csv_output_path = os.path.join(output_dir, csv_output_filename)

            # Create CSV version without geometry column
            csv_df = items_df.drop(columns=["geometry"])
            csv_df.to_csv(csv_output_path, index=False)
            print(f"📄 Also saved CSV version to: {csv_output_path}")

            # Show spatial summary
            bounds = geo_df.total_bounds
            print(
                f"🗺️  Spatial extent: {bounds[0]:.6f}, {bounds[1]:.6f}, {bounds[2]:.6f}, {bounds[3]:.6f}"
            )

        else:
            print("⚠️ No items with valid geometry found for geoparquet export")
            # Still save CSV version
            csv_output_filename = f"nz_imagery_items_{Path(csv_input_path).stem}.csv"
            csv_output_path = os.path.join(output_dir, csv_output_filename)
            items_df.drop(columns=["geometry"]).to_csv(csv_output_path, index=False)
            print(f"📄 Saved CSV version without geometry to: {csv_output_path}")

        # Show summary
        elapsed_time = time.time() - start_time
        print(f"\n✅ Processing completed in {elapsed_time:.2f} seconds")
        print(f"📈 Total items processed: {len(items_df)}")
        print(f"📋 Columns: {list(items_df.columns)}")

        # Show sample statistics
        print("\n📊 Summary Statistics:")
        if "item_type" in items_df.columns:
            print(f"   Item types: {items_df['item_type'].value_counts().to_dict()}")
        if "region" in items_df.columns:
            print(f"   Regions: {items_df['region'].value_counts().to_dict()}")
        if "asset_count" in items_df.columns:
            print(f"   Average assets per item: {items_df['asset_count'].mean():.1f}")

    else:
        print("⚠️ No items were processed successfully")


if __name__ == "__main__":
    main()
