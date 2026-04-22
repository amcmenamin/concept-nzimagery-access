import setup_gdal_env  # Configure GDAL environment
from osgeo import gdal

gdal.Warp("out.tif", "in.tif", xRes=10, yRes=10, resampleAlg="bilinear")
