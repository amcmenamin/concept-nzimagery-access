# README_GDAL.md

# GDAL S3 Imagery Download Script

## Overview

NOTE: gdal,Translate by default will save using default compression typically no compression 

`imagery_gdal_read.py` demonstrates how to download geospatial imagery from AWS S3 using GDAL's Virtual File System (`/vsis3/`). This script supports both public NZ datasets and private S3 buckets with comprehensive authentication options.

## Features

- ✅ **Direct S3 access** using GDAL's Virtual File System  
- ✅ **Public bucket support** (NZ imagery datasets)
- ✅ **Private bucket authentication** (multiple methods)
- ✅ **Performance timing** (download duration tracking)
- ✅ **Automatic directory creation**
- ✅ **Error handling** and status reporting

## Requirements

### Dependencies
- **GDAL** >= 3.0 (with S3 support)
- **Python** >= 3.8

### Installation

```bash
# Install GDAL (choose one method):

# Option 1: conda (recommended)
conda install -c conda-forge gdal

# Option 2: pip (may require system GDAL)
pip install gdal

# Option 3: Windows (OSGeo4W)
# Download and install from: https://trac.osgeo.org/osgeo4w/
```

## Usage

### Quick Start - Public Datasets

```bash
# Download from NZ public imagery (default configuration)
python imagery_gdal_read.py
```

This downloads a sample image from the New Zealand NZ public datasets to `c:\data\imagery\image.tiff`.

### Configuration Options

The script is pre-configured for different use cases. Edit the configuration section in the file:

#### Public S3 Buckets (NZ Datasets)
```python
# Current default - works out of the box
gdal.SetConfigOption('AWS_REGION', 'ap-southeast-2')
gdal.SetConfigOption('AWS_NO_SIGN_REQUEST', 'YES')
gdal.SetConfigOption('GDAL_DISABLE_READDIR_ON_OPEN', 'YES')
```

#### Private S3 Buckets
Uncomment and configure one of these methods:

**Method A: Direct Credentials**
```python
gdal.SetConfigOption('AWS_ACCESS_KEY_ID', 'your_access_key')
gdal.SetConfigOption('AWS_SECRET_ACCESS_KEY', 'your_secret_key')
gdal.SetConfigOption('AWS_REGION', 'your-region')
```

**Method B: AWS Profile (Recommended)**
```python
gdal.SetConfigOption('AWS_PROFILE', 'your_profile_name')
gdal.SetConfigOption('AWS_REGION', 'your-region')
```

**Method C: Environment Variables**
```bash
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_DEFAULT_REGION=your_region
python imagery_gdal_read.py
```

## Available NZ Datasets

The script is configured to access New Zealand NZ public datasets:

| Dataset | Bucket | Region | Content |
|---------|--------|---------|---------|
| **Imagery** | `nz-imagery` | `ap-southeast-2` | Aerial imagery, RGB, multispectral |
| **Elevation** | `nz-elevation` | `ap-southeast-2` | Digital elevation models (DEMs) |
| **Coastal** | `nz-coastal` | `ap-southeast-2` | Coastal datasets and bathymetry |

### Example File Paths

```python
# High-resolution RGB imagery (10cm resolution)
"/vsis3/nz-imagery/taranaki/taranaki_2022-2023_0.1m/rgb/2193/BH28_500_095032.tiff"

# Elevation data
"/vsis3/nz-elevation/wellington/wellington_2019_1m/dem_1m/2193/BQ31_10000_0101.tif"

# Custom path structure: region/survey/resolution/type/grid-reference.tif
```

## Customizing the Script

### Change Source File
Edit the `gdal.Translate()` source parameter:

```python
result = gdal.Translate(
    "c:\\data\\imagery\\my_image.tiff",                    # Local destination
    "/vsis3/your-bucket/path/to/your-file.tiff"           # S3 source
)
```

### Change Output Location
```python
# Modify these variables:
output_dir = "c:\\your\\custom\\path"
output_file = "c:\\your\\custom\\path\\custom_name.tiff"
```

### Add Format Conversion
GDAL supports format conversion during download:

```python
# Convert to different format
result = gdal.Translate(
    "c:\\data\\imagery\\image.png",                       # PNG output
    "/vsis3/nz-imagery/path/to/file.tiff",               # TIFF input
    format="PNG"
)

# Add compression
result = gdal.Translate(
    "c:\\data\\imagery\\compressed.tiff",
    "/vsis3/nz-imagery/path/to/file.tiff",
    creationOptions=["COMPRESS=LZW", "TILED=YES"]
)
```

## Output Example

```
Starting download at: 2026-04-16 14:30:25
Finished download at: 2026-04-16 14:30:32
Download duration: 6.84 seconds
File downloaded successfully!
Saved to: c:\data\imagery\image.tiff
```

## Performance Optimization

### GDAL Configuration Options
```python
# Already included in the script for better performance:
gdal.SetConfigOption('GDAL_DISABLE_READDIR_ON_OPEN', 'YES')    # Skip unnecessary S3 operations
gdal.SetConfigOption('CPL_VSIL_CURL_CACHE_SIZE', '200000000')  # 200MB cache
gdal.SetConfigOption('GDAL_HTTP_TIMEOUT', '300')               # 5 minute timeout
```

### Large Files
For very large files (>1GB), consider:

```python
# Enable progress reporting
def progress_callback(complete, message, data):
    print(f"Progress: {complete*100:.1f}%")

result = gdal.Translate(
    output_file,
    source_url,
    callback=progress_callback
)
```

## Troubleshooting

### Common Issues

**"NULL pointer" Error**
- Check parameter order: `gdal.Translate(destination, source)`
- Verify AWS configuration and bucket permissions
- Ensure the source file exists

**"Permission Denied" Error**
- For public buckets: Ensure `AWS_NO_SIGN_REQUEST='YES'`
- For private buckets: Check your credentials and bucket permissions

**Slow Downloads**
- Add `GDAL_DISABLE_READDIR_ON_OPEN='YES'`
- Increase cache size: `CPL_VSIL_CURL_CACHE_SIZE='200000000'`
- Check network connection and S3 region

**File Not Found**
- Verify the S3 path exists using AWS CLI: `aws s3 ls s3://bucket/path/`
- Check bucket region matches `AWS_REGION` setting

### Debug Mode
Enable GDAL debug messages:

```python
gdal.SetConfigOption('CPL_DEBUG', 'ON')
gdal.SetConfigOption('CPL_CURL_VERBOSE', 'YES')
```

## Security Best Practices

1. **Never commit credentials** to version control
2. **Use AWS profiles** instead of hardcoded keys
3. **Set appropriate IAM permissions** (read-only for downloads)
4. **Use environment variables** for CI/CD pipelines
5. **Enable MFA** for AWS accounts with high privileges

## Related Scripts

- `imagery_rasterio_read.py` - Rasterio-based approach with geospatial analysis
- `imagery_aws_read.py` - obstore-based approach for bulk operations
- `aws_gdal_raster_info.py` - GDAL raster info for metadata analysis

## License

This script is provided as-is for educational and research purposes. NZ data is available under Creative Commons licenses - check individual dataset licenses.

## Support

For GDAL-related issues:
- [GDAL Documentation](https://gdal.org/drivers/raster/vsis3.html)
- [GDAL GitHub Issues](https://github.com/OSGeo/gdal/issues)

For NZ data questions:
- [NZ Public Datasets](https://www.linz.govt.nz/data)
- [AWS Open Data Registry](https://registry.opendata.aws/)