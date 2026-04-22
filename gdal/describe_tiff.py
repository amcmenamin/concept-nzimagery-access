"""Describe TIFF/COG properties using GDAL."""

from __future__ import annotations

from pathlib import Path
from osgeo import gdal


def describe_tiff(path: str, results_file: str = "") -> None:
    tiff_path = Path(path)
    if not tiff_path.exists():
        raise FileNotFoundError(f"File not found: {tiff_path}")

    ds = gdal.Open(str(tiff_path), gdal.GA_ReadOnly)
    if ds is None:
        raise RuntimeError(f"Unable to open dataset: {tiff_path}")

    # Helper function to print and optionally write to file
    file_handle = None
    if results_file:
        file_handle = open(results_file, "w", encoding="utf-8")

    def print_and_write(text: str) -> None:
        print(text)
        if file_handle:
            file_handle.write(text + "\n")

    try:
        driver = ds.GetDriver()
        geotransform = ds.GetGeoTransform(can_return_null=True)

        print_and_write("=== Basic ===")
        print_and_write(f"Path: {tiff_path}")
        print_and_write(f"Driver: {driver.ShortName if driver else 'unknown'}")
        print_and_write(f"Width: {ds.RasterXSize}")
        print_and_write(f"Height: {ds.RasterYSize}")
        print_and_write(f"Band count: {ds.RasterCount}")

        dtypes: list[str] = []
        nodata_values: list[float | None] = []
        color_interpretation: list[str] = []
        block_shapes: list[tuple[int, int]] = []

        print_and_write("\n=== Overviews ===")
        for band_index in range(1, ds.RasterCount + 1):
            band = ds.GetRasterBand(band_index)
            if band is None:
                continue

            dtypes.append(gdal.GetDataTypeName(band.DataType))
            nodata_values.append(band.GetNoDataValue())
            color_interpretation.append(
                gdal.GetColorInterpretationName(band.GetColorInterpretation())
            )
            block_shapes.append(band.GetBlockSize())

            overview_count = band.GetOverviewCount()
            if overview_count > 0:
                factors: list[int] = []
                for i in range(overview_count):
                    overview = band.GetOverview(i)
                    if overview is None or overview.XSize == 0:
                        continue
                    factors.append(max(1, round(ds.RasterXSize / overview.XSize)))
                print_and_write(
                    f"Band {band_index}: {factors if factors else overview_count}"
                )
            else:
                print_and_write(f"Band {band_index}: none")

        print_and_write(f"Dtypes: {dtypes}")

        print_and_write("\n=== Spatial ===")
        projection = ds.GetProjectionRef() or "None"
        print_and_write(f"CRS: {projection}")

        if geotransform:
            x_min = geotransform[0]
            y_max = geotransform[3]
            x_res = geotransform[1]
            y_res = geotransform[5]
            x_max = x_min + ds.RasterXSize * x_res
            y_min = y_max + ds.RasterYSize * y_res
            print_and_write(f"Bounds: ({x_min}, {y_min}, {x_max}, {y_max})")
            print_and_write(f"Resolution: ({x_res}, {abs(y_res)})")
            print_and_write(f"Transform: {geotransform}")
        else:
            print_and_write("Bounds: None")
            print_and_write("Resolution: None")
            print_and_write("Transform: None")

        print_and_write("\n=== Data ===")
        print_and_write(f"NoData: {nodata_values}")
        print_and_write(f"Color interpretation: {color_interpretation}")

        print_and_write("\n=== TIFF/COG Structure ===")
        image_structure = ds.GetMetadata("IMAGE_STRUCTURE") or {}
        print_and_write(f"Is tiled: {image_structure.get('TILED', 'NO')}")
        print_and_write(f"Block shapes: {block_shapes}")
        print_and_write(f"Compression: {image_structure.get('COMPRESSION', 'unknown')}")
        print_and_write(f"Interleaving: {image_structure.get('INTERLEAVE', 'unknown')}")

        tags = ds.GetMetadata() or {}
        if tags:
            print_and_write("\n=== Dataset Tags ===")
            for key in sorted(tags):
                print_and_write(f"{key}: {tags[key]}")

        if file_handle:
            print_and_write(f"\n✅ Results also written to: {results_file}")
    finally:
        ds = None
        if file_handle:
            file_handle.close()


def main() -> int:
    path = r"C:\Data\imagery\BM36_5000_1010_RGBI.tiff"
    results_file = r"C:\Data\imagery\BM36_5000_1010_RGBI.txt"

    try:
        describe_tiff(path, results_file)
    except Exception as exc:
        print(f"Error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    main()
