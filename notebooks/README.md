# Data Access Notebooks

This directory contains Jupyter notebooks demonstrating various approaches to accessing and processing geospatial data from LINZ's AWS S3 datasets.

## Notebooks Overview

### 01_imagery_aws_read.ipynb
**AWS S3 Imagery Access**
- Direct access to LINZ imagery datasets using `obstore` and AWS SDK
- Bulk download examples for offline processing
- Authentication methods for both public and private datasets
- Performance optimization for large dataset downloads

### 02_imagery_rasterio_read.ipynb  
**Rasterio Streaming Access**
- Stream imagery data directly from S3 using rasterio
- Cloud-native processing without downloading full files
- Region-of-interest extraction using bounding boxes
- Overview level access for multi-scale analysis

### 03_download_examples.ipynb
**Download Workflow Examples**
- Comprehensive download strategies and patterns
- Error handling and retry mechanisms
- Batch processing workflows
- File organization and management

### 04_ndvi_processing.ipynb
**NDVI Analysis Workflows**
- Normalized Difference Vegetation Index calculations
- Multi-temporal analysis examples
- Vegetation health monitoring techniques
- Time series processing from satellite imagery

### 05_gdal_utilities.ipynb
**GDAL Command Line Integration**
- GDAL command-line tools integration with Python
- Format conversions and optimizations
- Data validation and quality checks
- Advanced raster processing workflows

### 06_imagery_gdal_read.ipynb
**GDAL S3 Integration with Metadata Preservation**
- Direct S3 access using GDAL Virtual File System (/vsis3/)
- Smart metadata preservation during downloads
- Cloud-Optimized GeoTIFF (COG) compliance
- Performance optimization for large imagery files

## Prerequisites

### Python Dependencies
```bash
pip install jupyter
pip install rasterio
pip install obstore
pip install boto3
pip install gdal
pip install numpy
pip install matplotlib
```

### AWS Configuration
Most examples work with public LINZ datasets that don't require authentication. For private datasets:
- Configure AWS credentials via `aws configure`
- Or set environment variables: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`

## Getting Started

1. **Start Jupyter**: `jupyter notebook` or `jupyter lab`
2. **Begin with**: `01_imagery_aws_read.ipynb` for basic concepts
3. **Cloud Processing**: Use `02_imagery_rasterio_read.ipynb` for streaming workflows
4. **Advanced Features**: Try `06_imagery_gdal_read.ipynb` for metadata preservation

## Dataset Information

All notebooks use LINZ's public geospatial datasets hosted on AWS S3:
- **Imagery**: `s3://nz-imagery/` (aerial photography)
- **Elevation**: `s3://nz-elevation/` (LiDAR and DEMs)
- **Coastal**: `s3://nz-coastal/` (coastal and marine data)

## Usage Patterns

### For Exploration and Analysis
- Use `02_imagery_rasterio_read.ipynb` for interactive data exploration
- Stream data directly without downloads

### For Production Workflows
- Use `01_imagery_aws_read.ipynb` for bulk data acquisition
- Download files for offline processing

### For Advanced Processing
- Use `06_imagery_gdal_read.ipynb` for metadata-aware workflows
- Ensure Cloud-Optimized GeoTIFF compliance

## Support Files

Related Python scripts in the parent directory:
- [`imagery_aws_read.py`](../imagery_aws_read.py) - Bulk download utilities
- [`imagery_rasterio_read.py`](../imagery_rasterio_read.py) - Streaming access tools
- [`imagery_gdal_read.py`](../imagery_gdal_read.py) - GDAL-based processing
- [`aws_gdal_raster_info.py`](../aws_gdal_raster_info.py) - Raster analysis tools

## Output Directory

By default, processed files are saved to:
```
c:\data\imagery\
```

Ensure this directory exists or modify paths in notebooks as needed.