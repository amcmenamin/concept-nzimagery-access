"""Read LINZ public datasets from AWS S3 using rasterio directly.

This script uses rasterio to directly read imagery from AWS S3 without downloading.
Particularly useful for Cloud Optimized GeoTIFFs (COGs).

Install dependencies:
	pip install rasterio boto3

Examples:
	python imagery_rasterio_read.py
	python imagery_rasterio_read.py --dataset elevation --path "some/path/file.tiff"
	python imagery_rasterio_read.py --bbox 174.7 -36.9 174.8 -36.8
	python imagery_rasterio_read.py --info-only
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Optional, Tuple

import setup_gdal_env  # Configure GDAL environment
import rasterio
from rasterio.session import AWSSession
from rasterio.windows import from_bounds
import numpy as np


@dataclass(frozen=True)
class DatasetInfo:
	bucket: str
	region: str


LINZ_DATASETS: dict[str, DatasetInfo] = {
	"imagery": DatasetInfo(bucket="nz-imagery", region="ap-southeast-2"),
	"elevation": DatasetInfo(bucket="nz-elevation", region="ap-southeast-2"),
	"coastal": DatasetInfo(bucket="nz-coastal", region="ap-southeast-2"),
}


def build_s3_url(bucket: str, path: str) -> str:
	"""Build S3 URL for rasterio access."""
	return f"s3://{bucket}/{path}"


def setup_aws_session() -> AWSSession:
	"""Create an AWS session for unsigned requests (public data)."""
	return AWSSession(
		requester_pays=False,
		aws_unsigned=True,
	)


def read_raster_info(s3_url: str, session: AWSSession) -> dict:
	"""Read basic raster metadata without loading pixel data."""
	with rasterio.Env(session=session):
		with rasterio.open(s3_url) as dataset:
			info = {
				"driver": dataset.driver,
				"width": dataset.width,
				"height": dataset.height,
				"count": dataset.count,
				"dtype": dataset.dtypes[0],
				"crs": dataset.crs,
				"transform": dataset.transform,
				"bounds": dataset.bounds,
				"res": dataset.res,
				"nodata": dataset.nodata,
				"overviews": [dataset.overviews(i) for i in range(1, dataset.count + 1)],
			}
			return info


def read_raster_window(
	s3_url: str,
	session: AWSSession,
	bbox: Optional[Tuple[float, float, float, float]] = None,
	overview_level: int = 0,
) -> Tuple[np.ndarray, dict]:
	"""Read raster data from S3, optionally clipped to a bounding box.
	
	Args:
		s3_url: S3 URL to the raster file
		session: AWS session
		bbox: Optional bounding box (minx, miny, maxx, maxy) 
		overview_level: Overview level to read (0=full resolution)
		
	Returns:
		Tuple of (numpy array, metadata dict)
	"""
	with rasterio.Env(session=session):
		with rasterio.open(s3_url) as dataset:
			if bbox is not None:
				# Read only the window that intersects with the bbox
				window = from_bounds(*bbox, dataset.transform)
				# Clip window to dataset bounds
				window = window.intersection(
					rasterio.windows.Window(0, 0, dataset.width, dataset.height)
				)
				data = dataset.read(window=window, out_shape=(
					dataset.count,
					int(window.height),
					int(window.width)
				))
				# Calculate the transform for the windowed data
				transform = rasterio.windows.transform(window, dataset.transform)
			else:
				# Read full dataset at specified overview level
				if overview_level > 0 and any(dataset.overviews(1)):
					# Get overview at specified level
					overview_factor = dataset.overviews(1)[min(overview_level - 1, len(dataset.overviews(1)) - 1)]
					out_shape = (
						dataset.count,
						dataset.height // overview_factor,
						dataset.width // overview_factor,
					)
					data = dataset.read(out_shape=out_shape)
					# Adjust transform for overview
					transform = dataset.transform * dataset.transform.scale(overview_factor)
				else:
					data = dataset.read()
					transform = dataset.transform
			
			metadata = {
				"crs": dataset.crs,
				"transform": transform,
				"width": data.shape[2] if len(data.shape) == 3 else data.shape[1],
				"height": data.shape[1] if len(data.shape) == 3 else data.shape[0],
				"count": data.shape[0] if len(data.shape) == 3 else 1,
				"dtype": data.dtype,
				"nodata": dataset.nodata,
			}
			
			return data, metadata


def save_raster(
	data: np.ndarray,
	metadata: dict,
	output_path: str,
) -> None:
	"""Save numpy array as a local raster file."""
	with rasterio.open(
		output_path,
		'w',
		driver='GTiff',
		height=metadata['height'],
		width=metadata['width'],
		count=metadata['count'],
		dtype=metadata['dtype'],
		crs=metadata['crs'],
		transform=metadata['transform'],
		nodata=metadata['nodata'],
		compress='lzw',
	) as dst:
		if len(data.shape) == 3:
			# Multi-band
			print(f"Saving multi-band raster to {output_path}")
			dst.write(data)
		else:
			# Single band
			print(f"Saving single-band raster to {output_path}")
			dst.write(data, 1)


def list_s3_objects(bucket: str, prefix: str, region: str) -> list[str]:
	"""List objects in S3 bucket using boto3 (fallback for listing)."""
	try:
		import boto3
		from botocore import UNSIGNED
		from botocore.config import Config
		
		s3 = boto3.client(
			's3',
			region_name=region,
			config=Config(signature_version=UNSIGNED)
		)
		
		response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
		objects = []
		
		while True:
			if 'Contents' in response:
				objects.extend([obj['Key'] for obj in response['Contents']])
			
			if not response.get('IsTruncated', False):
				break
				
			response = s3.list_objects_v2(
				Bucket=bucket,
				Prefix=prefix,
				ContinuationToken=response['NextContinuationToken']
			)
		
		return objects
		
	except ImportError:
		print("boto3 not available for listing. Install with: pip install boto3")
		return []


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(
		description="Access LINZ public AWS datasets directly with rasterio."
	)
	parser.add_argument(
		"--dataset",
		choices=sorted(LINZ_DATASETS.keys()),
		default="imagery",
		help="Known LINZ dataset alias (default: imagery).",
	)
	parser.add_argument(
		"--bucket",
		default="",
		help="Override bucket name directly (optional).",
	)
	parser.add_argument(
		"--region",
		default="",
		help="Override AWS region directly (optional).",
	)

	#default="taranaki/taranaki_2022-2023_0.1m/rgb/2193/BQ31_10000_0101.tiff",
	parser.add_argument(
		"--path",
		default="wellington/wellington_2025_0.2m/rgbnir/2193/BM36_5000_1010.tiff",
		help="Object key/path to specific raster file.",
	)
	parser.add_argument(
		"--list-prefix",
		action="store_true",
		help="List object keys under --path (treat --path as a prefix/folder).",
	)
	parser.add_argument(
		"--info-only",
		action="store_true",
		help="Only display raster metadata, don't read data.",
	)
	parser.add_argument(
		"--bbox",
		nargs=4,
		type=float,
		metavar=('minx', 'miny', 'maxx', 'maxy'),
		help="Bounding box to extract (in CRS of the raster).",
	)
	parser.add_argument(
		"--overview-level",
		type=int,
		default=0,
		help="Overview level to read (0=full resolution, 1+=overview levels).",
	)
	parser.add_argument(
		"--output",
		default="linz_rasterio_output.tiff",
		help="Local output filename for extracted data.",
	)
	return parser.parse_args()


def main() -> int:
	args = parse_args()

	dataset = LINZ_DATASETS[args.dataset]
	bucket = args.bucket or dataset.bucket
	region = args.region or dataset.region
	output = args.output

	print(f"Using bucket={bucket}, region={region}")
	print(f"Target path: {args.path}")

	session = setup_aws_session()

	try:
		if args.list_prefix:
			print(f"Listing objects under prefix: {args.path}")
			objects = list_s3_objects(bucket, args.path, region)
			
			# Filter for common raster formats
			raster_objects = [
				obj for obj in objects 
				if obj.lower().endswith(('.tif', '.tiff', '.jp2', '.png', '.jpg', '.jpeg'))
			]
			
			if not raster_objects:
				print("No raster files found.")
			else:
				for obj in raster_objects[:20]:  # Show first 20
					print(obj)
				if len(raster_objects) > 20:
					print(f"... and {len(raster_objects) - 20} more files")
				print(f"Total raster files found: {len(raster_objects)}")
		
		else:
			s3_url = build_s3_url(bucket, args.path)
			print(f"Accessing: {s3_url}")
			
			# Read metadata
			info = read_raster_info(s3_url, session)
			
			print("\n=== Raster Information ===")
			print(f"Driver: {info['driver']}")
			print(f"Size: {info['width']} x {info['height']} pixels")
			print(f"Bands: {info['count']}")
			print(f"Data type: {info['dtype']}")
			print(f"CRS: {info['crs']}")
			print(f"Resolution: {info['res'][0]:.6f} x {info['res'][1]:.6f}")
			print(f"Bounds: {info['bounds']}")
			print(f"NoData: {info['nodata']}")
			if any(info['overviews']):
				print(f"Overviews: {info['overviews'][0]}")
			
			if not args.info_only:
				print("\n=== Reading Data ===")
				bbox = tuple(args.bbox) if args.bbox else None
				if bbox:
					print(f"Reading bbox: {bbox}")
				
				data, metadata = read_raster_window(
					s3_url, session, bbox, args.overview_level
				)
				
				print(f"Data shape: {data.shape}")
				print(f"Data range: {data.min():.2f} to {data.max():.2f}")
				print(f"Mean: {data.mean():.2f}")
				
				# Save to local file
				save_raster(data, metadata, output)
				print(f"\n=== Saved to: {output} ===")

	except Exception as exc:
		print(f"Error accessing raster data: {exc}")
		return 1

	return 0


if __name__ == "__main__":
	main()