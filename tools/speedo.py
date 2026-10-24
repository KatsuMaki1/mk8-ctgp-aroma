#!/usr/bin/env python3
"""Give CTGP-Café's speedometer the look of the game's own lap / coin counters: a third dark pill in the bottom-left bar, a gauge icon and
italic digits (turbo_PointNum), no "km/h".

  speedo.py install --base-game <MK8 content dir> --content <content dir with ui/cmn/ctgp.szs> [--release <dir with Data.bin> --data-out <dir>]

What it edits (everything is rebuilt from the game's own layout pieces, nothing is hand-drawn except the icon):
  * ui/cmn/ctgp.szs: blyt/rc_RaceView_1P_00.bflyt (CTGP's race HUD layout) gets a window pane copied from the lap counter's pill, an icon picture pane
    and a re-styled text pane `L_Speedometer_00` (the one CTGP's code writes the speed into), plus 3 textures (pill gradients + the new gauge icon);
  * with --release/--data-out: Data.bin with the format string "%.0f km/h" turned into "%.0f" (same size) so only the number is shown.
Tuning knobs are the constants below (layout units: 1280x720, centre = 0,0, y up).
"""
import argparse, os, shutil, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bflim, szs
from PIL import Image, ImageDraw

PILL_X, PILL_Y = -254.0, -299.0         # pill centre
PILL_W = 140.0                          # pill width before the 0.9 scale (the lap pill is 160 wide)
SCALE = 0.9
ICON_DX, ICON_SIZE = -40.0, 40.0        # icon centre relative to the pill centre (layout units) and its size
TEXT_DX = 22.0                          # text centre relative to the pill centre
TEXT_W, TEXT_H = 70.0, 44.0

LAPCOIN = 'blyt/rc_L_LapCoin_00.bflyt'
RACEVIEW = 'blyt/rc_RaceView_1P_00.bflyt'
ICON_TEX = 'ym_SpeedIcon_00^l'
TEXS = ['tc_RcPnt_GrdBase_L^t', 'tc_RcPnt_GrdBase_R^t', ICON_TEX]


# ------------------------------------------------------------------ BFLYT plumbing
def split(d):
    hdr = d[:20]; o = 20; out = []
    while o < len(d):
        s = struct.unpack('>I', d[o + 4:o + 8])[0]; out.append([d[o:o + 4].decode('latin1'), bytearray(d[o:o + s])]); o += s
    return hdr, out


def join(hdr, secs):
    body = b''.join(bytes(s) for _, s in secs); h = bytearray(hdr)
    struct.pack_into('>I', h, 12, 20 + len(body)); struct.pack_into('>H', h, 16, len(secs))
    return bytes(h) + body


def cstr(b): return bytes(b).split(b'\0')[0].decode('latin1')
def pane_name(s): return cstr(s[12:36])
def sec(tag, body):
    body = bytes(body) + b'\0' * (-(8 + len(body)) % 4); return [tag, bytearray(tag.encode() + struct.pack('>I', 8 + len(body)) + body)]


def read_txl1(s):
    n = struct.unpack('>H', s[8:10])[0]; offs = struct.unpack('>%dI' % n, s[12:12 + 4 * n]); return [cstr(s[12 + o:]) for o in offs]


def make_txl1(names):
    n = len(names); table = 4 * n; strs = b''; offs = []
    for x in names: offs.append(table + len(strs)); strs += x.encode() + b'\0'
    return sec('txl1', struct.pack('>HH', n, 0) + struct.pack('>%dI' % n, *offs) + strs)


def read_mat1(s):
    n = struct.unpack('>H', s[8:10])[0]; offs = list(struct.unpack('>%dI' % n, s[12:12 + 4 * n])) + [len(s)]
    return [bytes(s[offs[i]:offs[i + 1]]) for i in range(n)]


def make_mat1(mats):
    n = len(mats); start = 12 + 4 * n; offs = []; pos = start
    for m in mats: offs.append(pos); pos += len(m)
    body = struct.pack('>HH', n, 0) + struct.pack('>%dI' % n, *offs) + b''.join(mats)
    return sec('mat1', body)


def make_fnl1(fonts):
    n = len(fonts); table = 4 * n; strs = b''; offs = []
    for x in fonts: offs.append(table + len(strs)); strs += x.encode() + b'\0'
    return sec('fnl1', struct.pack('>HH', n, 0) + struct.pack('>%dI' % n, *offs) + strs)


def set_pane(s, name=None, pos=None, scale=None, size=None):
    if name is not None: s[12:36] = name.encode().ljust(24, b'\0')
    if pos is not None: struct.pack_into('>2f', s, 0x2C, *pos)
    if scale is not None: struct.pack_into('>2f', s, 0x44, *scale)
    if size is not None: struct.pack_into('>2f', s, 0x4C, *size)


# ------------------------------------------------------------------ the gauge icon
def draw_icon(px=48, ss=8):
    import math
    S = px * ss; im = Image.new('RGBA', (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    cx, cy, r = S / 2, S * 0.56, S * 0.40
    white, grey = (246, 246, 246, 255), (150, 150, 150, 255)
    d.pieslice([cx - r, cy - r, cx + r, cy + r], 180 + 0, 360, fill=(0, 0, 0, 0))
    d.arc([cx - r, cy - r, cx + r, cy + r], 160, 380, fill=white, width=int(S * 0.085))
    for k in range(7):                                           # tick marks
        a = math.radians(160 + k * 220 / 6); r0, r1 = r * 0.72, r * 0.9
        d.line([(cx + r0 * math.cos(a), cy + r0 * math.sin(a)), (cx + r1 * math.cos(a), cy + r1 * math.sin(a))], fill=white, width=int(S * 0.04))
    a = math.radians(300)                                          # needle
    d.line([(cx, cy), (cx + r * 0.78 * math.cos(a), cy + r * 0.78 * math.sin(a))], fill=white, width=int(S * 0.07))
    d.ellipse([cx - S * 0.075, cy - S * 0.075, cx + S * 0.075, cy + S * 0.075], fill=white, outline=grey, width=int(S * 0.012))
    return im.resize((px, px), Image.LANCZOS)


# ------------------------------------------------------------------ build
def build(base_race, ctgp_in, ctgp_out, preview=None):
    base = {h: d for n, d, h, a in szs.sarc_info(szs.yaz0_decode(open(base_race, 'rb').read()))[0]}
    get = lambda name: base[szs.sarc_hash(name)]
    raw = szs.yaz0_decode(open(ctgp_in, 'rb').read()); info, _, ver = szs.sarc_info(raw)
    files = {n: d for n, d, h, a in info}; aligns = szs.sarc_aligns(raw)

    # --- source pieces from the lap/coin counter
    lh, lsecs = split(get(LAPCOIN)); ltex = read_txl1(next(s for t, s in lsecs if t == 'txl1')); lmat = read_mat1(next(s for t, s in lsecs if t == 'mat1'))
    mat_by_name = {cstr(m[:28]).strip(): i for i, m in enumerate(lmat)}
    wnd = {pane_name(s): s for t, s in lsecs if t == 'wnd1'}
    pic = {pane_name(s): s for t, s in lsecs if t == 'pic1'}

    # --- CTGP race HUD layout
    hdr, secs = split(files[RACEVIEW]); assert pane_name(next(s for t, s in secs if t == 'txt1')) == 'L_Speedometer_00'
    if any(t == 'txl1' for t, _ in secs): raise SystemExit('this ctgp.szs already has the speedometer layout; start from the original ctgp.szs (.bak)')
    new_tex = []
    def tex_idx(n):
        if n not in new_tex: new_tex.append(n)
        return new_tex.index(n)
    mats = read_mat1(next(s for t, s in secs if t == 'mat1')); first_new = len(mats); added = []

    def clone_material(name):
        m = bytearray(lmat[mat_by_name[name]]); flags = struct.unpack('>I', m[36:40])[0] if len(m) > 36 else 0
        for k in range(flags & 3):                                  # texture maps: re-point to the new texture list
            o = 40 + 4 * k; ti = struct.unpack('>H', m[o:o + 2])[0]
            m[o:o + 2] = struct.pack('>H', tex_idx(ltex[ti]))
        added.append(bytes(m)); return first_new + len(added) - 1

    def clone_wnd(src_name, dst_name, pos, size, kind):
        s = bytearray(wnd[src_name]); set_pane(s, dst_name, pos, (SCALE, SCALE) if kind == '00' else (1.0, 1.0), size)
        content = struct.unpack('>I', s[0x68:0x6C])[0]; frames = struct.unpack('>I', s[0x6C:0x70])[0]; assert content == 0x70 and frames == 0x84
        names = [n for n in mat_by_name if n.startswith('W_FlagBase_' + kind)]
        c = next(n for n in names if n.endswith('C')); order = [c] + [next(n for n in names if n.endswith(e)) for e in ('LT', 'RT', 'LB', 'RB')]
        assert struct.unpack('>H', s[0x80:0x82])[0] == mat_by_name[order[0]]
        new_idx = [clone_material(n) for n in order]
        struct.pack_into('>H', s, 0x80, new_idx[0])
        for k in range(4): struct.pack_into('>H', s, 0x94 + 4 * k, new_idx[1 + k])
        return s

    w0 = clone_wnd('W_FlagBase_00', 'W_Speedo_00', (PILL_X, PILL_Y), (PILL_W, 72.0), '00')
    w1 = clone_wnd('W_FlagBase_01', 'W_Speedo_01', (4.0, 0.0), (PILL_W - 6, 65.0), '01')
    icon = bytearray(pic['P_Lap_00']); set_pane(icon, 'P_Speedo_00', (PILL_X + ICON_DX * SCALE, PILL_Y), (1.0, 1.0), (ICON_SIZE, ICON_SIZE))
    assert struct.unpack('>H', icon[0x64:0x66])[0] == mat_by_name['P_Lap_00']
    m = bytearray(lmat[mat_by_name['P_Lap_00']]); m[40:42] = struct.pack('>H', tex_idx(ICON_TEX + '.bflim')); added.append(bytes(m))
    struct.pack_into('>H', icon, 0x64, first_new + len(added) - 1)

    # --- the text pane CTGP's code fills in: same style as the coin / lap digits
    txt = next(s for t, s in secs if t == 'txt1')
    set_pane(txt, None, (PILL_X + TEXT_DX * SCALE, PILL_Y), None, (TEXT_W, TEXT_H))
    struct.pack_into('>H', txt, 0x5A, 1)                                           # font index 1 = turbo_PointNum.bffnt
    struct.pack_into('>f', txt, 0x60, 0.22)                                        # italic
    txt[0x68:0x70] = bytes.fromhex('ffffffff969696ff')                             # white -> grey, like T_Coin_00
    struct.pack_into('>2f', txt, 0x70, 31.11, 38.76)                               # font size

    out = []
    for t, s in secs:
        if t == 'lyt1': out.append([t, s]); out.append(make_txl1(new_tex))
        elif t == 'fnl1': out.append(make_fnl1(['turbo_messageFontOutline_50.bffnt', 'turbo_PointNum.bffnt']))
        elif t == 'mat1': out.append(make_mat1(mats + added))
        elif t == 'txt1':
            out += [[ 'wnd1', w0], sec('pas1', b''), ['wnd1', w1], sec('pae1', b''), ['pic1', icon], [t, s]]
        else: out.append([t, s])
    files[RACEVIEW] = join(hdr, out)
    for n in [t[:-6] for t in new_tex]:
        name = 'timg/%s.bflim' % n
        if n == ICON_TEX:
            tmpl = get('timg/ym_Coin_00^l.bflim'); img = draw_icon(48)
            files[name] = bflim.encode_rgba8(img, tmpl)
            if preview: img.resize((192, 192), Image.NEAREST).save(preview)
        else: files[name] = get(name)
        aligns[name] = max(0x20, bflim.footer(files[name])['align'])
    aligns[RACEVIEW] = aligns.get(RACEVIEW, 4)
    open(ctgp_out, 'wb').write(szs.yaz0_store(szs.sarc_write(list(files.items()), aligns, ver)))


def patch_data(release, out):
    """Data.bin: "%.0f km/h" -> "%.0f" (same length, NUL padded)"""
    os.makedirs(out, exist_ok=True)
    for f in os.listdir(release): shutil.copy2(os.path.join(release, f), os.path.join(out, f))
    p = os.path.join(out, 'Data.bin'); b = bytearray(open(p, 'rb').read()); old = b'%.0f km/h\0'; i = b.find(old)
    if i < 0: raise SystemExit('format string not found in Data.bin (already patched?)')
    b[i:i + len(old)] = b'%.0f' + bytes(len(old) - 4); open(p, 'wb').write(bytes(b)); return i


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cmd', choices=['install']); ap.add_argument('--base-game', required=True); ap.add_argument('--content', required=True)
    ap.add_argument('--release'); ap.add_argument('--data-out'); ap.add_argument('--preview')
    a = ap.parse_args()
    target = os.path.join(a.content, 'ui', 'cmn', 'ctgp.szs'); src = target + '.pre-speedo'
    if not os.path.exists(src): shutil.copy2(target, src)
    build(os.path.join(a.base_game, 'ui', 'cmn', 'race.szs'), src, target, a.preview); print('ctgp.szs updated (original kept as ctgp.szs.pre-speedo)')
    if a.release and a.data_out: print('Data.bin patched at', hex(patch_data(a.release, a.data_out)))
