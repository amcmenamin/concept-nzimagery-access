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


