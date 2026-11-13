AURENIX PRO WINDOWS — Error reporting update V0.6.2

New behavior:
- Exceptions from AI model initialization and individual image processing are recorded
  with tracebacks to LOCALAPPDATA\AURENIX-PRO\Logs\aurenix.log.
- Rotating logs: maximum 2 MB each, plus 4 backup logs.
- Settings > Open Error Logs opens the log folder.
- Settings > Export Error Report saves a copy of the active log to a location selected
  by the user; no reports are sent automatically.
- AI initialization errors show a message and are not added to the image retry queue.
- Failed image processing errors can be retried by using Retry Failed.
- The program installs exception hooks for uncaught Python errors.

Limits:
- This does not automatically fix arbitrary crashes, corrupted images, missing GPU
  drivers, damaged model files or operating system errors.
- QT/C++ native crashes may bypass Python exception hooks.
- Reports may contain local file paths. Review them before sharing.
- No Windows GUI runtime test, real BiRefNet inference test, or installer test was run
  in this environment.
- The prior source package supports PNG export only. JPEG/WebP/TIFF/BMP output
  requested subsequently is still pending implementation.

Local checks:
  python test_source.py
  python test_diagnostics.py

Run with your existing RUN_WINDOWS.bat after installing prerequisites.
