# AURENIX PRO BG Remover V0.7.3 — source sync verified

**Source upload: COMPLETE.** The full November 12, 2026 source snapshot has been committed under `v0.7.3/`.

- Archive: `AURENIX_PRO_V073_CUDA12_ROBOCOPY_FIXED_2026-11-12.zip`
- Verified on 2026-11-13: **56 of 56 files** match their original Git blob SHA-1 exactly, including the BS Broadcast PNG.
- Source sync commit: `3d6908ff93914c7113c49679d488bee0775e92b7`.
- The original `main` branch remains unchanged; this is the V0.7.3 staging branch.
- CI: `.github/workflows/aurenix-v073-windows-candidate.yml` builds a **candidate**, not a certified release.

## Release blockers

- GitHub-hosted Windows runners do not verify NVIDIA RTX 4050 hardware or the reported ONNX Runtime CUDA WinError 1114.
- Real photographs must still validate cable removal, product-label preservation, and output quality.
- Sustained RAM/GPU stability, clean-Windows-PC installation, and final EXE/installer operation remain unverified.
- A passing source regression suite does not establish release certification.

**Do not mark the release final until the above checks pass.**
