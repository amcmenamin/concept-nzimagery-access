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
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass
import time

import pandas as pd
import geopandas as gpd
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


def get_public_store(bucket: str, region: str) -> S3Store:
    """Create an unsigned S3 store for public AWS Open Data buckets."""
    return S3Store(
        bucket=bucket,
        region=region,
        skip_signature=True,
    )


def read_collection_json(store: S3Store, collection_href: str) -> Optional[Dict[str, Any]]:
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
        clean_path = collection_href.replace('./', '').replace('\\', '/')
        
        print(f"   Reading: {clean_path}")
        
        # Get the object from S3
        response = obs.get(store, clean_path)
        content = response.bytes()
        
        # Parse JSON - handle obstore.Bytes class properly
        if hasattr(content, 'to_bytes'):
            # obstore.Bytes class - convert to standard bytes
            bytes_data = content.to_bytes()
            collection_data = json.loads(bytes_data.decode('utf-8'))
        elif isinstance(content, bytes):
            # Standard bytes object
            collection_data = json.loads(content.decode('utf-8'))
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
        if 'extent' in collection_data:
            if 'spatial' in collection_data['extent']:
                if 'bbox' in collection_data['extent']['spatial']:
                    bbox_array = collection_data['extent']['spatial']['bbox']
                    # bbox could be nested array
                    if bbox_array and len(bbox_array) > 0:
                        bbox = bbox_array[0] if isinstance(bbox_array[0], list) else bbox_array
        
        # Also check top level bbox
        if not bbox and 'bbox' in collection_data:
            bbox = collection_data['bbox']
            
        if bbox and len(bbox) >= 4:
            # Create box geometry from bbox [minx, miny, maxx, maxy]
            minx, miny, maxx, maxy = bbox[0], bbox[1], bbox[2], bbox[3]
            return box(minx, miny, maxx, maxy)
        
        return None
        
    except Exception as e:
        print(f"   Error extracting bbox: {e}")
        return None


def process_catalog_to_geoparquet(
    catalog_parquet_path: str,
    output_dir: str = "c:/temp",
    bucket: str = "nz-imagery"
) -> None:
    """
    Process catalog parquet file and create geoparquet files by type.
    
    Args:
        catalog_parquet_path: Path to the catalog parquet file
        output_dir: Directory to save geoparquet files
        bucket: S3 bucket name to read collection files from
    """
    print(f"Reading catalog from: {catalog_parquet_path}")
    
    # Read the parquet file
    if HAS_DUCKDB:
        # Use DuckDB for efficient processing
        conn = duckdb.connect()
        df = conn.execute(f"SELECT * FROM parquet_scan('{catalog_parquet_path}') ORDER BY type").df()
        conn.close()
    else:
        # Use pandas
        df = pd.read_parquet(catalog_parquet_path)
        df = df.sort_values('type')
    
    print(f"Loaded {len(df)} records from catalog")
    print(f"Data types found: {df['type'].value_counts().to_dict()}")
    
    # Get unique types
    unique_types = df['type'].unique()
    print(f"Processing {len(unique_types)} unique data types: {list(unique_types)}")
    
    # Create S3 store for reading collection files
    dataset_info = LINZ_DATASETS.get("imagery", LINZ_DATASETS["imagery"])  # Default to imagery
    store = get_public_store(bucket, dataset_info.region)
    
    # Process each type
    for data_type in unique_types:
        if not data_type:  # Skip empty types
            continue
            
        print(f"\n🔄 Processing type: '{data_type}'")
        
        # Filter data for this type
        type_df = df[df['type'] == data_type].copy()
        print(f"   Found {len(type_df)} records for type '{data_type}'")
        
        # Lists to store geometry and additional metadata
        geometries = []
        collection_metadata = []
        
        # Process each collection in this type
        for idx, row in type_df.iterrows():
            href = row['href']
            
            print(f"   Processing {idx+1}/{len(type_df)}: {row.get('title', 'Unknown')}")
            
            # Read collection.json file
            collection_data = read_collection_json(store, href)
            
            if collection_data:
                # Extract geometry from bbox
                geom = extract_bbox_geometry(collection_data)
                geometries.append(geom)
                
                # Extract additional metadata
                links_count = len(collection_data.get('links', []))
                metadata = {
                    'collection_id': collection_data.get('id', ''),
                    'collection_title': collection_data.get('title', ''),
                    'collection_description': collection_data.get('description', ''),
                    'license': collection_data.get('license', ''),
                    'links_count': links_count,
                }
                collection_metadata.append(metadata)
            else:
                # Failed to read collection
                geometries.append(None)
                collection_metadata.append({
                    'collection_id': '',
                    'collection_title': '',
                    'collection_description': '',
                    'license': '',
                    'links_count': 0,
                })
        
        # Add geometry and metadata to dataframe
        type_df['geometry'] = geometries
        
        # Add collection metadata columns
        metadata_df = pd.DataFrame(collection_metadata)
        for col in metadata_df.columns:
            type_df[col] = metadata_df[col]
        
        # Remove records without geometry
        valid_geom_mask = type_df['geometry'].notna()
        type_gdf = type_df[valid_geom_mask].copy()
        
        print(f"   Successfully processed {len(type_gdf)}/{len(type_df)} records with geometry")
        
        if len(type_gdf) > 0:
            # Convert to GeoDataFrame
            gdf = gpd.GeoDataFrame(type_gdf, geometry='geometry', crs='EPSG:4326')
            
            # Save as geoparquet
            output_filename = f"nz_imagery_collections_{data_type}.parquet"
            output_path = os.path.join(output_dir, output_filename)
            
            print(f"   Saving to: {output_path}")
            gdf.to_parquet(output_path, index=False)
            
            # Display summary
            print(f"   ✅ Saved {len(gdf)} records to {output_filename}")
            print(f"   📊 Columns: {list(gdf.columns)}")
            
            # Show sample of bbox info
            if len(gdf) > 0:
                bounds = gdf.total_bounds
                print(f"   🗺️  Spatial extent: {bounds[0]:.6f}, {bounds[1]:.6f}, {bounds[2]:.6f}, {bounds[3]:.6f}")
        else:
            print(f"   ⚠️  No valid geometries found for type '{data_type}' - skipping geoparquet creation")


def main():
    """Main processing function."""
    # Configuration
    catalog_parquet_path = r"c:\temp\nzimage_catalog_info.parquet"
    output_dir = r"c:\temp"
    
    print("=" * 60)
    print("CREATING GEOPARQUET FILES FROM CATALOG")
    print("=" * 60)
    
    # Check if catalog file exists
    if not os.path.exists(catalog_parquet_path):
        print(f"❌ Catalog file not found: {catalog_parquet_path}")
        print("Run process_catalog_to_table.py first to create the catalog parquet file.")
        return
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    start_time = time.time()
    
    try:
        process_catalog_to_geoparquet(
            catalog_parquet_path=catalog_parquet_path,
            output_dir=output_dir,
            bucket="nz-imagery"  # Could make this configurable
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