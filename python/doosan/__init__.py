"""Python wrapper for the Doosan DRFL robot API.

    from doosan import Robot, cfg
"""

from . import config as cfg
from .robot import Robot, fmt, load_library

__all__ = ["Robot", "cfg", "fmt", "load_library"]
