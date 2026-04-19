from osgeo import gdal
import os
from pathlib import Path


def uncompress_tiff(input_path: str, output_path: str) -> None:
    """Read a TIFF file and write it as an uncompressed GeoTIFF."""
    ds = gdal.Open(input_path, gdal.GA_ReadOnly)
    if ds is None:
        raise RuntimeError(f"Could not open: {input_path}")

    driver = gdal.GetDriverByName("GTiff")
    creation_options = [
        "COMPRESS=NONE",
        "TILED=YES",
        "BLOCKXSIZE=512",
        "BLOCKYSIZE=512",
        "BIGTIFF=IF_SAFER",
    ]
    out_ds = driver.CreateCopy(output_path, ds, strict=0, options=creation_options)
    if out_ds is None:
        raise RuntimeError(f"Could not write: {output_path}")

    out_ds.FlushCache()
    out_ds = None
    ds = None
    print(f"Written: {output_path}")


def process_folder(input_folder: str, output_folder: str) -> None:
    input_dir = Path(input_folder)
    output_dir = Path(output_folder)
    output_dir.mkdir(parents=True, exist_ok=True)

    tiff_files = list(input_dir.glob("*.tif")) + list(input_dir.glob("*.tiff"))
    if not tiff_files:
        print(f"No TIFF files found in {input_folder}")
        return

    for tiff_file in tiff_files:
        out_file = output_dir / tiff_file.name
        print(f"Processing: {tiff_file.name}")
        uncompress_tiff(str(tiff_file), str(out_file))

    print(f"\nDone. {len(tiff_files)} file(s) processed.")


if __name__ == "__main__":
    input_folder = r"C:\Data\imagery"
    output_folder = r"C:\Data\imagery\uncompressed"

    process_folder(input_folder, output_folder)

