"""Stable ASGI launcher for the local workspace app.

This avoids ambiguous ``app.main:app`` imports on machines that already have
another installed package named ``app``.
"""

from __future__ import annotations

import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


ROOT = Path(__file__).resolve().parent
MAIN_FILE = ROOT / "app" / "main.py"
PACKAGE_DIR = ROOT / "app"
PACKAGE_INIT = PACKAGE_DIR / "__init__.py"

# Ensure local imports like ``from app.config import settings`` resolve to this
# repository before any installed package with the same top-level name.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Uvicorn and its dependencies may import a different top-level ``app`` package
# before this module is evaluated. Clear those entries and seed the local
# package explicitly so downstream imports stay pinned to this workspace.
for module_name in list(sys.modules):
    if module_name == "app" or module_name.startswith("app."):
        del sys.modules[module_name]

_package_spec = spec_from_file_location(
    "app",
    PACKAGE_INIT,
    submodule_search_locations=[str(PACKAGE_DIR)],
)
if _package_spec is None or _package_spec.loader is None:
    raise RuntimeError(f"Unable to load local app package from {PACKAGE_INIT}")

_package_module = module_from_spec(_package_spec)
sys.modules["app"] = _package_module
_package_spec.loader.exec_module(_package_module)

_spec = spec_from_file_location("workspace_local_main", MAIN_FILE)
if _spec is None or _spec.loader is None:
    raise RuntimeError(f"Unable to load ASGI app from {MAIN_FILE}")

_module = module_from_spec(_spec)
_spec.loader.exec_module(_module)

app = _module.app
