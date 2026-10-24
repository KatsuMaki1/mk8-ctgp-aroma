#!/usr/bin/env python3
"""Port the CTGP-Cafe console release (built for MK8 v64) to MK8 v81 for the Aroma plugin.

  python mkpack.py --v64-rpx Turbo_v64.rpx --v81-rpx Turbo_v81.rpx --release <cafeloader/000500001010EC00> --out <cafeloader/000500001010ED00>

Same layout as the original release (blob at 0x0F800000, data at 0x10400020, game text = RPX + 0x0C180000, game data = RPX + 0x00502200),
but every game address is moved from the v64 to the v81 build (vmap.py). Extra files for the plugin:
  Verify.hax   original bytes at every patched address (the plugin refuses to patch if memory does not match)
  Code.bin     ends with a `blr` stub whose address the plugin stores at 0x1040001C (the slot the console loader used for log_printf)
"""
import argparse, os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import retarget, rpxlib, vmap

GT, GD, CB, DB = retarget.GT_SHIFT, retarget.GD_SHIFT, retarget.CB, retarget.DB


def parse_hax(b):
    n, = struct.unpack('>H', b[:2]); p = 2; out = []
    for _ in range(n):
        ln, a = struct.unpack('>HI', b[p:p+6]); out.append((a, b[p+6:p+6+ln])); p += 6 + ln
    assert p == len(b)
    return out


def write_hax(items):
    return struct.pack('>H', len(items)) + b''.join(struct.pack('>HI', len(d), a) + d for a, d in items)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--v64-rpx', required=True); ap.add_argument('--v81-rpx', required=True)
    ap.add_argument('--release', required=True, help='folder with the original Addr.bin/Code.bin/Data.bin/Patches.hax (v64)')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    _, S81 = rpxlib.load(a.v81_rpx)
    if [rpxlib.word_at(S81, x) for x, _ in ((0x02677548, 0), (0x0254D938, 0), (0x0253D6E0, 0))] != [0x2C030000, 0x386001A4, 0x4BFFFE39]:
        sys.exit('--v81-rpx is not an unmodified MK8 v81 RPX')
    maps = vmap.Maps(a.v64_rpx, a.v81_rpx)
    rd = lambda n: open(os.path.join(a.release, n), 'rb').read()
    code, data, addr, hax = rd('Code.bin'), rd('Data.bin'), rd('Addr.bin'), parse_hax(rd('Patches.hax'))
    assert struct.unpack('>II', addr) == (CB, DB)

    def gt(c):
        r = maps.text(c - GT); return None if r is None else r + GT
    def gd(c):
        r = maps.data2(c - GD); return None if r is None else r + GD

    code2, data2, st = retarget.Blob(code, data).retarget(CB, DB, gt, gd)
    print('retarget:', st)
    code2 += b'\0' * (-len(code2) % 16) + struct.pack('>I', 0x4E800020)            # log stub (last word)

    patches, verify = [], []
    b81 = {s['name']: s for s in S81}
    ptr81 = maps.ptr81
    for caddr, new in hax:
        w = struct.unpack('>I', new)[0]
        if retarget.GT_LO <= caddr < retarget.GT_HI:                                  # text site
            ra = caddr - GT; ra81 = maps.text(ra)
            i64 = (ra - maps.tm.base64) // 4
            assert ra81 is not None and maps.tm.k64[i64] == maps.tm.k81[(ra81 - maps.tm.base81) // 4], 'no equivalent for %08X' % caddr
            if w >> 26 == 18:                                                         # b/bl into the blob: re-encode for the new site
                off = w & 0x03FFFFFC
                if off & 0x02000000: off -= 0x04000000
                w = retarget.encode_branch(w, ra81 + GT, caddr + off)
            patches.append((ra81 + GT, struct.pack('>I', w)))
            verify.append((ra81 + GT, struct.pack('>I', rpxlib.word_at(S81, ra81))))
        else:                                                                         # vtable-like slot holding a text pointer
            r = maps.slot2(caddr - GD)
            assert r is not None, 'no equivalent slot for %08X' % caddr
            slot81 = r[0]
            patches.append((slot81 + GD, new))
            verify.append((slot81 + GD, struct.pack('>I', ptr81[slot81] + GT)))      # console memory holds the relocated pointer
    os.makedirs(a.out, exist_ok=True)
    for name, blob in (('Code.bin', code2), ('Data.bin', data2), ('Addr.bin', addr), ('Patches.hax', write_hax(patches)), ('Verify.hax', write_hax(verify))):
        open(os.path.join(a.out, name), 'wb').write(blob)
    print('wrote', a.out, ':', len(code2), 'code bytes,', len(data2), 'data bytes,', len(patches), 'patches')


if __name__ == '__main__':
    main()
