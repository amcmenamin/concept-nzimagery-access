"""
GDAL Environment Setup for OSGeo4W

This module configures the environment variables needed for GDAL to work
with the OSGeo4W installation on Windows. It resolves conflicts with
conda environments and other GDAL installations (e.g., PostgreSQL).

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
import sys
from pathlib import Path


def find_osgeo4w_installation():
    """
    Find OSGeo4W installation directory automatically.
    """
    possible_locations = [
        Path.home() / "AppData" / "Local" / "Programs" / "OSGeo4W",
        Path("C:/OSGeo4W"),
        Path("C:/OSGeo4W64"),
        Path("C:/Program Files/OSGeo4W"),
        Path("C:/Program Files/OSGeo4W64"),
    ]

    for location in possible_locations:
        if location.exists() and (location / "bin" / "gdalinfo.exe").exists():
            return str(location)

    return None


def clear_conflicting_gdal_vars():
    """
    Clear environment variables that might conflict with OSGeo4W GDAL.
    """
    conflicting_vars = ["POSTGIS_GDAL_ENABLED_DRIVERS", "GDAL_FILENAME_IS_UTF8"]

    cleared = []
    for var in conflicting_vars:
        if var in os.environ:
            del os.environ[var]
            cleared.append(var)

    if cleared:
        print(f"  Cleared conflicting variables: {', '.join(cleared)}")


def setup_environment():
    """
    Configure environment variables for OSGeo4W GDAL installation.
    Resolves conflicts with conda and other GDAL installations.
    """
    print("Setting up GDAL environment...")

    # Find OSGeo4W installation
    osgeo_root = find_osgeo4w_installation()
    if not osgeo_root:
        print("ERROR: OSGeo4W installation not found!")
        print("Please install OSGeo4W from: https://trac.osgeo.org/osgeo4w/")
        return False

    print(f"  Found OSGeo4W at: {osgeo_root}")

    # Clear potentially conflicting environment variables
    clear_conflicting_gdal_vars()

    # Set GDAL data directory (override any existing)
    os.environ["GDAL_DATA"] = f"{osgeo_root}\\share\\gdal"

    # Set PROJ library directory
    os.environ["PROJ_LIB"] = f"{osgeo_root}\\share\\proj"

    # Add OSGeo4W bin to PATH (prepend to ensure it takes precedence)
    bin_path = f"{osgeo_root}\\bin"
    current_path = os.environ.get("PATH", "")
    if bin_path not in current_path:
        os.environ["PATH"] = f"{bin_path};{current_path}"

    print("GDAL environment configured for OSGeo4W")
    print(f"  GDAL_DATA: {os.environ['GDAL_DATA']}")
    print(f"  PROJ_LIB: {os.environ['PROJ_LIB']}")

    # Warn if conda environment is active
    if "CONDA_DEFAULT_ENV" in os.environ:
        conda_env = os.environ["CONDA_DEFAULT_ENV"]
        print(f"  WARNING: Active conda environment detected: {conda_env}")
        print(f"  OSGeo4W GDAL will take precedence over conda GDAL")

    return True


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
        print("  TIP: Try running in OSGeo4W Shell or check installation")
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
        print("  TIP: Install with: pip install rasterio (in OSGeo4W environment)")
        return False
    except Exception as e:
        print(f"FAILED: Rasterio test failed: {e}")
        return False


def test_geospatial_stack():
    """
    Test the full geospatial Python stack.
    """
    packages = {
        "gdal": "osgeo.gdal",
        "rasterio": "rasterio",
        "geopandas": "geopandas",
        "fiona": "fiona",
        "shapely": "shapely",
    }

    print("Testing geospatial package stack:")
    success_count = 0

    for name, import_path in packages.items():
        try:
            module = __import__(import_path, fromlist=[""])
            if hasattr(module, "__version__"):
                version = module.__version__
            elif name == "gdal":
                version = (
                    module.gdal.__version__ if hasattr(module, "gdal") else "unknown"
                )
            else:
                version = "unknown"
            print(f"  SUCCESS: {name} ({version})")
            success_count += 1
        except ImportError as e:
            print(f"  FAILED: {name} - {e}")

    print(f"\nGeospatial stack: {success_count}/{len(packages)} packages available")
    return success_count == len(packages)


def diagnose_environment():
    """
    Diagnose current environment setup and potential conflicts.
    """
    print("\nEnvironment diagnosis:")

    # Check Python interpreter
    print(f"  Python executable: {sys.executable}")

    # Check for conda environment
    if "CONDA_DEFAULT_ENV" in os.environ:
        print(f"  Conda environment: {os.environ['CONDA_DEFAULT_ENV']}")
        conda_prefix = os.environ.get("CONDA_PREFIX", "Not set")
        print(f"  Conda prefix: {conda_prefix}")
    else:
        print("  Conda: Not detected")

    # Check GDAL environment variables
    gdal_vars = [
        "GDAL_DATA",
        "PROJ_LIB",
        "GDAL_FILENAME_IS_UTF8",
        "POSTGIS_GDAL_ENABLED_DRIVERS",
    ]
    for var in gdal_vars:
        value = os.environ.get(var, "Not set")
        status = (
            "✓"
            if var in ["GDAL_DATA", "PROJ_LIB"] and "OSGeo4W" in value
            else "⚠"
            if var in os.environ
            else "✓"
        )
        print(f"  {var}: {value} {status}")

    # Check PATH for OSGeo4W
    path_entries = os.environ.get("PATH", "").split(";")
    osgeo_in_path = any("OSGeo4W" in entry for entry in path_entries)
    print(f"  OSGeo4W in PATH: {'✓ Yes' if osgeo_in_path else '✗ No'}")


# Automatically configure environment when module is imported
if __name__ == "__main__":
    if not setup_environment():
        print("\nERROR: Failed to set up GDAL environment")
        diagnose_environment()
        sys.exit(1)

    print("\nTesting individual components:")
    gdal_ok = test_gdal_import()
    rasterio_ok = test_rasterio_import()

    print("\nTesting full geospatial stack:")
    stack_ok = test_geospatial_stack()

    if gdal_ok and rasterio_ok and stack_ok:
        print(f"\nSUCCESS: All geospatial tools are working properly!")
    else:
        print(f"\nWARNING: Some issues detected. Check output above.")
        diagnose_environment()
else:
    # Auto-setup when imported
    setup_environment()
