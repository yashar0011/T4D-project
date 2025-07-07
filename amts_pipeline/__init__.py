"""
AMTS-Pipeline package – expose sub-modules on demand.
"""

# By explicitly importing the modules here, we make them available
# as attributes of the 'amts_pipeline' package in a standard, predictable way.
# This resolves the conflict with the `python -m` command and eliminates
# the RuntimeWarning.

from . import splitter
from . import watcher
from . import settings
from . import file_profiles
from . import cleaner
from . import cache_utils
from . import log_utils

# This list tells tools what modules are intended to be public
# when someone does `from amts_pipeline import *`.
__all__ = [
    "splitter",
    "watcher",
    "settings",
    "file_profiles",
    "cleaner",
    "cache_utils",
    "log_utils",
]