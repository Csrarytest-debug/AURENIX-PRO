"""PyInstaller runtime hook: use the bundled BiRefNet weights on macOS."""
import os
import sys
from pathlib import Path

if getattr(sys, "frozen", False):
    base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    bundled_models = base / "models"
    if bundled_models.is_dir():
        os.environ["U2NET_HOME"] = str(bundled_models)
