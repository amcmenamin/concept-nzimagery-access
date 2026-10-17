import duckdb
import logging
from pathlib import Path


url_path = "https://d1jzh93b1t1cv.cloudfront.net/data"
layer_name = "airport"
export_folder = Path("exports")

NAMED_BBOXES = {
	# Approximate mainland New Zealand extent: west, south, east, north.
	"NZ_MAINLAND": (165.8, -47.5, 179.0, -34.0),
	# Regional council areas, sourced from NZ Stats regional boundaries.
	"NORTHLAND_REGION": (172.635244, -36.396343, 174.783576, -34.392630),
	"AUCKLAND_REGION": (174.161835, -37.292621, 175.550653, -35.897461),
	"WAIKATO_REGION": (174.613411, -39.300326, 176.505325, -36.421344),
	"BAY_OF_PLENTY_REGION": (175.805921, -39.005085, 178.107555, -37.267434),
	"GISBORNE_REGION": (177.122171, -38.972812, 178.577243, -37.534248),
	"HAWKES_BAY_REGION": (176.042936, -40.431291, 178.001674, -38.583921),
	"TARANAKI_REGION": (173.751496, -39.868770, 174.991765, -38.706486),
	"MANAWATU_WHANGANUI_REGION": (174.675165, -40.779585, 176.632958, -38.470327),
	"GREATER_WELLINGTON_REGION": (174.613267, -41.613549, 176.332760, -40.659210),
	"WEST_COAST_REGION": (168.052080, -44.499066, 172.692102, -40.774548),
	"CANTERBURY_REGION": (169.542498, -45.080929, 174.063380, -41.907383),
	"OTAGO_REGION": (168.116393, -46.638125, 171.144216, -43.955411),
	"SOUTHLAND_REGION": (166.426132, -47.289993, 169.279166, -44.255121),
	"TASMAN_REGION": (172.050587, -42.305571, 173.304418, -40.498029),
	"NELSON_REGION": (173.189653, -41.393428, 173.598761, -41.051120),
	"MARLBOROUGH_REGION": (172.718529, -42.488130, 174.446856, -40.663444),
	# Chatham Islands
	"CHATHAM_ISLANDS": (-176.893142, -44.356234, -176.154379, -43.692732),
	# Snares Islands
	"SNARES_ISLANDS": (166.4, -48.2, 166.7, -48.0),
	# Auckland Islands
	"AUCKLAND_ISLANDS": (165.7, -51.1, 166.4, -50.4),
	# Campbell Island / Motu Ihupuku
	"CAMPBELL_ISLAND": (168.9, -52.7, 169.3, -52.4),
	# Antipodes Islands
	"ANTIPODES_ISLANDS": (178.6, -49.9, 179.0, -49.5),
	# Bounty Islands
	"BOUNTY_ISLANDS": (178.6, -47.9, 179.2, -47.6),
	# Raoul Island, the northern Kermadec Islands.
	"RAOUL_ISLAND": (-178.1, -29.4, -177.7, -29.1),
	# Macauley and Curtis Islands, the southern Kermadec Islands.
	"MACAULEY_CURTIS_ISLANDS": (178.2, -30.5, 179.0, -29.5),
	# Approximate mapped urban extents; names align with Stats NZ Urban Area labels.
	"AUCKLAND_URBAN_AREA": (174.603180, -37.012095, 174.923180, -36.692095),
	"GREATER_WELLINGTON_URBAN_AREA": (174.617211, -41.448753, 174.937211, -41.128795),
	"CHRISTCHURCH_URBAN_AREA": (172.423982, -43.628593, 172.779772, -43.434618),
	"KAITAIA_URBAN_AREA": (173.223996, -35.154126, 173.303996, -35.074126),
	"WHANGAREI_URBAN_AREA": (174.159420, -35.887527, 174.479420, -35.567527),
	"HAMILTON_URBAN_AREA": (175.184301, -37.846039, 175.344877, -37.699330),
	"TAURANGA_URBAN_AREA": (176.008062, -37.842987, 176.328062, -37.522987),
	"ROTORUA_URBAN_AREA": (176.184793, -38.176858, 176.336733, -38.063082),
	"GISBORNE_URBAN_AREA": (177.860649, -38.821326, 178.180649, -38.501326),
	"NAPIER_HASTINGS_URBAN_AREA": (176.683078, -39.801768, 177.003078, -39.388193),
	"TAUPO_URBAN_AREA": (176.029477, -38.726620, 176.109477, -38.646620),
	"NEW_PLYMOUTH_URBAN_AREA": (173.920647, -39.217994, 174.240647, -38.897994),
	"WHANGANUI_URBAN_AREA": (174.891931, -40.092490, 175.211931, -39.772490),
	"PALMERSTON_NORTH_URBAN_AREA": (175.451239, -40.516317, 175.771239, -40.196317),
	"PARAPARAUMU_URBAN_AREA": (174.966196, -40.954464, 175.046196, -40.874464),
	"WELLINGTON_URBAN_AREA": (174.617211, -41.448753, 174.937211, -41.128795),
	"NELSON_URBAN_AREA": (173.189857, -41.393427, 173.598762, -41.051753),
	"BLENHEIM_URBAN_AREA": (173.914586, -41.551869, 173.994586, -41.471869),
	"GREYMOUTH_URBAN_AREA": (171.167988, -42.489947, 171.247988, -42.409947),
	"TIMARU_URBAN_AREA": (171.210979, -44.433025, 171.290979, -44.353025),
	"DUNEDIN_URBAN_AREA": (170.343576, -46.034098, 170.663576, -45.714098),
	"QUEENSTOWN_URBAN_AREA": (168.621000, -45.072192, 168.701000, -44.992192),
	"INVERCARGILL_URBAN_AREA": (168.195403, -46.625585, 168.542778, -46.322167),
}

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


class GeoParquetLayer:
	"""Query a remote GeoParquet 1.1 layer with DuckDB Spatial.

	The layer must expose a native ``geometry`` column and a per-row ``bbox``
	covering with ``xmin``, ``ymin``, ``xmax``, and ``ymax`` fields.
	"""

	NZ_BBOXES = {NAMED_BBOXES[name] for name in NZ_BBOX_NAMES}
	NAMED_BBOXES = NAMED_BBOXES

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
			try:
				self._bbox = self.NAMED_BBOXES[value]
			except KeyError as error:
				available_names = ", ".join(sorted(self.NAMED_BBOXES))
				raise ValueError(
					f"Unknown bbox name {value!r}. Available names: {available_names}"
				) from error
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

