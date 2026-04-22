# RGBI Processing Examples

This module contains the `NDVIProcessor` class for analyzing RGBI (Red, Green, Blue, Infrared) imagery combined with elevation data to identify and classify vegetation and other land features.

## Overview

The `NDVIProcessor` class provides comprehensive tools for processing multi-band imagery and elevation models to extract vegetation information, calculate various spectral indices, and perform height-based classification.

## Key Features

### Data Input
- **RGBI Imagery**: Red, Green, Blue, and Infrared band processing
- **DSM Integration**: Digital Surface Model for height analysis  
- **DEM Integration**: Digital Elevation Model for ground reference
- **Automatic Cropping**: Crops elevation data to match imagery bounds
- **Flexible Resizing**: Option to resize datasets to match dimensions

### Spectral Indices
- **NDVI**: Normalized Difference Vegetation Index for vegetation health
- **NDWI**: Normalized Difference Water Index for water content
- **Brightness Index**: Overall image brightness calculation
- **Urban Index**: Urban area identification using NDVI and brightness

### Classification Methods
- **Vegetation Classification**: Threshold-based vegetation identification
- **Height-Based Filtering**: Uses nDSM (normalized Digital Surface Model)
- **Slope Analysis**: Terrain slope calculation and classification
- **Urban Detection**: Urban area identification techniques

### Processing Capabilities
- **Height Tolerance**: Configurable minimum height thresholds
- **Debug Mode**: Intermediate output generation for analysis
- **Hole Filling**: Morphological operations to improve results
- **Multiple Output Formats**: Support for various classification approaches

## Main Class: NDVIProcessor

### Configuration Methods
```python
set_height_usage(use_height: bool)    # Enable/disable height-based processing
set_debug_mode(debug_mode: bool)      # Enable debug output generation
```

### Data Reading Methods
```python
read_raster_datasets()    # Read RGBI, DSM, and DEM files
read_rgbi()              # Read RGBI imagery
read_dsm()               # Read Digital Surface Model
read_dem()               # Read Digital Elevation Model
```

### Index Calculation Methods
```python
calculate_ndvi()         # Normalized Difference Vegetation Index
calculate_ndwi()         # Normalized Difference Water Index
calculate_ndsm()         # Normalized Digital Surface Model
calculate_slope()        # Terrain slope analysis
calculate_brightness_index()  # Image brightness
calculate_urban_index()  # Urban area identification
```

### Classification Methods
```python
classify_vegetation()    # Basic vegetation classification
classify()              # General threshold-based classification
select_by_height()      # Height-based feature selection
calculate_urban_threshold()  # Urban area thresholding
```

### Processing Workflows
```python
process_vegetation()     # Complete vegetation analysis workflow
process_general()       # General index processing workflow
process_slope()         # Slope analysis workflow
```

## Typical Workflow

1. **Initialize Processor**
   ```python
   processor = NDVIProcessor()
   processor.set_height_usage(True)
   processor.set_debug_mode(False)
   ```

2. **Load Data**
   ```python
   rgbi, dsm, dtm, transform = processor.read_raster_datasets(
       rgbi_path="imagery.tif",
       dsm_path="surface_model.tif", 
       dem_path="elevation_model.tif"
   )
   ```

3. **Process Vegetation**
   ```python
   processor.process_vegetation(
       rgbi, transform, dsm, dtm,
       output_path="vegetation_mask.tif",
       height_tolerance=3.5  # minimum height in meters
   )
   ```

## Dependencies

- **rasterio**: Raster data I/O and processing
- **numpy**: Numerical array operations
- **cv2 (OpenCV)**: Computer vision operations
- **skimage**: Image processing utilities
- **shapely**: Geometric operations
- **scipy**: Scientific computing functions
- **osgeo (GDAL)**: Geospatial data processing

## Input Data Requirements

- **RGBI Files**: 4-band raster (Red, Green, Blue, Infrared)
- **DSM Files**: Single-band elevation raster (surface heights)
- **DEM Files**: Single-band elevation raster (ground heights)
- **Coordinate Systems**: All inputs should have matching CRS

## Output Products

- **Vegetation Masks**: Binary rasters indicating vegetation presence
- **Index Rasters**: NDVI, NDWI, and other spectral indices
- **Classification Results**: Thematic rasters with classified features
- **Height Analysis**: nDSM and height-filtered results
- **Debug Outputs**: Intermediate processing results (when enabled)

## Use Cases

- **Forest Management**: Tree canopy analysis and health assessment
- **Urban Planning**: Vegetation mapping in urban environments  
- **Agricultural Monitoring**: Crop health and growth analysis
- **Environmental Studies**: Habitat mapping and change detection
- **Infrastructure Planning**: Vegetation clearance analysis

## Example Applications

- Identifying vegetation above 3.5 meters for utility line clearance
- Mapping urban green spaces and tree canopy coverage
- Monitoring crop health using NDVI time series
- Detecting water bodies using NDWI analysis
- Analyzing terrain characteristics for development planning

## Notes

- Height-based processing requires both DSM and DEM inputs
- Debug mode generates intermediate files for quality control
- Processing supports both vegetation and general thematic mapping
- Morphological operations help clean classification results
- Configurable thresholds allow adaptation to different environments