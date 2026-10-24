"""Wii U BFLIM textures (2D_TILED_THIN1 / 1D) <-> PNG, for 16/32-bit formats (RGB565 cup icons, RGBA8).

Address computation ported from Cemu's LatteAddrLib (MPL-2.0): 2 pipes, 4 banks, 256-byte pipe interleave.
"""
import struct
import numpy as np
from PIL import Image

FMT = {5: ('RGB565 (little endian)', 16), 9: ('RGBA8', 32)}   # BFLIM format id -> (name, bits per pixel)
PIPES, BANKS, INTERLEAVE_BITS = 2, 4, 8


def _micro_index(x, y, bpp):
    if bpp == 16:
        return (x & 1) | ((x & 2) << 0) | ((x & 4) << 0) | ((y & 1) << 3) | ((y & 2) << 3) | ((y & 4) << 3)
    if bpp == 32:
        return (x & 1) | ((x & 2) >> 1 << 1) | ((y & 1) << 2) | ((x & 4) >> 2 << 3) | ((y & 2) >> 1 << 4) | ((y & 4) >> 2 << 5)
    raise ValueError('bpp %d unsupported' % bpp)


def _micro_index_exact(x, y, bpp):
    if bpp == 64:
        b = [x & 1, y & 1, (x >> 1) & 1, (x >> 2) & 1, (y >> 1) & 1, (y >> 2) & 1]
        return sum(v << i for i, v in enumerate(b))
    """pixel index inside an 8x8 micro tile (AddrLib _ComputePixelIndexWithinMicroTile, non-depth, thickness 1)"""
    if bpp == 16:
        b = [x & 1, (x >> 1) & 1, (x >> 2) & 1, y & 1, (y >> 1) & 1, (y >> 2) & 1]
    elif bpp == 32:
        b = [x & 1, (x >> 1) & 1, y & 1, (x >> 2) & 1, (y >> 1) & 1, (y >> 2) & 1]
    else:
        raise ValueError('bpp %d unsupported' % bpp)
    return sum(v << i for i, v in enumerate(b))


def addr_2d_thin1(x, y, bpp, pitch, pipe_swz, bank_swz):
    elem = (bpp * _micro_index_exact(x, y, bpp)) >> 3
    pipe = ((y >> 3) ^ (x >> 3)) & 1
    bank = (y >> 4) & 3
    bank = ((bank >> 1) | (bank << 1)) & 3
    bank = (bank ^ (x >> 3)) & 3
    bank_pipe = pipe + PIPES * bank
    bank_pipe ^= (pipe_swz + PIPES * bank_swz)               # rotation * slice is 0 for slice 0
    bank_pipe %= PIPES * BANKS
    pipe, bank = bank_pipe % PIPES, bank_pipe // PIPES
    macro_bytes = (bpp * 16 * 32 + 7) >> 3
    macro_off = (x // 32 + (pitch // 32) * (y // 16)) * macro_bytes
    swz_bits = 3                                              # log2(banks) + log2(pipes)
    off = (macro_off >> swz_bits) + elem
    high, low = off & ~0xFF, off & 0xFF
    return (((high << swz_bits) | low)) | (pipe << INTERLEAVE_BITS) | (bank << (1 + INTERLEAVE_BITS))


def addr_1d_thin1(x, y, bpp, pitch):
    return (((bpp * 64) >> 3) * ((x >> 3) + (pitch >> 3) * (y >> 3))) + ((bpp * _micro_index_exact(x, y, bpp)) >> 3)


def footer(raw):
    f = raw[-0x28:]
    assert f[:4] == b'FLIM' and f[0x14:0x18] == b'imag'
    w, h, align, fmt, flags, size = struct.unpack('>HHHBBI', f[0x1C:0x28])
    return dict(w=w, h=h, align=align, fmt=fmt, tile=flags & 0x1F, swizzle_bits=flags >> 5, size=size)


def surface_dims(w, h, bpp, tile):
    if tile == 4:
        pa = max(32, 32 * (256 // bpp // 8))                  # pitch alignment for 2D thin1, 1 sample
        return (w + pa - 1) // pa * pa, (h + 15) // 16 * 16
    return (w + 7) // 8 * 8, (h + 7) // 8 * 8


def swizzle_candidates(f):
    return [(p, b) for b in range(4) for p in range(2)]


def decode(raw, swz=(0, 0)):
    """-> (PIL RGBA image, swizzle used)"""
    f = footer(raw); name, bpp = FMT[f['fmt']]
    pitch, height = surface_dims(f['w'], f['h'], bpp, f['tile'])
    data = raw[:f['size']]
    best = None
    for p, b in ([swz] if swz else swizzle_candidates(f)):
        px = np.zeros((f['h'], f['w'], 4), dtype=np.uint8); smooth = 0
        for y in range(f['h']):
            for x in range(f['w']):
                o = addr_2d_thin1(x, y, bpp, pitch, p, b) if f['tile'] == 4 else addr_1d_thin1(x, y, bpp, pitch)
                if bpp == 16:
                    v = (data[o + 1] << 8) | data[o]                      # 16-bit units are stored little endian
                    px[y, x] = (((v >> 11) & 31) * 255 // 31, ((v >> 5) & 63) * 255 // 63, (v & 31) * 255 // 31, 255)
                else:
                    px[y, x] = tuple(data[o:o + 4])
        d = np.abs(np.diff(px[..., :3].astype(int), axis=1)).sum()
        if best is None or d < best[0]: best = (d, px, (p, b))
        if swz: break
    return Image.fromarray(best[1], 'RGBA'), best[2]


def decode_raw565(raw):
    """-> (h, w) uint16 array of the original RGB565 values (exact, no float conversion)"""
    f = footer(raw); assert FMT[f['fmt']][1] == 16 and f['tile'] == 4
    pitch, _ = surface_dims(f['w'], f['h'], 16, 4); data = raw[:f['size']]
    out = np.zeros((f['h'], f['w']), dtype=np.uint16)
    for y in range(f['h']):
        for x in range(f['w']):
            o = addr_2d_thin1(x, y, 16, pitch, 0, 0); out[y, x] = (data[o + 1] << 8) | data[o]
    return out


def encode_raw565(vals, template):
    """16-bit RGB565 array -> BFLIM bytes, reusing the template's footer (size/format/alignment)"""
    f = footer(template); pitch, _ = surface_dims(f['w'], f['h'], 16, 4)
    assert vals.shape == (f['h'], f['w'])
    buf = bytearray(f['size'])
    for y in range(f['h']):
        for x in range(f['w']):
            o = addr_2d_thin1(x, y, 16, pitch, 0, 0); v = int(vals[y, x]); buf[o] = v & 0xFF; buf[o + 1] = v >> 8
    return bytes(buf) + template[-0x28:]


def rgb_to_565(img):
    a = np.array(img.convert('RGB')).astype(np.uint16)
    return ((a[..., 0] >> 3) << 11) | ((a[..., 1] >> 2) << 5) | (a[..., 2] >> 3)


# ---- block compressed (BC1 / DXT1: 4x4 pixels in 8 bytes; one "element" = one block)
def _bc1_geometry(f):
    bw, bh = (f['w'] + 3) // 4, (f['h'] + 3) // 4
    pitch = (bw + 31) // 32 * 32 if f['tile'] == 4 else bw
    return bw, bh, pitch


def decode_bc1(raw, swz=None):
    """BC1 BFLIM -> PIL RGBA image"""
    f = footer(raw); bw, bh, pitch = _bc1_geometry(f); data = raw[:f['size']]
    swz = swz or (f['swizzle_bits'] & 1, f['swizzle_bits'] >> 1)
    out = np.zeros((bh * 4, bw * 4, 4), dtype=np.uint8)
    for by in range(bh):
        for bx in range(bw):
            o = addr_2d_thin1(bx, by, 64, pitch, *swz) if f['tile'] == 4 else (by * pitch + bx) * 8
            c0, c1, idx = struct.unpack('<HHI', data[o:o + 8])
            def rgb(c): return [((c >> 11) & 31) * 255 // 31, ((c >> 5) & 63) * 255 // 63, (c & 31) * 255 // 31]
            p = [rgb(c0), rgb(c1)]
            if c0 > c1: p += [[(2 * a + b) // 3 for a, b in zip(p[0], p[1])], [(a + 2 * b) // 3 for a, b in zip(p[0], p[1])]]
            else: p += [[(a + b) // 2 for a, b in zip(p[0], p[1])], [0, 0, 0]]
            for i in range(16): out[by * 4 + i // 4, bx * 4 + i % 4, :3] = p[(idx >> (2 * i)) & 3]; out[by * 4 + i // 4, bx * 4 + i % 4, 3] = 255
    return Image.fromarray(out[:f['h'], :f['w']], 'RGBA')


def encode_bc1(img, template, swz=None):
    """PIL image -> BC1 BFLIM bytes (template gives footer: size/format/alignment/swizzle). Simple range-fit compressor."""
    f = footer(template); bw, bh, pitch = _bc1_geometry(f)
    swz = swz or (f['swizzle_bits'] & 1, f['swizzle_bits'] >> 1)
    a = np.array(img.convert('RGB').resize((f['w'], f['h']), Image.LANCZOS)).astype(int)
    a = np.pad(a, ((0, bh * 4 - f['h']), (0, bw * 4 - f['w']), (0, 0)), mode='edge')
    buf = bytearray(f['size'])
    def to565(c): return ((c[0] >> 3) << 11) | ((c[1] >> 2) << 5) | (c[2] >> 3)
    def from565(c): return np.array([((c >> 11) & 31) * 255 // 31, ((c >> 5) & 63) * 255 // 63, (c & 31) * 255 // 31])
    for by in range(bh):
        for bx in range(bw):
            blk = a[by * 4:by * 4 + 4, bx * 4:bx * 4 + 4].reshape(16, 3)
            lo, hi = blk.min(0), blk.max(0)
            c0, c1 = to565(hi), to565(lo)
            if c0 < c1: c0, c1 = c1, c0
            if c0 == c1: idx = 0
            else:
                pal = [from565(c0), from565(c1)]; pal += [(2 * pal[0] + pal[1]) // 3, (pal[0] + 2 * pal[1]) // 3]
                idx = 0
                for i, px in enumerate(blk): idx |= int(np.argmin([((px - p) ** 2).sum() for p in pal])) << (2 * i)
            o = addr_2d_thin1(bx, by, 64, pitch, *swz) if f['tile'] == 4 else (by * pitch + bx) * 8
            buf[o:o + 8] = struct.pack('<HHI', c0, c1, idx)
    return bytes(buf) + template[-0x28:]


def encode_rgba8(img, template):
    """RGBA PIL image -> RGBA8 BFLIM bytes (template: an existing RGBA8 BFLIM of the same size, e.g. ym_Coin_00^l; gives footer + swizzle)"""
    f = footer(template); assert f['fmt'] == 20 and f['tile'] == 4
    pitch, _ = surface_dims(f['w'], f['h'], 32, 4); s = f['swizzle_bits']; sw = (s & 1, s >> 1)
    a = np.array(img.convert('RGBA').resize((f['w'], f['h']), Image.LANCZOS)); buf = bytearray(f['size'])
    for y in range(f['h']):
        for x in range(f['w']):
            o = addr_2d_thin1(x, y, 32, pitch, *sw); buf[o:o + 4] = bytes(a[y, x])
    return bytes(buf) + template[-0x28:]


def decode_rgba8(raw):
    f = footer(raw); assert f['fmt'] == 20
    pitch, _ = surface_dims(f['w'], f['h'], 32, 4); s = f['swizzle_bits']; sw = (s & 1, s >> 1); out = np.zeros((f['h'], f['w'], 4), np.uint8)
    for y in range(f['h']):
        for x in range(f['w']): o = addr_2d_thin1(x, y, 32, pitch, *sw); out[y, x] = list(raw[o:o + 4])
    return Image.fromarray(out, 'RGBA')
