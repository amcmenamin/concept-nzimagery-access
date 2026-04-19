These file contain example approaches to connecting to the imagery hosted on AWS.

NOTE: THIS IS NOT SYSTEM/APP CODE BUT A SET OF EXAMPLES. FEEL FREE TO COPY SECTIONS.
THIS REPO IS FOR LEARNING / DEMO PURPOSES

Other information can be found here:

ArcGIS Pro - https://storymaps.arcgis.com/collections/e6d212054d9744f399fcbed00a75ee43?item=1

Other tools / approaches - https://github.com/linz/imagery/blob/master/docs/usage.md

# LINZ AWS Data Access

This repository contains Python scripts to access public LINZ datasets hosted on AWS S3 using obstore.

- **Main script**: imagery_aws_read.py
- **Supported dataset aliases**: imagery, elevation, coastal  
- **Default imagery bucket**: nz-imagery (ap-southeast-2)
- **New feature**: Batch download all images from directories

## Requirements

- Python 3.10+
- obstore

Install dependency:

```bash
pip install obstore
```

## Basic Usage

Run with defaults:

```bash
python imagery_aws_read.py
```

## Usage Examples

### 1) Batch download all images from a directory ⭐ **NEW**

Download all image files from a directory:

```bash
python imagery_aws_read.py --download-all --output-dir my_images
```

Download with limits and progress tracking:

```bash
python imagery_aws_read.py --download-all --limit 10 --output-dir sample_images
```

Download only specific image types:

```bash
python imagery_aws_read.py --download-all --image-extensions .tif .tiff --output-dir tiff_only
```

Download from a specific path:

```bash
python imagery_aws_read.py --dataset imagery --path "taranaki/taranaki_2022-2023_0.1m/rgb/2193/" --download-all --output-dir taranaki_images
```

### 2) List tiles under a folder prefix

List all TIFF tiles or JSON metadata under the Taranaki prefix:

```bash
python imagery_aws_read.py --dataset imagery --path "taranaki/taranaki_2022-2023_0.1m/rgb/2193/" --list-prefix --endswith ".tiff"
```

```bash
python imagery_aws_read.py --dataset imagery --path "taranaki/taranaki_2022-2023_0.1m/rgb/2193/" --list-prefix --endswith ".json"
```

Limit output to first 20 matches:

```bash
python imagery_aws_read.py --dataset imagery --path "taranaki/taranaki_2022-2023_0.1m/rgb/2193/" --list-prefix --endswith ".tiff" --limit 20
```

### 3) Download a specific tile

```bash
python imagery_aws_read.py --dataset imagery --path "taranaki/taranaki_2022-2023_0.1m/rgb/2193/BH28_500_095032.tiff" --output BH28_500_095032.tiff
```

### 4) Read only the header bytes of a tile

Useful for checking Cloud Optimized GeoTIFF header bytes without downloading the full file.

```bash
python imagery_aws_read.py --dataset imagery --path "taranaki/taranaki_2022-2023_0.1m/rgb/2193/BH28_500_095032.tiff" --header-only --range-length 2048
```

### 5) Access another known dataset alias

```bash
python imagery_aws_read.py --dataset elevation --path "some/path/file.tiff" --output sample.tiff
```

### 6) Override bucket and region manually

```bash
python imagery_aws_read.py --bucket nz-imagery --region ap-southeast-2 --path "taranaki/taranaki_2022-2023_0.1m/rgb/2193/BH28_500_095032.tiff" --output tile.tiff
```

## Programmatic Usage ⭐ **NEW**

Use the convenience function in your own Python scripts:

```python
from imagery_aws_read import download_dataset_images

# Download up to 5 images from Taranaki dataset
files = download_dataset_images(
    dataset_name="imagery",
    path_prefix="taranaki/taranaki_2022-2023_0.1m/rgb/2193/",
    output_dir="downloads",
    limit=5
)
print(f"Downloaded {len(files)} images")
```

For more control, use the core functions:

```python
from imagery_aws_read import get_public_store, download_all_images, LINZ_DATASETS

# Set up store
dataset = LINZ_DATASETS["imagery"]
store = get_public_store(bucket=dataset.bucket, region=dataset.region)

# Download with custom parameters
files = download_all_images(
    store=store,
    prefix="manawatu-whanganui/",
    output_dir="custom_downloads",
    image_extensions=(".tif", ".tiff"),
    limit=10
)
```

## Command Options

**Basic Options:**
- `--dataset`: Known dataset alias (imagery, elevation, coastal)
- `--bucket`: Override bucket name
- `--region`: Override AWS region  
- `--path`: S3 object key or folder-like prefix

**Listing Options:**
- `--list-prefix`: List object keys under --path
- `--endswith`: Suffix filter for --list-prefix (example: .tiff)
- `--limit`: Max listed objects (0 = no limit)

**Single Download Options:**
- `--output`: Local filename for download mode
- `--header-only`: Read first N bytes instead of full download
- `--range-length`: Number of bytes for --header-only mode

**Batch Download Options:** ⭐ **NEW**
- `--download-all`: Download all image files from the specified path prefix
- `--output-dir`: Directory to save downloaded files (default: downloads)
- `--image-extensions`: File extensions to consider as images (default: .tif .tiff .jpg .jpeg .png)

## Features ⭐ **NEW**

✅ **Progress tracking** with download speeds  
✅ **Error handling** with detailed reporting  
✅ **Smart skipping** of existing files  
✅ **Multiple image formats** (.tif, .jpg, .png, etc.)  
✅ **Automatic directory creation**  
✅ **Download limits** and filtering  
✅ **Summary statistics**

## Example Scripts

- `download_images_example.py`: Demonstrates both simple and advanced usage of the batch download functionality

Run the example:
```bash
python download_images_example.py
```

## Technical Information

### Future Imports

The scripts use `from __future__ import annotations` which enables **postponed evaluation of type annotations**:

- **Purpose**: Type annotations are stored as strings instead of being evaluated immediately when the module is imported
- **Benefits**:
  - ✅ **Forward references work** - You can reference classes/types before they're defined
  - ✅ **Faster imports** - Type annotations aren't evaluated during import, speeding up module loading  
  - ✅ **Cleaner syntax** - No need for string quotes around forward references
  - ✅ **Better for complex type hints** - Especially helpful with generic types like `dict[str, DatasetInfo]`
- **Future compatibility**: This behavior will become the default in Python 3.11+

**Example without future import:**
```python
def process_data(items: list[DatasetInfo]) -> dict[str, DatasetInfo]:
    # ❌ Error! DatasetInfo not defined yet if this function comes before the class
    pass
```

**Example with future import:**
```python
from __future__ import annotations

def process_data(items: list[DatasetInfo]) -> dict[str, DatasetInfo]: 
    # ✅ Works! DatasetInfo will be resolved when actually needed
    pass
```

## Notes

- The script uses unsigned access (public bucket reads).
- In list mode, if --path does not end with /, the script appends / automatically.
- Paths are S3 keys, not full s3:// URLs.
- **Batch downloads**: Files are automatically skipped if they already exist locally.
- **Progress reporting**: Shows download speed, file sizes, and completion status.
- **Error resilience**: Failed downloads are logged but don't stop the process.
