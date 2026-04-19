#!/usr/bin/env python3
"""Example script demonstrating how to use the image download functionality."""

from imagery_aws_read import download_dataset_images, get_public_store, download_all_images, LINZ_DATASETS

def example_simple_download():
    """Simple example using the convenience function."""
    print("=== Simple Download Example ===")
    
    # Download up to 5 images from Taranaki dataset to 'c:\data\imagery' directory
    files = download_dataset_images(
        dataset_name="imagery",
        path_prefix="taranaki/taranaki_2022-2023_0.1m/rgb/2193/",
        output_dir="c:\\data\\imagery",
        limit=5
    )
    
    print(f"Downloaded {len(files)} files to c:\\data\\imagery/")
    return files


def example_custom_download():
    """More advanced example with custom parameters."""
    print("\n=== Custom Download Example ===")
    
    # Set up store manually for more control
    dataset = LINZ_DATASETS["imagery"]
    store = get_public_store(bucket=dataset.bucket, region=dataset.region)
    
    # Download only TIFF files with custom settings
    files = download_all_images(
        store=store,
        prefix="manawatu-whanganui/",
        output_dir="tiff_downloads",
        image_extensions=(".tif", ".tiff"),
        limit=3
    )
    
    print(f"Downloaded {len(files)} TIFF files to tiff_downloads/")
    return files


def list_available_datasets():
    """Show available datasets."""
    print("\n=== Available LINZ Datasets ===")
    for name, info in LINZ_DATASETS.items():
        print(f"  {name}: {info.bucket} ({info.region})")


if __name__ == "__main__":
    # Show what datasets are available
    list_available_datasets()
    
    try:
        # Run simple example
        example_simple_download()
        
        # Run advanced example
        example_custom_download()
        
        print("\n Examples completed successfully!")
        
    except Exception as e:
        print(f" Error: {e}")
        print("\nMake sure you have obstore installed: pip install obstore")