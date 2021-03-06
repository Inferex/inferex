""" Top-level package for Inferex CLI """

__app_name__ = "inferex"
__version__ = "0.0.5"

from inferex.api.client import Client
from inferex.decorator.inferex import pipeline

__all__ = [
    "Client",
    "pipeline",
]
