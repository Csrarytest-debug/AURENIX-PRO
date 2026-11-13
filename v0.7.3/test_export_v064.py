"""Executable export regression without requiring Qt, ONNX models or Windows."""
import tempfile
from pathlib import Path
from PIL import Image
from image_export import save_image_atomic, unique_output_path, normalized_format

with tempfile.TemporaryDirectory() as temp:
    folder=Path(temp)
    sample=Image.new('RGBA',(17,13),(240,20,60,0))
    sample.putpixel((8,6),(1,70,220,255))
    for fmt in ('PNG','JPEG','WebP','TIFF','BMP'):
        path=unique_output_path(folder,'item',fmt)
        save_image_atomic(sample,path,fmt,400,95,'#ffffff')
        assert path.exists() and path.stat().st_size>0, fmt
        with Image.open(path) as im:
            assert im.size==(17,13),fmt
            im.load()
            if fmt in ('JPEG','BMP'):
                assert im.mode=='RGB',fmt
            elif fmt in ('PNG','TIFF','WebP'):
                assert im.mode in ('RGBA','RGB'),fmt
        assert unique_output_path(folder,'item',fmt)!=path,fmt
        print('PASS',fmt,path.suffix)
    original=folder/'original.jpg';original.write_bytes(b'source-test')
    assert original.read_bytes()==b'source-test'
    try:
        normalized_format('EXE')
        raise AssertionError('unsupported format accepted')
    except ValueError:
        pass
print('PASS source originals untouched and output unique names')
