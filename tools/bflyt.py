"""Minimal BFLYT (Wii U) reader: section list, pane tree with names/positions/sizes, texture and material names."""
import struct

def sections(d):
    o = struct.unpack('>H', d[6:8])[0]; out = []
    while o < len(d):
        t = d[o:o + 4].decode('latin1'); s = struct.unpack('>I', d[o + 4:o + 8])[0]; out.append((t, o, s)); o += s
    return out

def cstr(b): return b.split(b'\0')[0].decode('latin1')

def dump(d, verbose=True):
    secs = sections(d); depth = 0; res = []; tex = []; mats = []
    for t, o, s in secs:
        b = d[o:o + s]
        if t == 'txl1':
            n = struct.unpack('>H', b[8:10])[0]; offs = struct.unpack('>%dI' % n, b[12:12 + 4 * n]); base = 12
            tex = [cstr(b[base + x:]) for x in offs]
        elif t == 'mat1':
            n = struct.unpack('>H', b[8:10])[0]; offs = struct.unpack('>%dI' % n, b[12:12 + 4 * n]); mats = [(cstr(d[o + x:o + x + 28]), x) for x in offs]
        elif t == 'pas1': depth += 1
        elif t == 'pae1': depth -= 1
        elif t in ('pan1', 'pic1', 'txt1', 'wnd1', 'bnd1', 'prt1'):
            name = cstr(b[12:36]); flag, origin, alpha, _ = b[8], b[9], b[10], b[11]
            x, y, z, rx, ry, rz, sx, sy, w, h = struct.unpack('>10f', b[44:84])
            extra = ''
            if t == 'pic1': extra = ' mat=%d' % struct.unpack('>H', b[0x5C + 0 : 0x5E])[0] if False else ''
            res.append((depth, t, name, round(x, 1), round(y, 1), round(w, 1), round(h, 1), o, s))
    if verbose:
        print('textures:', tex); print('materials:', [m[0] for m in mats])
        for r in res: print('  ' * r[0], r[1], r[2], 'pos', r[3], r[4], 'size', r[5], r[6], 'off', hex(r[7]), 'size', r[8])
    return res
