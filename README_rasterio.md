# LINZ Imagery Access with Rasterio

This script (`imagery_rasterio_read.py`) provides direct access to LINZ public datasets on AWS S3 using rasterio, without needing to download full files first. It's particularly efficient for Cloud Optimized GeoTIFFs (COGs).

## Installation

```bash
pip install rasterio boto3
```

## Basic Usage

### Get Raster Information Only
```bash
# Display metadata for a specific raster file
python imagery_rasterio_read.py --info-only

# Check elevation data
python imagery_rasterio_read.py --dataset elevation --path "auckland/auckland_2013_0.75m/dem_1m/2193/BQ31_10000_0101.tif" --info-only

# Check coastal data
python imagery_rasterio_read.py --dataset coastal --info-only --path "some/coastal/file.tif"
```

### Download Full Raster
```bash
# Download default imagery sample
python imagery_rasterio_read.py --output my_imagery.tif

# Download specific elevation file
python imagery_rasterio_read.py --dataset elevation --path "auckland/auckland_2013_0.75m/dem_1m/2193/BQ31_10000_0101.tif" --output elevation_sample.tif
```

## Advanced Spatial Operations

### Extract by Bounding Box
```bash
# Extract specific area (coordinates in raster's CRS)
python imagery_rasterio_read.py --bbox 174.7 -36.9 174.8 -36.8 --output area_extract.tif

# Extract from elevation data
python imagery_rasterio_read.py --dataset elevation --bbox 1748000 5917000 1749000 5918000 --output elevation_subset.tif

# Small area for testing
python imagery_rasterio_read.py --bbox 174.75 -36.85 174.76 -36.84 --output small_test.tif
```

### Use Overview Levels for Faster Access
```bash
# Use overview level 1 (lower resolution, faster)
python imagery_rasterio_read.py --overview-level 1 --output low_res.tif

# Use overview level 2 (even lower resolution)
python imagery_rasterio_read.py --bbox 174.7 -36.9 174.8 -36.8 --overview-level 2 --output very_low_res.tif

# Combine bbox and overview for quick previews
python imagery_rasterio_read.py --bbox 174.0 -37.0 175.0 -36.0 --overview-level 3 --output quick_preview.tif
```

## Data Discovery

### List Available Files
```bash
# List all raster files in a directory
python imagery_rasterio_read.py --list-prefix --path "taranaki/taranaki_2022-2023_0.1m/rgb/2193/"

# List elevation files for Auckland
python imagery_rasterio_read.py --dataset elevation --list-prefix --path "auckland/"

# List coastal data
python imagery_rasterio_read.py --dataset coastal --list-prefix --path ""
```

### Browse Different Datasets
```bash
# Explore imagery datasets
python imagery_rasterio_read.py --list-prefix --path "wellington/"
python imagery_rasterio_read.py --list-prefix --path "auckland/"
python imagery_rasterio_read.py --list-prefix --path "canterbury/"

# Explore elevation datasets
python imagery_rasterio_read.py --dataset elevation --list-prefix --path "wellington/"
```

## Real-World Workflows

### Quick Data Preview
```bash
# Get overview of a region at low resolution
python imagery_rasterio_read.py \
    --path "auckland/auckland_2017_0.075m/rgb/2193/" \
    --list-prefix

# Pick a file and preview it
python imagery_rasterio_read.py \
    --path "auckland/auckland_2017_0.075m/rgb/2193/BE34_10000_0405.tif" \
    --overview-level 3 \
    --output auckland_preview.tif
```

### Extract Study Area
```bash
# 1. Find your area of interest
python imagery_rasterio_read.py --list-prefix --path "wellington/"

# 2. Check the metadata
python imagery_rasterio_read.py \
    --path "wellington/wellington_2020-2021_0.05m/rgb/2193/BQ31_10000_0204.tif" \
    --info-only

# 3. Extract your study area (coordinates in NZGD2000/2193)
python imagery_rasterio_read.py \
    --path "wellington/wellington_2020-2021_0.05m/rgb/2193/BQ31_10000_0204.tif" \
    --bbox 1748500 5428500 1749500 5429500 \
    --output wellington_study_area.tif
```

### Multi-temporal Analysis Setup
```bash
# Extract same area from different time periods
python imagery_rasterio_read.py \
    --path "auckland/auckland_2017_0.075m/rgb/2193/BE34_10000_0405.tif" \
    --bbox 1756000 5925000 1757000 5926000 \
    --output auckland_2017.tif

python imagery_rasterio_read.py \
    --path "auckland/auckland_2020-2021_0.075m/rgb/2193/BE34_10000_0405.tif" \
    --bbox 1756000 5925000 1757000 5926000 \
    --output auckland_2020.tif
```

### Elevation Analysis
```bash
# Get elevation data for watershed analysis
python imagery_rasterio_read.py \
    --dataset elevation \
    --path "canterbury/canterbury_2018-2019_1m/dem_1m/2193/CB33_10000_0101.tif" \
    --bbox 1580000 5170000 1585000 5175000 \
    --output watershed_dem.tif

# Quick elevation profile
python imagery_rasterio_read.py \
    --dataset elevation \
    --path "canterbury/canterbury_2018-2019_1m/dem_1m/2193/CB33_10000_0101.tif" \
    --overview-level 1 \
    --output elevation_overview.tif
```

## Common Use Cases

### Research and Analysis
- Extract specific study areas without downloading full tiles
- Get quick previews using overview levels
- Time-series analysis by extracting same bboxes from different dates
- Elevation profiles and watershed analysis

### Data Exploration
- Browse available datasets efficiently
- Check metadata before committing to downloads
- Test processing workflows on small areas first

### Production Workflows
- Extract only needed areas to minimize storage
- Use appropriate resolution levels for different applications
- Automate extraction of multiple areas or time periods

## Performance Tips

1. **Use overviews** for quick previews and reconnaissance
2. **Extract specific bboxes** rather than downloading full tiles
3. **Check metadata first** with `--info-only` before data extraction  
4. **Use boto3 listing** to discover available files efficiently
5. **COG optimization**: Works best with Cloud Optimized GeoTIFFs

## Comparison with Original Script

| Feature | Original (obstore) | New (rasterio) |
|---------|-------------------|----------------|
| Data access | Download then process | Direct streaming access |
| Spatial subsetting | No | Yes (bbox extraction) |
| Overview levels | No | Yes (multi-resolution) |
| Memory usage | Full file in memory | Only requested data |
| Metadata access | Limited | Comprehensive geospatial metadata |
| File formats | Any | Optimized for rasters |

## Error Handling

If you encounter errors:

1. **Access errors**: Ensure you have internet connectivity and the file path exists
2. **Memory errors**: Use smaller bounding boxes or higher overview levels
3. **CRS errors**: Check coordinate system - LINZ data is typically in NZGD2000 (EPSG:2193)
4. **Timeout errors**: Try smaller areas or use overview levels

## Output Information

The script provides detailed output including:
- Raster dimensions and data types
- Coordinate reference system (CRS)
- Spatial resolution and bounds
- Data statistics (min, max, mean)
- Available overview levels
- NoData values

All extracted data is saved as compressed GeoTIFF files with proper spatial reference information preserved.