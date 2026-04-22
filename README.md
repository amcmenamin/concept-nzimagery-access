These file contain example approaches to connecting to the imagery hosted on AWS.

NOTE: THIS IS NOT SYSTEM/APP CODE BUT A SET OF EXAMPLES. FEEL FREE TO COPY SECTIONS.
THIS REPO IS FOR LEARNING / DEMO PURPOSES

## Other tooling information can be found here

ArcGIS Pro - https://storymaps.arcgis.com/collections/e6d212054d9744f399fcbed00a75ee43?item=1

Other tools / approaches - https://github.com/linz/imagery/blob/master/docs/usage.md


## Creating chips - other code examples

A modern approach to creating chips: see: https://github.com/Clay-foundation/stacchip/

NZ Example: https://github.com/Clay-foundation/stacchip/blob/main/stacchip/processors/linz_processor.py

## Creating a stacpg version

https://github.com/vincentsarago/MAXAR_opendata_to_pgstac

NZ Imagery - https://github.com/vincentsarago/MAXAR_opendata_to_pgstac/tree/main/Linz

## Find the collection of tiff images to use has several approaches

using **STAC** - see https://github.com/linz/imagery/blob/master/docs/usage.md

Top level catalog : https://nz-imagery.s3-ap-southeast-2.amazonaws.com/catalog.json

You can download **NZ Imagery Survey Index** from the LDS Service https://data.linz.govt.nz/layer/95677-nz-imagery-survey-index/

This information is also available as a ArcGIS Feature Service 

**NZ Imagery Survey Index**

See latest and planned survey

https://experience.arcgis.com/experience/553a610215c945e8971953bffee1e079/page/NZ-Imagery----Availability#data_s=id%3AdataSource_3-199c6d936c9-layer-2%3A271

https://services.arcgis.com/xdsHIIxuCWByZiCB/arcgis/rest/services/NZ_Imagery_Survey_Index_view/FeatureServer/0


**RGBI = RGBNIR**

southland/invercargill_2022_0.1m/rgbnir/2193

southland/southland-central-otago_2013-2014_0.4m/rgb/2193


#Note

RGB include 4 bands: 4=Alpha Band

RGBI includes 5 bands: ['Red', 'Green', 'Blue', 'NIR', 'Alpha']

## Latest aerial configuration

https://github.com/linz/basemaps-config/blob/master/config/tileset/aerial.json
