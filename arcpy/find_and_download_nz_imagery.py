"""
Script: find_and_download_nz_imagery.py
Purpose: Find open AWS NZ imagery layers intersecting a study area and download them using ArcGIS arcpy libraries only.
"""

import arcpy
import os
import json
import posixpath
from arcpy import AIO

# --- Step 1: Set workspace and study area ---
workspace = r"C:\data\imagery"
gdb_path = os.path.join(workspace, "study_areas.gdb")
study_layer = "study_area1"
filter_region = "wellington/wellington"
filter_date = "2021"
filter_gsd = "0.3m"
use_rgbnir = True
use_service = False

arcpy.env.workspace = gdb_path

# Read study area polygons
study_polys = [row[0] for row in arcpy.da.SearchCursor(study_layer, ["SHAPE@"])]

# --- Step 3: Create Cloud Storage Connection File (.acs) ---
acs_path = os.path.join(workspace, "aws_nzimagery.acs")
if not os.path.exists(acs_path):
    arcpy.management.CreateCloudStorageConnectionFile(
        out_folder_path=workspace,
        out_name="aws_nzimagery.acs",
        service_provider="AMAZON",
        bucket_name="nz-imagery",
        region="ap-southeast-2"
    )
cloud_io = AIO(acs_path)

# --- Step 2: Query NZ Imagery Survey Index FeatureService or use catalog---
if use_service:
    service_url = "https://services.arcgis.com/xdsHIIxuCWByZiCB/arcgis/rest/services/NZ_Imagery_Survey_Index_view/FeatureServer/0"
    layer_name = "nz_imagery_index"

    # Create the feature layer from the REST service.
    arcpy.management.MakeFeatureLayer(service_url, layer_name)

    s3_field = "s3"

    s3_paths = sorted(
        {
            row[0].replace("s3://nz-imagery/", "").strip("/") + "/"
            for row in arcpy.da.SearchCursor(layer_name, [s3_field])
            if row[0]
        }
    )

    # Replace rgb with rgbnir in each s3_path
    if use_rgbnir:
        s3_paths = [path.replace("rgb/", "rgbnir/") for path in s3_paths]
else:
    catalog_path = "/vsis3/nz-imagery/catalog.json"
    file = cloud_io.open(catalog_path, "r") 
    catalog_data = json.loads(file.read())
    file.close()

    s3_paths = []
    for i in range(len(catalog_data.get("links", {}))):
        if catalog_data["links"][i].get("rel") == "child":
            s3_path = catalog_data["links"][i].get("href", "")
            # './auckland/auckland-coast_2023_0.05m/rgb/2193/collection.json'
            s3_path = s3_path.replace("collection.json", "")
            s3_path = s3_path.replace("./", "").strip("/")
            s3_paths.append(s3_path)

region_filter = filter_region.lower().strip() if filter_region and filter_region.strip() else ""
date_filter = filter_date.lower().strip() if filter_date and filter_date.strip() else ""
gsd_filter = filter_gsd.lower().strip() if filter_gsd and filter_gsd.strip() else ""

# Apply filters in two steps so when both are provided, both must match.
if region_filter:
    s3_paths = [path for path in s3_paths if region_filter in path.lower()]

if date_filter:
    s3_paths = [path for path in s3_paths if date_filter in path.lower()]

if gsd_filter:
    s3_paths = [path for path in s3_paths if gsd_filter in path.lower()]

if use_rgbnir:
    s3_paths = [path for path in s3_paths if "rgbnir/" in path.lower()]
else:
    s3_paths = [path for path in s3_paths if "rgb/" in path.lower()]


# --- Step 4: List and read JSON files in S3 path, extract bbox ---
downloaded_output_names = set()

for study_poly in study_polys:
    print("Processing study area...")
    for s3_path in s3_paths:
        folder_path = s3_path.strip("/")
        json_files = [
            item.name for item in cloud_io.scandir(s3_path, depth=0)
            if item.name.endswith(".json") and not item.is_dir()
        ]
        for json_file in json_files:
            # AIO paths are cloud keys; keep POSIX separators and avoid duplicate prefixes.
            if json_file.startswith(folder_path + "/"):
                json_rel_path = json_file
            else:
                json_rel_path = posixpath.join(folder_path, json_file)
            file = cloud_io.open(json_rel_path, "r")
            json_data = json.loads(file.read())
            file.close()
            # Extract bbox (assume GeoJSON format)
            bbox = json_data.get("bbox")
            if not bbox:
                continue
            # Create arcpy Polygon from bbox
            xmin, ymin, xmax, ymax = bbox
            source_srid = arcpy.SpatialReference(4326)
            bbox_poly = arcpy.Polygon(arcpy.Array([
                arcpy.Point(xmin, ymin),
                arcpy.Point(xmin, ymax),
                arcpy.Point(xmax, ymax),
                arcpy.Point(xmax, ymin),
                arcpy.Point(xmin, ymin)
            ]), source_srid)

            out_sr = arcpy.SpatialReference(2193)
            # print(bbox_poly.spatialReference.name)
            bbox_poly = bbox_poly.projectAs(out_sr, "NZGD_2000_To_WGS_1984_1")

            # --- Step 5: Check intersection for this study polygon ---
            # Returns True when polygons intersect in any way.
            if study_poly.disjoint(bbox_poly):
                print(f"No overlap between study area and {json_rel_path}, skipping. - bbox: {bbox_poly.extent}")
                continue
            
            print(f"Processing study area with extent: {study_poly.extent}")
            
            # --- Step 6: Download raster using arcpy.management.DownloadRasters ---
            raster_name = json_data.get("assets", {})['visual']['href']
            if not raster_name:
                continue
            raster_name = raster_name.replace("./","")
            s3_raster_path = f"/vsis3/nz-imagery/{folder_path}/{raster_name}"
            output_folder = os.path.join(workspace, folder_path)
            if not os.path.exists(output_folder):
                os.makedirs(output_folder)
            output_name = os.path.basename(raster_name)
            if output_name in downloaded_output_names:
                continue
            local_dest = os.path.join(output_folder, output_name)
            print(f"Will take some time: Downloading {s3_raster_path} to {local_dest}...")
            cloud_io.copy(s3_raster_path, local_dest)
            downloaded_output_names.add(output_name)
            print(f"Raster downloaded to {local_dest}")
