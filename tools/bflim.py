"""Wii U BFLIM textures (2D_TILED_THIN1 / 1D) <-> PNG, for 16/32-bit formats (RGB565 cup icons, RGBA8).

Address computation ported from Cemu's LatteAddrLib (MPL-2.0): 2 pipes, 4 banks, 256-byte pipe interleave.
"""
import struct
import numpy as np
from PIL import Image

FMT = {5: ('RGB565', 16), 9: ('RGBA8', 32)}          # BFLIM format id -> (name, bits per pixel)
PIPES, BANKS, INTERLEAVE_BITS = 2, 4, 8


def _micro_index(x, y, bpp):
    if bpp == 16:
        return (x & 1) | ((x & 2) << 0) | ((x & 4) << 0) | ((y & 1) << 3) | ((y & 2) << 3) | ((y & 4) << 3)
    if bpp == 32:
        return (x & 1) | ((x & 2) >> 1 << 1) | ((y & 1) << 2) | ((x & 4) >> 2 << 3) | ((y & 2) >> 1 << 4) | ((y & 4) >> 2 << 5)
    raise ValueError('bpp %d unsupported' % bpp)


def _micro_index_exact(x, y, bpp):
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


def decode(raw, swz=None):
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
                    v = (data[o] << 8) | data[o + 1]
                    px[y, x] = (((v >> 11) & 31) * 255 // 31, ((v >> 5) & 63) * 255 // 63, (v & 31) * 255 // 31, 255)
                else:
                    px[y, x] = tuple(data[o:o + 4])
        d = np.abs(np.diff(px[..., :3].astype(int), axis=1)).sum()
        if best is None or d < best[0]: best = (d, px, (p, b))
        if swz: break
    return Image.fromarray(best[1], 'RGBA'), best[2]
