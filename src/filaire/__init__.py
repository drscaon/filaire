"""Filaire: standard cable assets generator for Physical AI, exporting to OpenUSD."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("filaire")
except PackageNotFoundError:  # running from a source tree without installation
    __version__ = "0.0.0+unknown"

from .catalog import CATEGORIES, JACKETS, PRESETS  # noqa: E402
from .connectors import CONNECTORS  # noqa: E402
from .generator import Scene, Variations, generate_scene, write_outputs  # noqa: E402

__all__ = [
    "CATEGORIES",
    "CONNECTORS",
    "JACKETS",
    "PRESETS",
    "Scene",
    "Variations",
    "__version__",
    "generate_scene",
    "write_outputs",
]
