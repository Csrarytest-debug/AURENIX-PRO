"""Use the BiRefNet model bundled with the PyInstaller Windows distribution."""
import os
import sys
from pathlib import Path

if getattr(sys, "frozen", False):
    base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    model_dir = base / "models"
    if model_dir.is_dir():
        os.environ["U2NET_HOME"] = str(model_dir)
