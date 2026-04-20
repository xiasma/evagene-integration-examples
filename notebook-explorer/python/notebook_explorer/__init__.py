"""Evagene notebook-explorer helpers.

The notebook (``explorer.ipynb``) is the demo; this package keeps its
setup cells short.  Nothing here is clever — just enough structure to
keep the HTTP transport, the API surface, and the notebook narrative as
three separate concerns.
"""

from .client import EvageneClient
from .config import Config, ConfigError, load_config
from .http_gateway import HttpGateway, HttpxGateway

__all__ = [
    "Config",
    "ConfigError",
    "EvageneClient",
    "HttpGateway",
    "HttpxGateway",
    "load_config",
]
