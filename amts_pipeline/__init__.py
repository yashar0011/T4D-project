from importlib import import_module as _imp
from typing import TYPE_CHECKING

__all__ = ["splitter", "watcher", "settings", "file_profiles"]

for _mod in __all__:
    globals()[_mod] = _imp(f"{__name__}.{_mod}")

del _imp                       # ← keep namespace tidy; _mod deletion not needed

if TYPE_CHECKING:              # pragma: no cover
    from . import splitter, watcher, settings, file_profiles