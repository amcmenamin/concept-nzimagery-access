import duckdb
import logging
from pathlib import Path

try:
	from src.configuration import Config
	from src.named_bboxes import NamedBBoxes
except ModuleNotFoundError:
	from configuration import Config
	from named_bboxes import NamedBBoxes


config = Config()
url_path = config.url_path
layer_name = "airport"
export_folder = Path("exports")

NZ_BBOX_NAMES = (
	"NZ_MAINLAND",
	"CHATHAM_ISLANDS",
	"SNARES_ISLANDS",
	"AUCKLAND_ISLANDS",
	"CAMPBELL_ISLAND",
	"ANTIPODES_ISLANDS",
	"BOUNTY_ISLANDS",
	"RAOUL_ISLAND",
	"MACAULEY_CURTIS_ISLANDS",
)
NAMED_BBOX_CONFIG = NamedBBoxes()


class GeoParquetLayer:
	"""Query a remote GeoParquet 1.1 layer with DuckDB Spatial.

	The layer must expose a native ``geometry`` column and a per-row ``bbox``
	covering with ``xmin``, ``ymin``, ``xmax``, and ``ymax`` fields.
	"""

	BBOXES = NAMED_BBOX_CONFIG
	NZ_BBOXES = {NAMED_BBOX_CONFIG.get_bbox(name) for name in NZ_BBOX_NAMES}
	NAMED_BBOXES = NAMED_BBOX_CONFIG.as_mapping()

	def __init__(
		self,
		url_path: str,
		layer_name: str,
		bbox: str | tuple[float, float, float, float] = "NZ_MAINLAND",
		export_folder: str | Path = export_folder,
	) -> None:
		self.url_path = url_path.rstrip("/")
		self.layer_name = layer_name
		self.bbox = bbox
		self.export_folder = Path(export_folder)

	@property
	def bbox(self) -> tuple[float, float, float, float]:
		"""Return the default bbox used when ``query_bbox()`` has no argument."""
		return self._bbox

	@bbox.setter
	def bbox(self, value: str | tuple[float, float, float, float]) -> None:
		"""Set a named bbox or explicit ``(west, south, east, north)`` extent."""
		if isinstance(value, str):
			self._bbox = self.BBOXES.get_bbox(value)
			return

		west, south, east, north = value
		if west > east or south > north:
			raise ValueError("bbox must be ordered as (west, south, east, north)")
		self._bbox = value

	@property
	def parquet_url(self) -> str:
		"""Return the latest GeoParquet URL for this layer."""
		return (
			f"{self.url_path}/{self.layer_name}/latest/"
			f"{self.layer_name}.parquet"
		)

	@property
	def output_path(self) -> Path:
		"""Return the GeoParquet export path for this layer."""
		return self.export_folder / f"{self.layer_name}.parquet"

	def query_bbox(
		self, bbox: tuple[float, float, float, float] | None = None
	) -> list[tuple[object, ...]]:
		"""Return rows that intersect an explicit or configured default bbox."""
		return self.query_bboxes((self.bbox if bbox is None else bbox,))

	def query_new_zealand(self) -> list[tuple[object, ...]]:
		"""Return rows from mainland New Zealand and selected offshore islands."""
		return self.query_bboxes(self.NZ_BBOXES)

	def query_bboxes(
		self, bboxes: set[tuple[float, float, float, float]]
		| tuple[tuple[float, float, float, float], ...],
	) -> list[tuple[object, ...]]:
		"""Return rows that intersect one or more ``(west, south, east, north)`` bboxes.

		The bbox covering predicate is evaluated before the exact geometry
		intersection, allowing DuckDB to prune non-overlapping data.
		"""
		if not bboxes:
			return []

		conditions = []
		query_parameters: list[object] = [self.parquet_url]
		for west, south, east, north in bboxes:
			conditions.append("""
				(bbox.xmax >= ?
					AND bbox.xmin <= ?
					AND bbox.ymax >= ?
					AND bbox.ymin <= ?
					AND ST_Intersects(
						geometry,
						ST_MakeEnvelope(?, ?, ?, ?)
					)
				)
			""")
			query_parameters.extend(
				[west, east, south, north, west, south, east, north]
			)

		query = "SELECT * FROM read_parquet(?) WHERE " + " OR ".join(conditions)
		connection = duckdb.connect()
		connection.execute("INSTALL spatial")
		connection.execute("LOAD spatial")
		return connection.execute(query, query_parameters).fetchall()

	def export_bbox(
		self, bbox: tuple[float, float, float, float] | None = None
	) -> tuple[Path, str]:
		"""Export the configured or explicit bbox and return its path and SQL."""
		return self.export_bboxes((self.bbox if bbox is None else bbox,))

	def export_new_zealand(self) -> tuple[Path, str]:
		"""Export mainland New Zealand and selected offshore islands with COPY."""
		return self.export_bboxes(self.NZ_BBOXES)

	def export_bboxes(
		self, bboxes: set[tuple[float, float, float, float]]
		| tuple[tuple[float, float, float, float], ...],
	) -> tuple[Path, str]:
		"""Export rows and return the GeoParquet path and executed COPY SQL."""
		if not bboxes:
			raise ValueError("at least one bbox is required for export")

		conditions = []
		query_parameters: list[object] = [self.parquet_url]
		for west, south, east, north in bboxes:
			conditions.append("""
				(bbox.xmax >= ?
					AND bbox.xmin <= ?
					AND bbox.ymax >= ?
					AND bbox.ymin <= ?
					AND ST_Intersects(
						geometry,
						ST_MakeEnvelope(?, ?, ?, ?)
					)
				)
			""")
			query_parameters.extend(
				[west, east, south, north, west, south, east, north]
			)

		select_query = "SELECT * FROM read_parquet(?) WHERE " + " OR ".join(conditions)
		for query_parameter in query_parameters:
			if isinstance(query_parameter, str):
				literal = "'" + query_parameter.replace("'", "''") + "'"
			else:
				literal = str(query_parameter)
			select_query = select_query.replace("?", literal, 1)

		self.export_folder.mkdir(parents=True, exist_ok=True)
		escaped_output_path = str(self.output_path).replace("'", "''")
		copy_query = (
			f"COPY ({select_query}) TO '{escaped_output_path}' "
			"(FORMAT PARQUET, COMPRESSION ZSTD)"
		)
		connection = duckdb.connect()
		connection.execute("INSTALL spatial")
		connection.execute("LOAD spatial")
		connection.execute(copy_query)
		return self.output_path, copy_query


def main() -> None:
	"""Export airports in mainland New Zealand and selected offshore islands."""
	airport_layer = GeoParquetLayer(url_path, layer_name, export_folder=export_folder)
	airport_layer.export_folder.mkdir(parents=True, exist_ok=True)
	logging.basicConfig(
		filename=airport_layer.export_folder / "extract_geoparquet.log",
		level=logging.INFO,
		format="%(asctime)s %(levelname)s %(message)s",
	)
	output_path, copy_query = airport_layer.export_new_zealand()
	print(f"Exported airports to {output_path}")
	logging.info("COPY SQL for %s:\n%s", layer_name, copy_query)


if __name__ == "__main__":
	main()

