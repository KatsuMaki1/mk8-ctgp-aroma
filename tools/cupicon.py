"""Build a CTGP cup icon (blue medallion like the 1UP/Hammer/Bomb/Stamp/Pickaxe cups) around any emblem image.

  cupicon.py --emblem flower.png --ctgp-szs ctgp.szs --out icon.bflim [--preview preview.png]

The ring of an existing blue cup icon is kept; the dark disc inside is repainted with the radial gradient measured on those icons and the
emblem (a PNG with transparency) is pasted at its centre.
"""
import argparse, os, sys
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bflim, szs

DISC_R = 68                                   # inside this radius the icon is the dark disc
# (radius, RGB) of the disc background measured on the five blue CTGP cup icons
PROFILE = [(0, (15, 21, 55)), (9, (11, 16, 48)), (15, (10, 14, 43)), (21, (13, 16, 42)), (27, (9, 12, 36)), (33, (5, 6, 27)),
           (51, (4, 5, 24)), (63, (4, 5, 22)), (69, (4, 5, 19))]


def medallion(base, emblem, size=120):
    """base: RGB image of an existing blue cup icon, emblem: RGBA image -> RGB image (200x200)"""
    a = np.array(base.convert('RGB')).astype(float); h, w = a.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]; r = np.hypot(xx - (w - 1) / 2, yy - (h - 1) / 2)
    xs, cols = [p[0] for p in PROFILE], np.array([p[1] for p in PROFILE], dtype=float)
    disc = np.stack([np.interp(r, xs, cols[:, c]) for c in range(3)], axis=-1)
    inside = np.clip((DISC_R - r) / 2.0 + 0.5, 0, 1)[..., None]          # 2px soft edge against the ring
    a = a * (1 - inside) + disc * inside
    em = emblem.convert('RGBA'); s = size / em.height
    em = em.resize((max(1, round(em.width * s)), size), Image.LANCZOS)
    canvas = Image.fromarray(a.astype('uint8'), 'RGB').convert('RGBA')
    canvas.alpha_composite(em, ((w - em.width) // 2, (h - em.height) // 2 - 2))
    return canvas.convert('RGB')


def build(emblem_path, ctgp_szs, base_name='Stamp', size=120):
    files = {n: b for n, b, h in szs.sarc_read(szs.yaz0_decode(open(ctgp_szs, 'rb').read()))}
    tmpl = files['timg/ym_CupIcon%s^h.bflim' % base_name]
    base, _ = bflim.decode(tmpl)
    img = medallion(base, Image.open(emblem_path), size)
    return bflim.encode_raw565(bflim.rgb_to_565(img), tmpl), img


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--emblem', required=True); ap.add_argument('--ctgp-szs', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--preview'); ap.add_argument('--size', type=int, default=120)
    a = ap.parse_args(); data, img = build(a.emblem, a.ctgp_szs, size=a.size)
    open(a.out, 'wb').write(data)
    if a.preview: img.save(a.preview)
    print('wrote', a.out, len(data), 'bytes')


# ------------------------------------------------------------------ put an icon into ui/cmn/ctgp.szs
import struct

ANIM = 'anim/mn_L_CupSlctBtn_00_IconChange.bflan'      # texture-pattern animation of the cup button: frame N -> icon texture
FIRST_CTGP_FRAME = 24                                  # frames 24..29 = CTGP icon slots 0..5 (cup0 `icon` field)


def bflan_set_icon(anim, tex_name, frame):
    """add `tex_name` to the animation's texture list and make `frame` use it; returns the new BFLAN bytes"""
    assert anim[:4] == b'FLAN'
    p = 20
    while anim[p:p + 4] != b'pai1': p += struct.unpack('>I', anim[p + 4:p + 8])[0]
    psize, = struct.unpack('>I', anim[p + 4:p + 8]); pai = bytearray(anim[p:p + psize])
    frame_size, flags, pad, ntex, nent, ent_off = struct.unpack('>HBBHHI', pai[8:20])
    # 1. keyframe of the cup icon pattern (the entry whose name is P_CupIcon_00, tag FLTP): 8-byte keys {f32 frame, u16 texture, u16 pad}
    table = struct.unpack('>%dI' % nent, pai[ent_off:ent_off + 4 * nent])
    for eo in table:
        if pai[eo:eo + 12] == b'P_CupIcon_00': break
    else: raise ValueError('P_CupIcon_00 not found')
    tag = eo + 0x24; assert pai[tag:tag + 4] == b'FLTP'
    nkeys, = struct.unpack('>H', pai[tag + 0x10:tag + 0x12]); keys = tag + 0x18
    for k in range(nkeys):
        if struct.unpack('>f', pai[keys + 8 * k:keys + 8 * k + 4])[0] == frame:
            struct.pack_into('>H', pai, keys + 8 * k + 4, ntex); break
    else: raise ValueError('frame %d not in the animation' % frame)
    # 2. append the texture name: table grows by 4, strings by len+NUL padded to 4; everything behind shifts
    old_offs = list(struct.unpack('>%dI' % ntex, pai[20:20 + 4 * ntex])); strings = bytes(pai[20 + 4 * ntex:ent_off])
    name = tex_name.encode() + b'\0'; name += b'\0' * (-len(name) % 4); delta = 4 + len(name)
    new_offs = [o + 4 for o in old_offs] + [(ent_off - 20) + 4]
    head = bytearray(pai[:20]); struct.pack_into('>I', head, 4, psize + delta); struct.pack_into('>H', head, 12, ntex + 1); struct.pack_into('>I', head, 16, ent_off + delta)
    ent_table = struct.pack('>%dI' % nent, *[e + delta for e in table])
    new_pai = bytes(head) + struct.pack('>%dI' % (ntex + 1), *new_offs) + strings + name + ent_table + bytes(pai[ent_off + 4 * nent:])
    out = bytearray(anim[:p]) + new_pai + anim[p + psize:]
    struct.pack_into('>I', out, 12, len(out))
    return bytes(out)


def install_icon(ctgp_szs, out_szs, bflim_data, icon_idx, name):
    raw = szs.yaz0_decode(open(ctgp_szs, 'rb').read()); info, _, ver = szs.sarc_info(raw)
    files = [(n, d) for n, d, h, a in info]; aligns = szs.sarc_aligns(raw)
    tex = 'timg/%s^h.bflim' % name
    files = [(n, d) for n, d in files if n != tex] + [(tex, bflim_data)]
    aligns[tex] = max(0x20, bflim.footer(bflim_data)['align'])
    names = dict(files); base_anim = names[ANIM]
    if (name + '^h.bflim').encode() in base_anim: raise SystemExit('this icon name is already in the animation; use another name or start from the original ctgp.szs')
    names[ANIM] = bflan_set_icon(base_anim, name + '^h.bflim', FIRST_CTGP_FRAME + icon_idx)
    out = szs.sarc_write(list(names.items()), aligns, ver)
    open(out_szs, 'wb').write(szs.yaz0_store(out))
    return len(out)
