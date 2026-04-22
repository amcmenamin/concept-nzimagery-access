import setup_gdal_env  # Configure GDAL environment
from osgeo import gdal

print(gdal.VersionInfo("LIBS"))

# libwebp support is indicated by the presence of "WEBP" in the list of supported formats.
formats = gdal.GetDriverCount()
webp_supported = any(
    gdal.GetDriver(i).GetDescription() == "WEBP" for i in range(formats)
)
if webp_supported:
    print("GDAL has WEBP support.")
else:
    print("GDAL does NOT have WEBP support.")
    print(
        "You may need to install GDAL with WEBP support or build GDAL with WEBP enabled."
    )


import rasterio
from rasterio.env import GDALVersion

print(rasterio.__gdal_version__)
print(f"{GDALVersion.runtime().major}.{GDALVersion.runtime().minor}")


with rasterio.Env() as env:
    print(env)
    print(env.drivers())
    print(f"WEBP support: {'WEBP' in env.drivers()}")
