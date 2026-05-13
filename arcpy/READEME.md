## Purpose: Given a study area find open AWS imagery layers that intersect the study area

This must run in an ArcPy environment.

You can set some parameters at the top of the fileL

workspace = r"C:\data\imagery"

gdb_path = os.path.join(workspace, "study_areas.gdb")

study_layer = "study_area1"

The following will select paths have have these keys in the string - any can be empty string.

Examples: 
filter_region = "wellington/wellington"

filter_date = "2021"

filter_gsd = "0.3m"

filter_region = "auckland"

filter_date = "2024"

filter_gsd = "0.25m"


The default access is RGB if you want to access RGBNIR (if present) set:

use_rgbnir = True

The code can use the rest service to get the initial paths or access the full catalog directly

use_service = True or False. Set to False if service fails.

Query NZ Imagery Survey Index FeatureService ---
https://services.arcgis.com/xdsHIIxuCWByZiCB/arcgis/rest/services/NZ_Imagery_Survey_Index_view/FeatureServer/0

**Step 1**

Define workspace c:\data\imagery

Open local file geodatabase (study_areas) in workspace

Read layer (study_area1)

Create a list of polygon geometries

**Step 2**

For a polygon and find the related information that intersects using esri rest featureservice NZ Imagery Survey Index https://services.arcgis.com/xdsHIIxuCWByZiCB/arcgis/rest/services/NZ_Imagery_Survey_Index_view/FeatureServer/0

Get a list of paths from 's3 Path' attribute - s3://nz-imagery/wellington/wellington_2016-2017_0.3m/rgb/2193/

**Step 3**
using S3_Path and lookup - CreateCloudStorageConnectionFile
NZ_DATASETS: dict[str, DatasetInfo] = {
    "imagery": DatasetInfo(
        bucket="nz-imagery", region="ap-southeast-2", name="NZ Imagery"
    ),
    "elevation": DatasetInfo(
        bucket="nz-elevation", region="ap-southeast-2", name="NZ Elevation"
    ),
    "coastal": DatasetInfo(
        bucket="nz-coastal", region="ap-southeast-2", name="NZ Coastal"
    ),
}
import arcpy

Create the .acs file

arcpy.management.CreateCloudStorageConnectionFile(
    out_folder_path=workspace,
    out_name="aws_nzimagery.acs",
    service_provider="AMAZON",
    bucket_name="nz-imagery",
    region="ap-southeast-2"
)

read all the item json files in that path example wellington/wellington_2016-2017_0.3m/rgb/2193/

from arcpy import AIO
import json

Path to your .acs file and the JSON inside the bucket
acs_path = r"c:\data\imagery\aws_nzimagery.acs"

json_relative_path = "wellington/wellington_2016-2017_0.3m/rgb/2193/"

Initialize AIO with the connection file
cloud_io = AIO(acs_path)

List all .json files in that folder
'depth=0' only looks in the top level of that folder

json_files = [
    item.name for item in cloud_io.scandir(folder_path, depth=0) 
    if item.name.endswith(".json") and not item.is_dir()
]

for each json file - read and extract bbox
# Use AIO to open and read the file
with cloud_io.open(json_relative_path, "r") as f:
    json_data = json.loads(f.read())
    create bbox

**Step 4**

See if bbox intersects study area polygon

If yes add the name of the raster file to the relative path

Loop through the slected imagery paths and
Create a virtual raster file - .vrt


**Step 5**

Download imagery - example code
import arcpy
import os

a. Define paths and parameters
Example for a public AWS S3 file (requires internet access)
s3_path = r"/vsis3/esa-worldcover/v100/2020/ESA_WorldCover_10m_2020_v100_Map_AWS.vrt"
output_folder = r"C:\Data\Imagery\Downloaded"
output_name = tif name.tiff

Create output folder if it doesn't exist
if not os.path.exists(output_folder):
    os.makedirs(output_folder)

b. Use Download Rasters Tool
This tool copies the data locally
arcpy.management.DownloadRasters(
    input_raster=s3_path,
    output_folder=output_folder,
    query_definition="",
    output_name=output_name
)

print(f"Raster downloaded to {os.path.join(output_folder, output_name)}")





