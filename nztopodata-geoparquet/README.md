# GeoParquet Layer Query

Query a remote GeoParquet 1.1 layer with DuckDB and its `spatial` extension.
The included example retrieves airport features that intersect the approximate
mainland New Zealand bounding box.

## Requirements

- Python 3.11 or newer
- [uv](https://docs.astral.sh/uv/)
- Network access to the GeoParquet URL and DuckDB extension repository

## Run

```powershell
uv sync
uv run python extract_geoparquet_layer.py
```

## Docker

Build the image, then mount a host folder for the exported files and logs:

```powershell
docker build -t geoparquet-export .
docker run --rm -v "${PWD}/exports:/app/exports" geoparquet-export --layer-names airport --bbox-name CHATHAM_ISLANDS
```

All runner arguments can follow the image name. Run `docker run --rm
geoparquet-export --help` to view them.

## Use As A Class

```python
from extract_geoparquet_layer import GeoParquetLayer

airports = GeoParquetLayer(
	"https://d1jzh93b1t1cv.cloudfront.net/data",
	"airport",
	"CHATHAM_ISLANDS",
)
rows = airports.query_bbox()
```

The constructor's `bbox` property defaults to `"NZ_MAINLAND"`. It accepts a
defined region name such as `"CHATHAM_ISLANDS"`, or an explicit tuple in
`(west, south, east, north)` order:

```python
custom_area = GeoParquetLayer(
	"https://d1jzh93b1t1cv.cloudfront.net/data",
	"airport",
	(174.7, -41.4, 174.9, -41.2),
)
rows = custom_area.query_bbox()
```

`query_bbox()` first filters the GeoParquet 1.1 `bbox` covering using overlap
comparisons, then uses `ST_Intersects` for an exact geometry test. The source
layer must provide root-level `geometry` and `bbox` columns; `bbox` must contain
`xmin`, `ymin`, `xmax`, and `ymax` fields.

## Export GeoParquet

Set `export_folder` to choose where DuckDB writes the extracted file. The output
is named `<layer_name>.parquet` and is produced by DuckDB `COPY` with Zstandard
compression.

```python
output, copy_sql = airports.export_bbox()
print(output)  # exports/airport.parquet
print(copy_sql)  # full DuckDB COPY command
```

Use `export_new_zealand()` to export all configured mainland and offshore
regions into one file.

## Runner

Run the default airport and building-point exports for all configured New
Zealand regions:

```powershell
uv run python run_extract_geoparquet.py
```

Use `--help` to view the available options. Layer names are positional; use
`--bbox-name` for a named region or `--extent` for four explicit coordinates:

```powershell
uv run python run_extract_geoparquet.py --help
uv run python run_extract_geoparquet.py airport --bbox-name CHATHAM_ISLANDS
uv run python run_extract_geoparquet.py --layer-names airport,building_point
uv run python run_extract_geoparquet.py building_point --extent 174.7,-41.4,174.9,-41.2
uv run python run_extract_geoparquet.py airport --export-folder data/exports
```

Supported `--bbox-name` values:

```text
NZ_MAINLAND
NORTHLAND_REGION
AUCKLAND_REGION
WAIKATO_REGION
BAY_OF_PLENTY_REGION
GISBORNE_REGION
HAWKES_BAY_REGION
TARANAKI_REGION
MANAWATU_WHANGANUI_REGION
GREATER_WELLINGTON_REGION
WEST_COAST_REGION
CANTERBURY_REGION
OTAGO_REGION
SOUTHLAND_REGION
TASMAN_REGION
NELSON_REGION
MARLBOROUGH_REGION
CHATHAM_ISLANDS
SNARES_ISLANDS
AUCKLAND_ISLANDS
CAMPBELL_ISLAND
ANTIPODES_ISLANDS
BOUNTY_ISLANDS
RAOUL_ISLAND
MACAULEY_CURTIS_ISLANDS
AUCKLAND_URBAN_AREA
GREATER_WELLINGTON_URBAN_AREA
CHRISTCHURCH_URBAN_AREA
KAITAIA_URBAN_AREA
WHANGAREI_URBAN_AREA
HAMILTON_URBAN_AREA
TAURANGA_URBAN_AREA
ROTORUA_URBAN_AREA
GISBORNE_URBAN_AREA
NAPIER_HASTINGS_URBAN_AREA
TAUPO_URBAN_AREA
NEW_PLYMOUTH_URBAN_AREA
WHANGANUI_URBAN_AREA
PALMERSTON_NORTH_URBAN_AREA
PARAPARAUMU_URBAN_AREA
WELLINGTON_URBAN_AREA
NELSON_URBAN_AREA
BLENHEIM_URBAN_AREA
GREYMOUTH_URBAN_AREA
TIMARU_URBAN_AREA
DUNEDIN_URBAN_AREA
QUEENSTOWN_URBAN_AREA
INVERCARGILL_URBAN_AREA
```

Without `--bbox-name` or `--extent`, the runner preserves the default all-regions
New Zealand export. Each run logs its `COPY` SQL to
`<export-folder>/extract_geoparquet.log`.

When `--bbox-name` is used, the runner appends its lowercase name to the export
folder. For example, `--export-folder exports --bbox-name CHATHAM_ISLANDS` writes to
`exports/chatham_islands/`.

Regional bboxes are calculated from NZ Stats regional boundary data. City names
align with Stats NZ Urban Area labels; their mapped bboxes are intended for
coarse extraction, while the GeoParquet geometry predicate performs the exact
spatial test.

`query_new_zealand()` uses the class's `NZ_BBOXES` set. It includes the
mainland extent plus Chatham, Snares, Auckland, Campbell, Antipodes, Bounty,
and Kermadec Islands (Raoul, Macauley, and Curtis). Separate bboxes avoid
turning the widely dispersed islands into one large ocean-sized query area.
