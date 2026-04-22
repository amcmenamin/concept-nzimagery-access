#!/usr/bin/env python3
"""
Process STAC catalog JSON to extract child collection information into a pandas table.

This script reads a STAC catalog JSON file and processes each child section to create
a structured table with extracted path components.
"""

import os
import json
import pandas as pd
import re
from pathlib import Path
from typing import List, Dict, Any

# Try to import pyarrow for parquet support
try:
    import pyarrow  # Required for parquet output

    PARQUET_AVAILABLE = True
except ImportError:
    PARQUET_AVAILABLE = False
    print("Warning: pyarrow not available. Parquet output will be skipped.")


def load_catalog_json(file_path: str) -> Dict[str, Any]:
    """Load the catalog JSON file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Catalog file not found: {file_path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in catalog file: {e}")


def extract_href_components(href: str) -> Dict[str, str]:
    """
    Extract components from href path.

    Expected format: ./path/type/crs/collection.json
    Where path contains: location_year_gsdm pattern

    Example: ./auckland/auckland-central_2023_0.06m/rgb/2193/collection.json
    """
    # Remove leading ./ and trailing /collection.json
    clean_path = href.replace("./", "").replace("/collection.json", "")

    # Split into parts
    parts = clean_path.split("/")

    if len(parts) < 3:
        # Handle cases where the structure might be different
        region = parts[0].replace("-", " ") if len(parts) > 0 else ""
        sub_region = ""
        if len(parts) > 1:
            second_part = parts[1]
            underscore_pos = second_part.find("_")
            if underscore_pos != -1:
                sub_region = second_part[:underscore_pos].replace("-", " ")
            else:
                sub_region = second_part.replace("-", " ")

        return {
            "path": clean_path,
            "region": region,
            "sub_region": sub_region,
            "type": "",
            "crs": "",
            "base_year": "",
            "year_range": "",
            "cellsize_cm": "",
            "gsd": "",
            "s3": f"s3://nz-imagery/{clean_path}/",
            "https": f"https://nz-imagery.s3.ap-southeast-2.amazonaws.com/{clean_path}/",
        }

    # Extract components
    path_components = "/".join(parts[:-2])  # Everything except type and crs
    data_type = parts[-2] if len(parts) >= 2 else ""
    crs = parts[-1] if len(parts) >= 1 else ""

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

    # Extract year and GSD from the path
    # Look for pattern like location_year_gsdm
    base_year = ""
    year_range = ""
    gsd = ""
    cellsize_cm = ""

    # Find year range (full format: 2023 or 2022-2023)
    year_range_match = re.search(r"_(\d{4}(?:-\d{4})?)(?=_)", path_components)
    if year_range_match:
        year_range = year_range_match.group(1)
        # Extract first year for base_year
        base_year = year_range.split("-")[0]

    # Find GSD (number followed by 'm' after underscore)
    gsd_match = re.search(r"_(\d+\.?\d*m)(?=/|$)", path_components)
    if gsd_match:
        gsd = gsd_match.group(1)
        # Extract just the numeric part for cellsize and convert to cm
        resolution_match = re.search(r"(\d+\.?\d*)m", gsd)
        if resolution_match:
            resolution_meters = float(resolution_match.group(1))
            cellsize_cm = str(resolution_meters * 100)

    # Create S3 path and HTTPS URL from href
    # Convert ./path/to/data/collection.json to s3://nz-imagery/path/to/data/
    s3_path = href.replace("./", "").replace("/collection.json", "")
    s3_url = f"s3://nz-imagery/{s3_path}/"
    https_url = f"https://nz-imagery.s3.ap-southeast-2.amazonaws.com/{s3_path}/"

    return {
        "path": path_components,
        "region": region,
        "sub_region": sub_region,
        "type": data_type,
        "crs": crs,
        "base_year": base_year,
        "year_range": year_range,
        "cellsize_cm": cellsize_cm,
        "gsd": gsd,
        "s3": s3_url,
        "https": https_url,
    }


def process_catalog_to_dataframe(catalog_data: Dict[str, Any]) -> pd.DataFrame:
    """
    Process catalog data to create a pandas DataFrame with extracted components.
    """
    child_records = []

    # Extract child links
    links = catalog_data.get("links", [])
    child_links = [link for link in links if link.get("rel") == "child"]

    print(f"Found {len(child_links)} child collections in catalog")

    for child in child_links:
        href = child.get("href", "")
        title = child.get("title", "")

        # Extract href components
        components = extract_href_components(href)

        # Create record
        record = {
            "href": href,
            "title": title,
            **components,  # Unpack the extracted components
        }

        child_records.append(record)

    # Create DataFrame
    df = pd.DataFrame(child_records)

    return df


def main():
    """Main processing function."""
    catalog_path = r"c:\temp\catalog.json"
    output_folder = r"c:\temp"

    print(f"Processing catalog: {catalog_path}")

    try:
        # Load catalog
        catalog_data = load_catalog_json(catalog_path)

        # Process to DataFrame
        df = process_catalog_to_dataframe(catalog_data)

        # Display results
        print(f"\nProcessed {len(df)} child collections:")
        print("\nDataFrame columns:", list(df.columns))
        print(f"\nDataFrame shape: {df.shape}")

        # Show first few records
        print("\nFirst 5 records:")
        print(df.head().to_string(index=False))

        # Show summary statistics
        print("\nData type distribution:")
        print(df["type"].value_counts())

        print("\nCRS distribution:")
        print(df["crs"].value_counts())

        print("\nYear distribution:")
        print(df["base_year"].value_counts())

        # Save to CSV and Parquet for further analysis
        csv_output_path = os.path.join(output_folder, "nzimage_catalog_info.csv")
        parquet_output_path = os.path.join(
            output_folder, "nzimage_catalog_info.parquet"
        )

        df.to_csv(csv_output_path, index=False)
        print("\nSaved processed catalog to:")
        print(f"  CSV: {csv_output_path}")

        if PARQUET_AVAILABLE:
            df.to_parquet(parquet_output_path, index=False)
            print(f"  Parquet: {parquet_output_path}")
        else:
            print("  Parquet: Skipped (pyarrow not available)")

        return df

    except Exception as e:
        print(f"Error processing catalog: {e}")
        return None


if __name__ == "__main__":
    df = main()
