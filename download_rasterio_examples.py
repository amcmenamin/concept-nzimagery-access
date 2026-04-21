#!/usr/bin/env python3
"""Example script demonstrating how to use the rasterio-based imagery access functionality.

This script demonstrates different ways to access and process imagery data from LINZ's
AWS S3 buckets using rasterio for direct streaming access.
"""

from imagery_rasterio_read import (
    setup_aws_session,
    build_s3_url,
    read_raster_info,
    read_raster_window,
    save_raster,
    list_s3_objects,
    LINZ_DATASETS,
)


def example_metadata_only():
    """Example: Read metadata without downloading any pixel data."""
    print("=== Metadata-Only Example ===")

    # Set up AWS session for unsigned access to public data
    session = setup_aws_session()

    # Access the Taranaki imagery file
    dataset = LINZ_DATASETS["imagery"]
    path = "taranaki/taranaki_2022-2023_0.1m/rgb/2193/BQ31_10000_0101.tiff"
    s3_url = build_s3_url(dataset.bucket, path)

    print(f"Reading metadata from: {s3_url}")

    # Get metadata without loading pixel data
    info = read_raster_info(s3_url, session)

    print(f"📋 Image dimensions: {info['width']} x {info['height']} pixels")
    print(f"📊 Bands: {info['count']}")
    print(f"🗂️  Data type: {info['dtype']}")
    print(f"🗺️  CRS: {info['crs']}")
    print(f"📐 Resolution: {info['res'][0]:.6f} x {info['res'][1]:.6f} meters")
    print(f"🌍 Bounds: {info['bounds']}")

    if any(info["overviews"]):
        print(f"🔍 Available overviews: {info['overviews'][0]}")

    return info


def example_region_extract():
    """Example: Extract a specific region using bounding box."""
    print("\n=== Region Extract Example ===")

    session = setup_aws_session()
    dataset = LINZ_DATASETS["imagery"]
    path = "taranaki/taranaki_2022-2023_0.1m/rgb/2193/BQ31_10000_0101.tiff"
    s3_url = build_s3_url(dataset.bucket, path)

    # Define a bounding box (adjust these coordinates to fit your data)
    # These are example coordinates - adjust based on actual image bounds
    bbox = (1735000, 5650000, 1736000, 5651000)  # minx, miny, maxx, maxy in image CRS

    print(f"📦 Extracting region: {bbox}")
    print(f"🌐 From: {s3_url}")

    # Read only the specified region
    data, metadata = read_raster_window(s3_url, session, bbox=bbox)

    print(f"📏 Extracted shape: {data.shape}")
    print(f"📊 Data range: {data.min():.2f} to {data.max():.2f}")
    print(f"📈 Mean value: {data.mean():.2f}")

    # Save the extracted region
    output_path = "c:\\data\\imagery\\taranaki_region_extract.tiff"
    save_raster(data, metadata, output_path)
    print(f"💾 Saved extract to: {output_path}")

    return data, metadata


def example_overview_access():
    """Example: Access data at different resolution levels."""
    print("\n=== Overview Access Example ===")

    session = setup_aws_session()
    dataset = LINZ_DATASETS["imagery"]
    path = "taranaki/taranaki_2022-2023_0.1m/rgb/2193/BQ31_10000_0101.tiff"
    s3_url = build_s3_url(dataset.bucket, path)

    # Read at different overview levels
    overview_levels = [0, 1, 2]  # 0=full resolution, 1+=overview levels

    for level in overview_levels:
        print(f"\n🔍 Reading at overview level {level}:")

        try:
            data, metadata = read_raster_window(s3_url, session, overview_level=level)

            print(f"   📏 Shape: {data.shape}")
            print(
                f"   📐 Resolution: {metadata['width']} x {metadata['height']} pixels"
            )
            print(f"   💽 Memory usage: ~{data.nbytes / 1024 / 1024:.1f} MB")

            # Save the overview
            output_path = f"c:\\data\\imagery\\taranaki_overview_{level}.tiff"
            save_raster(data, metadata, output_path)
            print(f"   💾 Saved to: {output_path}")

        except Exception as e:
            print(f"   ❌ Error at level {level}: {e}")


def example_list_available_files():
    """Example: List available files in a dataset directory."""
    print("\n=== File Listing Example ===")

    dataset = LINZ_DATASETS["imagery"]
    prefix = "taranaki/taranaki_2022-2023_0.1m/rgb/2193/"

    print(f"📂 Listing files in: s3://{dataset.bucket}/{prefix}")

    # List objects with the specified prefix
    objects = list_s3_objects(dataset.bucket, prefix, dataset.region)

    # Filter for raster files
    raster_files = [obj for obj in objects if obj.lower().endswith((".tiff", ".tifff"))]

    print(f"🗂️  Found {len(raster_files)} raster files:")

    # Show first 10 files
    for i, file_path in enumerate(raster_files[:10]):
        file_name = file_path.split("/")[-1]
        print(f"   {i + 1:2d}. {file_name}")

    if len(raster_files) > 10:
        print(f"   ... and {len(raster_files) - 10} more files")

    return raster_files


def example_batch_processing():
    """Example: Process multiple files from a directory."""
    print("\n=== Batch Processing Example ===")

    session = setup_aws_session()
    dataset = LINZ_DATASETS["imagery"]
    prefix = "taranaki/taranaki_2022-2023_0.1m/rgb/2193/"

    # Get list of files
    objects = list_s3_objects(dataset.bucket, prefix, dataset.region)
    raster_files = [obj for obj in objects if obj.lower().endswith(".tiff")][
        :3
    ]  # Process first 3

    print(f"🔄 Processing {len(raster_files)} files...")

    for i, file_path in enumerate(raster_files):
        try:
            s3_url = build_s3_url(dataset.bucket, file_path)
            file_name = file_path.split("/")[-1].replace(".tiff", "")

            print(f"\n📄 Processing file {i + 1}/{len(raster_files)}: {file_name}")

            # Read metadata
            info = read_raster_info(s3_url, session)

            # Read at overview level 1 for faster processing
            data, metadata = read_raster_window(s3_url, session, overview_level=1)

            # Save processed version
            output_path = f"c:\\data\\imagery\\processed_{file_name}_overview.tiff"
            save_raster(data, metadata, output_path)

            print(f"   ✅ Processed: {info['width']}x{info['height']} -> {data.shape}")
            print(f"   💾 Saved: {output_path}")

        except Exception as e:
            print(f"   ❌ Error processing {file_path}: {e}")


def show_datasets():
    """Show available LINZ datasets."""
    print("=== Available LINZ Datasets ===")
    for name, info in LINZ_DATASETS.items():
        print(f"  📦 {name}: s3://{info.bucket}/ ({info.region})")


if __name__ == "__main__":
    print("🌟 LINZ Imagery Access Examples using Rasterio")
    print("=" * 50)

    # Show available datasets
    show_datasets()

    try:
        # Example 1: Read metadata only
        metadata = example_metadata_only()

        # Example 2: Extract a specific region
        data, meta = example_region_extract()

        # Example 3: Access different overview levels
        example_overview_access()

        # Example 4: List available files
        files = example_list_available_files()

        # Example 5: Batch processing
        example_batch_processing()

        print("\n🎉 All examples completed successfully!")
        print("\n💡 Tips:")
        print("   - Use overview levels for faster preview/analysis")
        print("   - Use bounding boxes to extract regions of interest")
        print("   - Metadata reading is very fast (no data transfer)")
        print("   - Files are streamed directly from S3 (no full download needed)")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure you have required dependencies:")
        print("   pip install rasterio boto3")
