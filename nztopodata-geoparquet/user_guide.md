# User Guide

This guide covers the configuration and export options for the GeoParquet layer
extractor. Run the Python commands from the `src` folder.

## Default Configuration

When no configuration options are supplied, the runner uses:

- Layer configuration: `nztopo`
- URL data path: `nztopodev`
- Layer file: `config/nztopo_layers.yml`
- URL file: `config/url_data_paths.yml`
- Export folder: `exports`
- Default bbox: `NZ_MAINLAND`

The current `nztopodev` URL is stored in `url_data_paths.yml`, rather than in
the Python source.

## Install And Run

Install the locked dependencies and view the runner options:

```powershell
uv sync
Set-Location src
uv run python -m run_extract_geoparquet --help
```

Run the default export:

```powershell
uv run python -m run_extract_geoparquet
```

The runner writes GeoParquet files and an `extract_geoparquet.log` file under
`exports`.

## Select Layers

Use `--layer-names` with a comma-separated list:

```powershell
uv run python -m run_extract_geoparquet --layer-names airport,building_point
```

Or use `--layer-config` with a YAML file whose keys are layer names:

```powershell
uv run python -m run_extract_geoparquet --layer-config config/nztopo_layers.yml
```

The layer names and themes are defined in `config/nztopo_layers.yml`.

## URL Data Paths

URL values are defined in `config/url_data_paths.yml`:

```yaml
nztopodev: https://d1jzh93b1t1cv.cloudfront.net/data
overture: s3://overturemaps-us-west-2/release/
```

The default is `nztopodev`. Select the configured URL with
`--url-data-path`:

```powershell
# nztopodev
uv run python -m run_extract_geoparquet `
  --layer-names airport `
  --url-data-path nztopodev

# overture
uv run python -m run_extract_geoparquet `
  --layer-names airport `
  --url-data-path overture
```

Use `--url-path-config` when the URL keys are stored in another YAML file:

```powershell
uv run python -m run_extract_geoparquet `
  --url-path-config config/url_data_paths.yml `
  --url-data-path overture
```

## Named Bboxes

Named bboxes are defined in `config/nz_names_bboxes.yml`.

Use a named bbox from the runner:

```powershell
uv run python -m run_extract_geoparquet `
  --layer-names airport `
  --bbox-name CHATHAM_ISLANDS
```

When `--bbox-name` is used, output is placed in a lowercase subfolder such as
`exports/chatham_islands`.

To add another set of named bboxes, create a file following the
`<name>_names_bboxes.yml` naming pattern in `config`.

## Explicit Extents

Use `--extent` when the bbox is not already named. Coordinates must be in
`west,south,east,north` order:

```powershell
uv run python -m run_extract_geoparquet `
  --layer-names airport `
  --extent 174.7,-41.4,174.9,-41.2
```

## Python Export API

Query one bbox:

```python
from extract_geoparquet_layer import GeoParquetLayer

layer = GeoParquetLayer(
  "https://d1jzh93b1t1cv.cloudfront.net/data",
  "airport",
  bbox="NZ_MAINLAND",
)
rows = layer.query_bbox()
```

Export one bbox:

```python
output_path, copy_sql = layer.export_bbox()
```

Export the configured New Zealand mainland and offshore regions:

```python
output_path, copy_sql = layer.export_new_zealand()
```

Set a different output folder with `export_folder`:

```python
layer = GeoParquetLayer(
  "https://d1jzh93b1t1cv.cloudfront.net/data",
    "airport",
    export_folder="data/exports",
)
```

## Docker

Build the image:

```powershell
docker build -t geoparquet-export .
```

Run the default export with a host output folder:

```powershell
docker run --rm `
  -v "${PWD}/exports:/app/src/exports" `
  geoparquet-export
```

Pass runner options after the image name:

```powershell
docker run --rm `
  -v "${PWD}/exports:/app/src/exports" `
  geoparquet-export `
  --layer-names airport,water `
  --bbox-name CHATHAM_ISLANDS
```

## Windows WSL Containers

WSL 2.9.3 or later includes `wslc.exe`, a container CLI that does not require
Docker. Update WSL and verify the installation from PowerShell:

```powershell
wsl --update
wsl --version
wslc version
```

From the project root, build the image with `wslc`:

```powershell
wslc build -t geoparquet-export .
```

Run the image and pass runner options:

```powershell
wslc run --rm -v "${PWD}/exports:/app/src/exports" geoparquet-export --layer-names airport,water --bbox-name CHATHAM_ISLANDS
```

See Microsoft's [Get started with containers on WSL](https://learn.microsoft.com/en-us/windows/wsl/tutorials/wsl-containers)
guide for installation and troubleshooting details.

## Output And Logging

Each exported layer is written as `<layer_name>.parquet`. The runner also logs
the generated DuckDB `COPY` SQL to:

```text
<export-folder>/extract_geoparquet.log
```

Named bbox runs use a lowercase bbox subfolder below the selected export
folder. Explicit extents use the export folder directly.

## Example Runs

Run one layer for the Chatham Islands using the default NZ URL configuration:

```powershell
uv run python -m run_extract_geoparquet `
  --layer-names island `
  --bbox-name CHATHAM_ISLANDS `
  --url-data-path nztopodev `
  --export-folder C:\temp\exports
```

Run all layers from the NZ layer configuration for the Chatham Islands:

```powershell
uv run python -m run_extract_geoparquet `
  --layer-config config/nztopo_layers.yml `
  --bbox-name CHATHAM_ISLANDS `
  --url-data-path nztopodev `
  --export-folder C:\temp\exports
```

Run all configured layers using the default NZ regional coverage and URL:

```powershell
uv run python -m run_extract_geoparquet `
  --layer-config config/nztopo_layers.yml `
  --url-data-path nztopodev `
  --export-folder C:\temp\exports
```

The same example runs from Windows Command Prompt use `^` for line
continuation:

Run one layer for the Chatham Islands:

```cmd
uv run python -m run_extract_geoparquet ^
  --layer-names island ^
  --bbox-name CHATHAM_ISLANDS ^
  --url-data-path nztopodev ^
  --export-folder C:\temp\exports
```

Run all configured layers for the Chatham Islands:

```cmd
uv run python -m run_extract_geoparquet ^
  --layer-config config/nztopo_layers.yml ^
  --bbox-name CHATHAM_ISLANDS ^
  --url-data-path nztopodev ^
  --export-folder C:\temp\exports
```

Run all configured layers using the default NZ regional coverage:

```cmd
uv run python -m run_extract_geoparquet ^
  --layer-config config/nztopo_layers.yml ^
  --url-data-path nztopodev ^
  --export-folder C:\temp\exports
```

The same commands can be run from Linux or macOS shells. Bash uses `\` for
line continuation and Linux paths use `/`:

Run all configured layers for the Chatham Islands:

```bash
uv run python -m run_extract_geoparquet \
  --layer-config config/nztopo_layers.yml \
  --bbox-name CHATHAM_ISLANDS \
  --url-data-path nztopodev \
  --export-folder /tmp/geoparquet-exports
```

Run all configured layers using the default NZ regional coverage:

```bash
uv run python -m run_extract_geoparquet \
  --layer-config config/nztopo_layers.yml \
  --url-data-path nztopodev \
  --export-folder /tmp/geoparquet-exports
```

When no `--bbox-name` or `--extent` is supplied, the runner uses the NZ
regional coverage set:

- `NZ_MAINLAND`
- `CHATHAM_ISLANDS`
- `SNARES_ISLANDS`
- `AUCKLAND_ISLANDS`
- `CAMPBELL_ISLAND`
- `ANTIPODES_ISLANDS`
- `BOUNTY_ISLANDS`
- `RAOUL_ISLAND`
- `MACAULEY_CURTIS_ISLANDS`

Use `--bbox-name` or `--extent` when only one area should be exported.
