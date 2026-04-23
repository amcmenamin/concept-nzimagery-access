# AWS Connection Approaches Summary

## Overview of Three Different AWS S3 Connection Methods

The three `imagery_*.py` files demonstrate different approaches to connecting to AWS S3 buckets, each with specific advantages and use cases.

---

## 📦 **imagery_aws_read.py** - obstore Library Approach

**Library:** `obstore` (Rust-based object store library)

**Connection Method:**
```python
from obstore.store import S3Store

store = S3Store(
    bucket="nz-imagery",
    region="ap-southeast-2", 
    skip_signature=True,  # For public buckets
)
```

**Key Features:**
- ✅ **Pure object store operations** (list, get, put)
- ✅ **High performance** (Rust-based)
- ✅ **Simple API** for basic S3 operations
- ✅ **Built-in streaming** and range requests
- ❌ **No geospatial awareness** (treats files as binary blobs)

**Best for:** Bulk downloads, file management, listing operations

---

## 🗺️ **imagery_rasterio_read.py** - Rasterio + AWSSession

**Library:** `rasterio` with `AWSSession`

**Connection Method:**
```python
from rasterio.session import AWSSession

session = AWSSession(
    requester_pays=False,
    aws_unsigned=True,  # For public buckets
)

with rasterio.Env(session=session):
    with rasterio.open(s3_url) as dataset:
        # Direct geospatial operations
```

**Key Features:**
- ✅ **Geospatial-native** (understands raster formats)
- ✅ **Cloud Optimized GeoTIFF (COG) support**
- ✅ **Direct reading** without download
- ✅ **Window/bbox reading** (partial data access)
- ✅ **Rich metadata** extraction
- ❌ **Raster-specific** (won't work for non-geospatial files)

**Best for:** Geospatial analysis, COG processing, spatial data exploration

---

## 🛠️ **imagery_gdal_read.py** - GDAL Virtual File System

**Library:** `GDAL` with Virtual File System (`/vsis3/`)

**Connection Method:**
```python
from osgeo import gdal

# Configure GDAL for AWS
gdal.SetConfigOption('AWS_REGION', 'ap-southeast-2')
gdal.SetConfigOption('AWS_NO_SIGN_REQUEST', 'YES')  # Public buckets
gdal.SetConfigOption('GDAL_DISABLE_READDIR_ON_OPEN', 'YES')

# Use S3 URLs directly in GDAL functions
result = gdal.Translate(
    "local_file.tiff",
    "/vsis3/bucket/path/file.tiff"
)
```

**Key Features:**
- ✅ **Universal geospatial support** (100+ formats)
- ✅ **Transparent S3 integration** (URLs work everywhere)
- ✅ **Most comprehensive** format support
- ✅ **Both public and private** bucket support
- ✅ **CLI and Python API** options
- ❌ **Complex configuration** for advanced use cases

**Best for:** Format conversion, comprehensive geospatial operations, legacy workflows

---

## 🎯 **When to Use Each Approach**

| Use Case | Recommended Approach |
|----------|---------------------|
| **Bulk file downloads** | `obstore` (imagery_aws_read.py) |
| **Geospatial analysis of COGs** | `rasterio` (imagery_rasterio_read.py) |
| **Format conversions** | `GDAL` (imagery_gdal_read.py) |
| **Listing/managing files** | `obstore` (imagery_aws_read.py) |
| **Reading partial raster data** | `rasterio` (imagery_rasterio_read.py) |
| **Working with many formats** | `GDAL` (imagery_gdal_read.py) |
| **Private S3 buckets** | `GDAL` or `rasterio` (both support credentials) |

---

## 🔐 **Authentication Summary**

**Public Buckets (LINZ datasets):**
- **obstore**: `skip_signature=True`
- **rasterio**: `aws_unsigned=True`
- **GDAL**: `AWS_NO_SIGN_REQUEST='YES'`

**Private Buckets:**
- **obstore**: Standard AWS credentials via environment/profile
- **rasterio**: Remove `aws_unsigned=True`, use AWS credentials
- **GDAL**: Multiple options (credentials, profile, environment, IAM roles)

---

## 📊 **Performance Characteristics**

| Library | Speed | Memory Usage | CPU Usage |
|---------|-------|--------------|-----------|
| **obstore** | 🔥 Fastest | 💚 Lowest | 💚 Lowest |
| **rasterio** | ⚡ Fast | 🔶 Medium | 💚 Low |
| **GDAL** | 📈 Variable | 🔶 Medium-High | 🔶 Medium |

Choose based on your specific needs: raw performance (obstore), geospatial operations (rasterio), or comprehensive format support (GDAL).