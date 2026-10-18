from pathlib import Path
from typing import Mapping

import yaml


BBox = tuple[float, float, float, float]


class NamedBBoxes:
	"""Load named bounding boxes from a ``{name}_names_bboxes.yml`` file."""

	def __init__(self, name: str = "nz", config_folder: str | Path | None = None) -> None:
		self.name = name
		self.config_folder = (
			Path(config_folder)
			if config_folder is not None
			else Path(__file__).with_name("config")
		)
		self.path = self.config_folder / f"{name}_names_bboxes.yml"
		self.bboxes = self._load()

	def _load(self) -> dict[str, BBox]:
		with self.path.open(encoding="utf-8") as config_file:
			values = yaml.safe_load(config_file)
		if not isinstance(values, dict):
			raise ValueError(f"Expected a mapping in {self.path}")

		bboxes: dict[str, BBox] = {}
		for bbox_name, value in values.items():
			if not isinstance(bbox_name, str) or not isinstance(value, list) or len(value) != 4:
				raise ValueError(
					f"Expected {bbox_name!r} in {self.path} to contain four coordinates"
				)
			if not all(isinstance(coordinate, (int, float)) for coordinate in value):
				raise ValueError(f"Expected numeric coordinates for {bbox_name!r}")
			bboxes[bbox_name] = tuple(float(coordinate) for coordinate in value)  # type: ignore[assignment]
		return bboxes

	def get_bbox(self, name: str) -> BBox:
		"""Return a named bbox or raise a useful error for an unknown name."""
		try:
			return self.bboxes[name]
		except KeyError as error:
			available_names = ", ".join(sorted(self.bboxes))
			raise ValueError(
				f"Unknown bbox name {name!r}. Available names: {available_names}"
			) from error

	def __getitem__(self, name: str) -> BBox:
		return self.get_bbox(name)

	def names(self) -> tuple[str, ...]:
		"""Return available bbox names in sorted order."""
		return tuple(sorted(self.bboxes))

	def as_mapping(self) -> Mapping[str, BBox]:
		"""Return the loaded named bboxes."""
		return self.bboxes
