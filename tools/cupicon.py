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
# (the icon shown for a cup is animation frame <cup_id>; see set_icons below)


# ------------------------------------------------------------------ icons for ANY cup id (frame number = cup_id)
def bflan_set_icons(anim, mapping, filler=None):
    """mapping {cup_id: texture name 'ym_CupIcon<X>^h.bflim'}. The animation shows frame <cup_id>, so the key list is extended up to the highest id;
    frames nobody uses get `filler` (a texture name that already exists in the animation; default: the first one)."""
    p = 20
    while anim[p:p + 4] != b'pai1': p += struct.unpack('>I', anim[p + 4:p + 8])[0]
    psize, = struct.unpack('>I', anim[p + 4:p + 8]); pai = bytearray(anim[p:p + psize])
    frame_size, flags, pad, ntex, nent, ent_off = struct.unpack('>HBBHHI', pai[8:20])
    table = list(struct.unpack('>%dI' % nent, pai[ent_off:ent_off + 4 * nent]))
    old_offs = list(struct.unpack('>%dI' % ntex, pai[20:20 + 4 * ntex])); strings = bytes(pai[20 + 4 * ntex:ent_off])
    names = [bytes(pai[20 + o:pai.index(b'\0', 20 + o)]).decode() for o in old_offs]
    for n in mapping.values():                                         # add the textures that are not listed yet
        if n not in names:
            b = n.encode() + b'\0'; b += b'\0' * (-len(b) % 4); names.append(n); strings += b
    new_offs = []; pos = 4 * len(names)
    for n in names: new_offs.append(pos); pos += len(n.encode()) + 1; pos += -(len(n.encode()) + 1) % 4
    # the string area may carry its own padding: rebuild it from scratch
    strings = b''.join((n.encode() + b'\0').ljust((len(n.encode()) + 1 + 3) // 4 * 4, b'\0') for n in names)
    delta = (20 + 4 * len(names) + len(strings)) - ent_off
    eo2 = ent_off + delta; ent_table = struct.pack('>%dI' % nent, *[e + delta for e in table])
    body = bytes(pai[ent_off + 4 * nent:])                              # entries (relative offsets inside): unchanged
    # key list of the icon entry (the last entry in the file)
    for k, e in enumerate(table):
        if bytes(pai[e:e + 12]) == b'P_CupIcon_00': icon_entry = e; break
    else: raise ValueError('P_CupIcon_00 not found')
    tag = icon_entry + 0x24; assert pai[tag:tag + 4] == b'FLTP'
    nk, = struct.unpack('>H', pai[tag + 0x10:tag + 0x12]); keys0 = tag + 0x18
    assert tag + 0x18 + 8 * nk == len(pai), 'the icon entry must be the last one'
    cur = {int(struct.unpack('>f', pai[keys0 + 8 * i:keys0 + 8 * i + 4])[0]): struct.unpack('>H', pai[keys0 + 8 * i + 4:keys0 + 8 * i + 6])[0] for i in range(nk)}
    last = max(max(cur), max(mapping)); fill = names.index(filler) if filler in names else cur.get(0, 0)
    keys = b''
    for f in range(last + 1):
        t = names.index(mapping[f]) if f in mapping else cur.get(f, fill)
        keys += struct.pack('>fHH', float(f), t, 0)
    # entries part with the new key list; positions are relative to the old ent_off
    icon_tag_rel = tag - ent_off - 4 * nent                              # where the key header sits inside `body`
    body = bytearray(body[:icon_tag_rel + 0x18]) + keys
    struct.pack_into('>H', body, icon_tag_rel + 0x10, last + 1)
    head = bytearray(pai[:20]); struct.pack_into('>H', head, 8, max(frame_size, last + 1)); struct.pack_into('>H', head, 12, len(names)); struct.pack_into('>I', head, 16, eo2)
    new_pai = bytes(head) + struct.pack('>%dI' % len(names), *new_offs) + strings + ent_table + bytes(body)
    new_pai = bytearray(new_pai); struct.pack_into('>I', new_pai, 4, len(new_pai))
    out = bytearray(anim[:p]) + new_pai + anim[p + psize:]
    struct.pack_into('>I', out, 12, len(out)); return bytes(out)


def set_icons(ctgp_szs, out_szs, icons, filler='ym_CupIconBanana^h.bflim'):
    """icons: {cup_id: (texture name without ^h.bflim, BFLIM bytes or None if the texture already exists)}; reads ctgp_szs, writes out_szs"""
    raw = szs.yaz0_decode(open(ctgp_szs, 'rb').read()); info, _, ver = szs.sarc_info(raw)
    files = {n: d for n, d, h, a in info}; aligns = szs.sarc_aligns(raw)
    for cid, (name, data) in icons.items():
        if data is not None:
            tex = 'timg/%s^h.bflim' % name; files[tex] = data; aligns[tex] = max(0x20, bflim.footer(data)['align'])
    files[ANIM] = bflan_set_icons(files[ANIM], {cid: name + '^h.bflim' for cid, (name, d) in icons.items()}, filler)
    open(out_szs, 'wb').write(szs.yaz0_store(szs.sarc_write(list(files.items()), aligns, ver)))


def letter_icon(cup_name, ctgp_szs):
    """a default icon for a new cup: the blue medallion with the first letters of its name; -> (texture name, BFLIM bytes)"""
    import io, re
    from PIL import ImageDraw, ImageFont
    text = (re.sub(r'[^A-Za-z0-9]', '', cup_name)[:2] or '?').upper()
    em = Image.new('RGBA', (256, 256), (0, 0, 0, 0)); d = ImageDraw.Draw(em)
    font = None
    for f in ('C:/Windows/Fonts/arialbd.ttf', 'C:/Windows/Fonts/arial.ttf'):
        if os.path.exists(f): font = ImageFont.truetype(f, 170 if len(text) == 1 else 130); break
    font = font or ImageFont.load_default()
    w, h = d.textbbox((0, 0), text, font=font)[2:]; x, y = (256 - w) // 2, (256 - h) // 2 - 12
    d.text((x + 6, y + 6), text, font=font, fill=(0, 0, 0, 150)); d.text((x, y), text, font=font, fill=(250, 250, 250, 255))
    buf = io.BytesIO(); em.save(buf, 'PNG'); buf.seek(0)
    data, _ = build(buf, ctgp_szs)
    return 'ym_CupIcon' + (re.sub(r'[^A-Za-z0-9]', '', cup_name)[:12] or 'Cup'), data
