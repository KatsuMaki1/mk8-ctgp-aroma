#!/usr/bin/env python3
"""Make a track preview picture (custom/cPict_<dir>.bflim, 304x256 BC1) from any screenshot.

  cpict.py --image shot.png --template <an existing cPict_*.bflim> --out cPict_Gu_MyTrack.bflim [--preview check.png]

The game shows the picture in a 288x164 window at (8,28) of the 304x256 texture; the screenshot is cropped to fill it.
"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bflim
from PIL import Image, ImageOps

RECT = (8, 28, 296, 192)


def from_image(path, template_bytes):
    f = bflim.footer(template_bytes); assert (f['w'], f['h']) == (304, 256), 'template is not a 304x256 preview picture'
    src = ImageOps.fit(Image.open(path).convert('RGB'), (RECT[2] - RECT[0], RECT[3] - RECT[1]), Image.LANCZOS)
    canvas = Image.new('RGB', (304, 256), (0, 0, 0)); canvas.paste(src, RECT[:2])
    return bflim.encode_bc1(canvas, template_bytes), canvas


def install(content, course_dir, image):
    """screenshot -> <content>/custom/cPict_<course_dir>.bflim (uses an existing preview as the format template); returns the cup0 path"""
    cust = os.path.join(content, 'custom'); os.makedirs(cust, exist_ok=True)
    have = sorted(f for f in os.listdir(cust) if f.startswith('cPict_') and f.endswith('.bflim'))
    if not have: raise SystemExit('no existing cPict_*.bflim in %s to use as a format template' % cust)
    data, _ = from_image(image, open(os.path.join(cust, have[0]), 'rb').read())
    rel = 'custom/cPict_%s.bflim' % course_dir; open(os.path.join(content, rel), 'wb').write(data)
    return rel


IMAGE_EXT = ('.png', '.jpg', '.jpeg', '.webp', '.bmp')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--image', required=True); ap.add_argument('--template', required=True); ap.add_argument('--out', required=True); ap.add_argument('--preview')
    a = ap.parse_args(); data, canvas = from_image(a.image, open(a.template, 'rb').read()); open(a.out, 'wb').write(data)
    if a.preview: bflim.decode_bc1(data).save(a.preview)
    print('wrote', a.out, len(data), 'bytes')
