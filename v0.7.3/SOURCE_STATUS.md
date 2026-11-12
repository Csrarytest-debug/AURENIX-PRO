# AURENIX PRO BG Remover V0.7.3 — source synchronization (in progress)

This branch is a staging area for the November 12, 2026 V0.7.3 source snapshot.

**Do not build a release from this branch yet.** The full 56-entry source archive has not been committed here. The original `main` branch is preserved unchanged.

Uploaded so far:
- `v0.7.3/wire_cleanup.py` — conservative alpha-mask wire trimming. It does **not** perform semantic cable recognition or inpainting, and is not guaranteed to remove wires crossing equipment.

Known unresolved release blockers:
- ONNX Runtime CUDA provider fails initialization with Windows WinError 1114 in both the Python environment and packaged EXE.
- RAM/GPU stability is not certified.
- Automatic wire removal on real product photographs is not validated.
- Final Windows EXE/installer is not certified.

The authoritative complete source package in the ChatGPT working environment is `AURENIX_PRO_V073_CUDA12_ROBOCOPY_FIXED_2026-11-12.zip` (56 entries). Additional repair tools were generated after that snapshot; these are not a verified release.
