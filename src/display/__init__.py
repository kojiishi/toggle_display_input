__all__ = ["Display", "__version__"]

try:
    from ._version import version as __version__  # type: ignore
except ImportError:
    __version__ = "0.0.0+unknown"

from .display import Display
