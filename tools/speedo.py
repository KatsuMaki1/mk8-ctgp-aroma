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

# lap/coin layout units (N_All_00 centre = the part centre; the part sits at (-434,-295) in the race HUD with scale 0.9)
LOCAL_LEFT, LOCAL_W = 116.0, 120.0      # new pill: left edge (the lap pill ends at 122) and width
ICON_DX, ICON_SIZE = 30.0, 40.0         # icon centre = left edge + ICON_DX
# race HUD units (where CTGP's text pane lives): part centre + 0.9 * local
TEXT_X, TEXT_Y = -262.0, -295.0
TEXT_W, TEXT_H = 90.0, 44.0

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
def children_end(secs, i):
    """index just after the pae1 that closes the pas1 following secs[i] (or i+1 when the pane has no children)"""
    if i + 1 >= len(secs) or secs[i + 1][0] != 'pas1': return i + 1
    depth = 0
    for j in range(i + 1, len(secs)):
        if secs[j][0] == 'pas1': depth += 1
        elif secs[j][0] == 'pae1':
            depth -= 1
            if depth == 0: return j + 1
    raise ValueError('unbalanced panes')


def build(base_race, ctgp_in, ctgp_out, preview=None):
    base = {h: d for n, d, h, a in szs.sarc_info(szs.yaz0_decode(open(base_race, 'rb').read()))[0]}
    get = lambda name: base[szs.sarc_hash(name)]
    raw = szs.yaz0_decode(open(ctgp_in, 'rb').read()); info, _, ver = szs.sarc_info(raw)
    files = {n: d for n, d, h, a in info}; aligns = szs.sarc_aligns(raw)
    if LAPCOIN in files: raise SystemExit('this ctgp.szs already has the speedometer layout; start from the original ctgp.szs (.pre-speedo)')

    # ---- 1. the lap/coin counter layout (the game plays its In/Out animation on N_All_00): add the pill + icon inside it, so they appear with it
    hdr, secs = split(get(LAPCOIN))
    tex = read_txl1(next(s for t, s in secs if t == 'txl1')); icon_tex = ICON_TEX + '.bflim'; tex.append(icon_tex)
    mats = read_mat1(next(s for t, s in secs if t == 'mat1')); mat_by_name = {cstr(m[:28]).strip(): i for i, m in enumerate(mats)}
    names = [pane_name(s) if t in ('wnd1', 'pic1', 'pan1', 'txt1') else None for t, s in secs]
    at = lambda n: names.index(n)
    w0 = bytearray(secs[at('W_FlagBase_00')][1]); w1 = bytearray(secs[at('W_FlagBase_01')][1]); lap = bytearray(secs[at('P_Lap_00')][1])
    set_pane(w0, 'W_Speedo_00', (LOCAL_LEFT, 0.0), None, (LOCAL_W, 72.0)); set_pane(w1, 'W_Speedo_01', (4.0, 0.0), None, (LOCAL_W - 6, 65.0))
    m = bytearray(mats[mat_by_name['P_Lap_00']]); m[40:42] = struct.pack('>H', len(tex) - 1); mats.append(bytes(m))
    icon = lap; set_pane(icon, 'P_Speedo_00', (LOCAL_LEFT + ICON_DX, 0.0), None, (ICON_SIZE, ICON_SIZE))
    assert struct.unpack('>H', icon[0x64:0x66])[0] == mat_by_name['P_Lap_00']; struct.pack_into('>H', icon, 0x64, len(mats) - 1)
    out = []; end = children_end(secs, at('W_FlagBase_00'))
    for i, (t, s) in enumerate(secs):
        if t == 'txl1': out.append(make_txl1(tex))
        elif t == 'mat1': out.append(make_mat1(mats))
        else: out.append([t, s])
        if i == end - 1: out += [['wnd1', w0], sec('pas1', b''), ['wnd1', w1], sec('pae1', b''), ['pic1', icon]]
    files[LAPCOIN] = join(hdr, out)
    for n in tex:                                                   # the layout now comes from this archive: give it every texture it uses
        nm = 'timg/%s' % n
        if n == icon_tex:
            tmpl = get('timg/ym_Coin_00^l.bflim'); img = draw_icon(48); files[nm] = bflim.encode_rgba8(img, tmpl)
            if preview: img.resize((192, 192), Image.NEAREST).save(preview)
        else: files[nm] = get(nm)
        aligns[nm] = max(0x20, bflim.footer(files[nm])['align'])

    # ---- 2. CTGP's race HUD: only restyle the text pane its code writes the speed into (found by name, so it stays where CTGP expects it)
    hdr, secs = split(files[RACEVIEW]); txt = next(s for t, s in secs if t == 'txt1'); assert pane_name(txt) == 'L_Speedometer_00'
    set_pane(txt, None, (TEXT_X, TEXT_Y), None, (TEXT_W, TEXT_H))
    struct.pack_into('>f', txt, 0x60, 0.22)                                        # italic like the game's digits
    txt[0x68:0x70] = bytes.fromhex('ffffffff969696ff'); struct.pack_into('>2f', txt, 0x70, 36.0, 40.0)
    off = struct.unpack('>I', txt[0x64:0x68])[0]; txt[off:off + 2] = bytes(2)       # placeholder text "... km/h" -> empty until the game writes the speed
    files[RACEVIEW] = join(hdr, secs)
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
