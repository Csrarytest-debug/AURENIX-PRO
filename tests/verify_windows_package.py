"""Static verification only; no GUI, live service or clean-PC runtime test."""
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
bundle = root / "dist" / "AURENIX PRO"
internal = bundle / "_internal"
models = list(internal.rglob("birefnet-general.onnx")) if internal.exists() else []
checks = {
    "Windows EXE": (bundle / "AURENIX PRO.exe").is_file(),
    "PyInstaller internal folder": internal.is_dir(),
    "Bundled BiRefNet General ONNX model": bool(models) and max(p.stat().st_size for p in models) > 100_000_000,
    "ONNX Runtime bundled": bool(list(internal.rglob("onnxruntime*"))),
}
for name, passed in checks.items():
    print(("[PASS] " if passed else "[FAIL] ") + name)
if not all(checks.values()):
    sys.exit("Incomplete Windows bundle: cannot approve installer")
print("Static package checks passed. Clean Windows installation and image-quality tests still required.")
