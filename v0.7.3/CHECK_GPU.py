"""Preflight check only: CUDA availability is not proof of successful inference."""
import onnxruntime as ort
print('ONNX Runtime:', ort.__version__)
if hasattr(ort, 'preload_dlls'):
    try:
        ort.preload_dlls(directory='')
    except Exception as exc:
        print('CUDA DLL preload warning:', exc)
providers = ort.get_available_providers()
print('Available providers:', providers)
if 'CUDAExecutionProvider' not in providers:
    raise SystemExit('CUDA unavailable. Refusing to label this a GPU build.')
print('CUDA provider registered. Actual BiRefNet CUDA inference still requires validation.')
