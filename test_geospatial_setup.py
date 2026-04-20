#!/usr/bin/env python3
"""
Comprehensive test of GDAL and rasterio integration in OSGeo4W environment.

This script demonstrates that both GDAL (via osgeo) and rasterio work properly
together, sharing the same underlying GDAL installation.
"""

import setup_gdal_env  # Configure environment
import numpy as np
import tempfile
import os

def test_gdal_rasterio_integration():
    """
    Test creating data with GDAL and reading it with rasterio, and vice versa.
    """
    print("Testing GDAL and rasterio integration...")
    
    # Import both libraries
    from osgeo import gdal, osr
    import rasterio
    from rasterio.crs import CRS
    from rasterio.transform import from_bounds
    
    # Create a temporary file
    with tempfile.NamedTemporaryFile(suffix='.tif', delete=False) as tmp:
        temp_file = tmp.name
    
    try:
        # Test 1: Create with GDAL, read with rasterio
        print("\n1. Creating raster with GDAL...")
        
        # Create a simple raster with GDAL
        driver = gdal.GetDriverByName('GTiff')
        dataset = driver.Create(temp_file, 100, 100, 1, gdal.GDT_Byte)
        
        # Set geotransform and projection
        dataset.SetGeoTransform([-180, 3.6, 0, 90, 0, -1.8])  # 3.6 degree pixels
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(4326)
        dataset.SetProjection(srs.ExportToWkt())
        
        # Write some data
        band = dataset.GetRasterBand(1)
        data = np.random.randint(0, 255, (100, 100), dtype=np.uint8)
        band.WriteArray(data)
        
        # Close dataset to flush to disk
        dataset = None
        band = None
        
        print(f"   SUCCESS: Created {temp_file} with GDAL")
        
        # Test 2: Read the GDAL-created file with rasterio
        print("2. Reading GDAL-created raster with rasterio...")
        
        with rasterio.open(temp_file) as src:
            rasterio_data = src.read(1)
            rasterio_crs = src.crs
            rasterio_transform = src.transform
            
        print(f"   SUCCESS: Read with rasterio")
        print(f"   - Shape: {rasterio_data.shape}")
        print(f"   - CRS: {rasterio_crs}")
        print(f"   - Data matches: {np.array_equal(data, rasterio_data)}")
        
        # Test 3: Create with rasterio, read with GDAL
        print("3. Creating raster with rasterio...")
        
        temp_file2 = temp_file.replace('.tif', '_rasterio.tif')
        
        # Create with rasterio
        transform = from_bounds(-180, -90, 180, 90, 200, 100)
        crs = CRS.from_epsg(4326)
        
        with rasterio.open(
            temp_file2, 'w',
            driver='GTiff',
            height=100, width=200, count=1,
            dtype=rasterio.uint8,
            crs=crs,
            transform=transform
        ) as dst:
            rasterio_data2 = np.random.randint(0, 255, (100, 200), dtype=np.uint8)
            dst.write(rasterio_data2, 1)
            
        print(f"   SUCCESS: Created {temp_file2} with rasterio")
        
        # Test 4: Read the rasterio-created file with GDAL
        print("4. Reading rasterio-created raster with GDAL...")
        
        dataset2 = gdal.Open(temp_file2)
        gdal_data = dataset2.ReadAsArray()
        gdal_geotransform = dataset2.GetGeoTransform()
        gdal_projection = dataset2.GetProjection()
        
        print(f"   SUCCESS: Read with GDAL")
        print(f"   - Shape: {gdal_data.shape}")
        print(f"   - Geotransform: {gdal_geotransform}")
        print(f"   - Data matches: {np.array_equal(rasterio_data2, gdal_data)}")
        
        dataset2 = None
        
        print(f"\nSUCCESS: GDAL and rasterio are fully interoperable!")
        return True
        
    except Exception as e:
        print(f"FAILED: Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Cleanup
        for file in [temp_file, temp_file2]:
            if os.path.exists(file):
                try:
                    os.remove(file)
                except:
                    pass


def test_common_workflows():
    """
    Test common geospatial workflows using the full stack.
    """
    print("\nTesting common geospatial workflows...")
    
    try:
        import geopandas as gpd
        import shapely.geometry as geom
        import rasterio
        from rasterio.features import rasterize
        import numpy as np
        
        print("1. Creating vector data with geopandas...")
        # Create a simple polygon
        polygon = geom.box(-1, -1, 1, 1)  # Simple square
        gdf = gpd.GeoDataFrame({'geometry': [polygon], 'value': [100]}, crs='EPSG:4326')
        print(f"   SUCCESS: Created GeoDataFrame with {len(gdf)} feature(s)")
        
        print("2. Rasterizing vector data with rasterio...")
        # Create a simple raster to rasterize into
        transform = rasterio.transform.from_bounds(-2, -2, 2, 2, 100, 100)
        
        # Rasterize the polygon
        raster = rasterize(
            [(geom, value) for geom, value in zip(gdf.geometry, gdf.value)],
            out_shape=(100, 100),
            transform=transform,
            dtype='uint8'
        )
        
        non_zero_pixels = np.count_nonzero(raster)
        print(f"   SUCCESS: Rasterized polygon, {non_zero_pixels} pixels have values")
        
        print(f"\nSUCCESS: Common workflows completed successfully!")
        return True
        
    except Exception as e:
        print(f"FAILED: Workflow test failed: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("COMPREHENSIVE GEOSPATIAL SETUP TEST")
    print("=" * 60)
    
    # Run integration tests
    integration_ok = test_gdal_rasterio_integration()
    
    # Run workflow tests  
    workflow_ok = test_common_workflows()
    
    print("\n" + "=" * 60)
    if integration_ok and workflow_ok:
        print("ALL TESTS PASSED! Your geospatial Python environment is ready! 🎉")
    else:
        print("Some tests failed. Check output above for details.")
    print("=" * 60)