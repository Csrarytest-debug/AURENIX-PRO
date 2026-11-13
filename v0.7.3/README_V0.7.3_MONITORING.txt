AURENIX PRO BG Remover V0.7.3 — Windows source monitoring update

Changes:
* Enlarged GPU/RAM panels with equal left/right header wings to retain centered title.
* GPU usage %, dedicated VRAM used/total in MiB, RAM usage and total in GB.
* AI CUDA availability indicator; availability does NOT prove the inference session uses GPU.
* No processing engine or AI provider installation changes in this patch.

IMPORTANT: Your existing environment reported AzureExecutionProvider and CPUExecutionProvider only.
To enable accelerated AI, create/test a separate ONNX Runtime GPU environment compatible with CUDA/cuDNN. Do not overwrite your working CPU environment.

No native Windows GUI or BiRefNet test was performed here. This is NOT a finished installer.
Launch the app via aurenix_pro.py, not background_remover_pro.py.
