## Find the collection of tiff images to use has several approaches

using **STAC** - see https://github.com/linz/imagery/blob/master/docs/usage.md

Top level catalog : https://nz-imagery.s3-ap-southeast-2.amazonaws.com/catalog.json

You can download **NZ Imagery Survey Index** from the LDS Service https://data.linz.govt.nz/layer/95677-nz-imagery-survey-index/

This information is also available as a ArcGIS Feature Service 

**NZ Imagery Survey Index**

https://services.arcgis.com/xdsHIIxuCWByZiCB/arcgis/rest/services/NZ_Imagery_Survey_Index_view/FeatureServer/0


**RGBI = RGBNIR**

southland/invercargill_2022_0.1m/rgbnir/2193

southland/southland-central-otago_2013-2014_0.4m/rgb/2193


#Note

RGB include 4 bands: 4=Alpha Band

RGBI includes 5 bands: ['Red', 'Green', 'Blue', 'NIR', 'Alpha']