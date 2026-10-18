from pathlib import Path
from typing import Any

import yaml


class Config:
	"""Load layer and URL configuration from the project config directory."""

	def __init__(
		self,
		layer_config: str = "nztopo",
		url_data_path: str = "nztopodev",
		layers: list[str] | tuple[str, ...] | None = None,
		layer_file: str | Path | None = None,
		url_path_config: str | Path | None = None,
		config_folder: str | Path | None = None,
	) -> None:
		self.config_folder = (
			Path(config_folder)
			if config_folder is not None
			else Path(__file__).with_name("config")
		)
		self.layer_config = layer_config
		self.url_data_path = url_data_path
		self.layers = (
			self._layers_from_names(layers)
			if layers is not None
			else self._load_mapping(
				layer_file if layer_file is not None else f"{layer_config}_layers.yml"
			)
		)
		self.url_path_config = (
			url_path_config if url_path_config is not None else "url_data_paths.yml"
		)
		self.url_data_paths = self._load_mapping(self.url_path_config)
		self.url_path = self._get_string(
			self.url_data_paths,
			url_data_path,
			"URL data path",
		)

	def _load_mapping(self, filename: str | Path) -> dict[str, Any]:
		path = Path(filename)
		if not path.is_absolute() and not path.exists():
			path = self.config_folder / path
		with path.open(encoding="utf-8") as config_file:
			values = yaml.safe_load(config_file)
		if not isinstance(values, dict):
			raise ValueError(f"Expected a mapping in {path}")
		return values

	@staticmethod
	def _layers_from_names(layers: list[str] | tuple[str, ...]) -> dict[str, None]:
		if not all(isinstance(layer_name, str) and layer_name for layer_name in layers):
			raise ValueError("layers must contain non-empty strings")
		return {layer_name: None for layer_name in layers}

	@staticmethod
	def _get_string(values: dict[str, Any], key: str, label: str) -> str:
		value = values.get(key)
		if not isinstance(value, str) or not value:
			raise ValueError(f"{label} {key!r} must have a non-empty string value")
		return value

	def get_layer_theme(self, layer_name: str) -> str | None:
		"""Return the configured theme for a layer, if one is defined."""
		value = self.layers.get(layer_name)
		if value is not None and not isinstance(value, str):
			raise ValueError(f"Layer {layer_name!r} must have a string or null theme")
		return value
