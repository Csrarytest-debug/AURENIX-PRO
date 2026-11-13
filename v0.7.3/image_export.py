"""Deterministic, non-overwriting, atomic image export for AURENIX PRO."""
import os
import tempfile
from pathlib import Path
from PIL import Image

EXTENSIONS = {'PNG': '.png', 'JPEG': '.jpg', 'WEBP': '.webp', 'TIFF': '.tiff', 'BMP': '.bmp'}

def normalized_format(value):
    fmt = str(value).lstrip('.').upper()
    if fmt in ('JPG', 'JPE'): fmt = 'JPEG'
    if fmt in ('TIF',): fmt = 'TIFF'
    if fmt not in EXTENSIONS:
        raise ValueError(f'Unsupported output format: {value}')
    return fmt

def unique_output_path(folder, stem, fmt):
    fmt = normalized_format(fmt)
    folder = Path(folder)
    # Filename may originate from an external source. Do not permit path traversal.
    stem = Path(str(stem)).name or 'image'
    path = folder / (stem + EXTENSIONS[fmt])
    i = 2
    while path.exists():
        path = folder / f'{stem}_{i}{EXTENSIONS[fmt]}'
        i += 1
    return path

def save_image_atomic(image, target, fmt, dpi=400, quality=95, bg='#ffffff'):
    fmt = normalized_format(fmt)
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    if dpi <= 0 or not 1 <= quality <= 100:
        raise ValueError('Invalid DPI or quality setting')
    rgba = image.convert('RGBA')
    opts = {}
    if fmt in ('JPEG', 'BMP'):
        canvas = Image.new('RGBA', rgba.size, bg)
        canvas.alpha_composite(rgba)
        image_out = canvas.convert('RGB')
    else:
        image_out = rgba
    if fmt == 'JPEG': opts.update(quality=quality, subsampling=0)
    elif fmt == 'WEBP': opts.update(quality=quality, method=4)
    elif fmt == 'PNG': opts.update(compress_level=6)
    if fmt in ('PNG', 'JPEG', 'TIFF'):
        opts['dpi'] = (dpi, dpi)
    # Use mkstemp in destination folder for atomic same-volume rename.
    fd, tmp = tempfile.mkstemp(prefix='.aurenix_', suffix='.partial', dir=target.parent)
    os.close(fd)
    try:
        image_out.save(tmp, format=fmt, **opts)
        os.replace(tmp, target)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)
    return target
