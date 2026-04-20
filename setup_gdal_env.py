"""
GDAL Environment Setup for OSGeo4W

This module configures the environment variables needed for GDAL to work
with the OSGeo4W installation on Windows.

Usage:
    Import this module at the beginning of any script that uses GDAL:
    
    import setup_gdal_env  # This will configure the environment
    from osgeo import gdal  # Now this should work
    
Or call setup_environment() explicitly:
    
    import setup_gdal_env
    setup_gdal_env.setup_environment()
    from osgeo import gdal
"""

import os


def setup_environment():
    """
    Configure environment variables for OSGeo4W GDAL installation.
    """
    osgeo_root = r"C:\Users\AMcMenamin\AppData\Local\Programs\OSGeo4W"
    
    # Set GDAL data directory
    os.environ['GDAL_DATA'] = f"{osgeo_root}\\share\\gdal"
    
    # Set PROJ library directory  
    os.environ['PROJ_LIB'] = f"{osgeo_root}\\share\\proj"
    
    # Add OSGeo4W bin to PATH (prepend to ensure it takes precedence)
    bin_path = f"{osgeo_root}\\bin"
    current_path = os.environ.get('PATH', '')
    if bin_path not in current_path:
        os.environ['PATH'] = f"{bin_path};{current_path}"
    
    print("GDAL environment configured for OSGeo4W")
    print(f"  GDAL_DATA: {os.environ['GDAL_DATA']}")
    print(f"  PROJ_LIB: {os.environ['PROJ_LIB']}")


def test_gdal_import():
    """
    Test if GDAL can be imported and basic information.
    """
    try:
        from osgeo import gdal
        print(f"SUCCESS: GDAL imported successfully!")
        print(f"  Version: {gdal.__version__}")
        print(f"  Drivers available: {gdal.GetDriverCount()}")
        return True
    except ImportError as e:
        print(f"FAILED: GDAL import failed: {e}")
        return False


def test_rasterio_import():
    """
    Test if rasterio can be imported and works with GDAL.
    """
    try:
        import rasterio
        from rasterio.crs import CRS
        print(f"SUCCESS: Rasterio imported successfully!")
        print(f"  Version: {rasterio.__version__}")
        
        # Test basic functionality
        crs = CRS.from_epsg(4326)
        print(f"  CRS test: {crs.to_string()}")
        return True
    except ImportError as e:
        print(f"FAILED: Rasterio import failed: {e}")
        return False
    except Exception as e:
        print(f"FAILED: Rasterio test failed: {e}")
        return False


def test_geospatial_stack():
    """
    Test the full geospatial Python stack.
    """
    packages = {
        'gdal': 'osgeo.gdal',
        'rasterio': 'rasterio', 
        'geopandas': 'geopandas',
        'fiona': 'fiona',
        'shapely': 'shapely'
    }
    
    print("Testing geospatial package stack:")
    success_count = 0
    
    for name, import_path in packages.items():
        try:
            module = __import__(import_path, fromlist=[''])
            if hasattr(module, '__version__'):
                version = module.__version__
            elif name == 'gdal':
                version = module.gdal.__version__ if hasattr(module, 'gdal') else 'unknown'
            else:
                version = 'unknown'
            print(f"  SUCCESS: {name} ({version})")
            success_count += 1
        except ImportError as e:
            print(f"  FAILED: {name} - {e}")
    
    print(f"\nGeospatial stack: {success_count}/{len(packages)} packages available")
    return success_count == len(packages)


# Automatically configure environment when module is imported
if __name__ == "__main__":
    setup_environment()
    print("\nTesting individual components:")
    gdal_ok = test_gdal_import() 
    rasterio_ok = test_rasterio_import()
    
    print("\nTesting full geospatial stack:")
    stack_ok = test_geospatial_stack()
    
    if gdal_ok and rasterio_ok and stack_ok:
        print(f"\nSUCCESS: All geospatial tools are working properly!")
    else:
        print(f"\nWARNING: Some issues detected. Check output above.")
else:
    # Auto-setup when imported
    setup_environment()