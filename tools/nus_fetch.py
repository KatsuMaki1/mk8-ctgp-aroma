#!/usr/bin/env python3
"""Download one file of a Wii U title (e.g. code/Turbo.rpx of an older MK8 update) from Nintendo's update CDN.

  python nus_fetch.py --title 0005000e1010ed00 --version 64 --path code/Turbo.rpx --otp <Cemu>/otp.bin --out Turbo_v64.rpx

Use it only for titles you own. The title key comes from the CDN's public ticket, decrypted with the Wii U common key
read from YOUR OWN otp.bin (a console dump, e.g. the one Cemu uses); no key is bundled with this tool.
Tested with plain (non-hashed) contents; hashed contents (type & 2) use the block format of CDecrypt.
"""
import argparse, struct, sys, urllib.request
from Crypto.Cipher import AES          # pip install pycryptodome


def get(base, name):
    with urllib.request.urlopen(urllib.request.Request(base + name, headers={'User-Agent': 'wii libnup/1.0'}), timeout=120) as r:
        return r.read()


def decrypt(key, raw, idx, typ):
    iv = struct.pack('>H', idx) + b'\0' * 14
    if not typ & 2: return AES.new(key, AES.MODE_CBC, iv).decrypt(raw[:len(raw) // 16 * 16])
    out = bytearray()                                  # hashed content: 0x10000 blocks = 0x400 hashes + 0xFC00 data
    for b in range(len(raw) // 0x10000):
        blk = raw[b * 0x10000:(b + 1) * 0x10000]
        hashes = AES.new(key, AES.MODE_CBC, iv).decrypt(blk[:0x400])
        out += AES.new(key, AES.MODE_CBC, hashes[(b % 16) * 20:(b % 16) * 20 + 16]).decrypt(blk[0x400:])
    return bytes(out)


def fst_files(f):
    """yield (path, content_index, offset, size) from a decrypted FST"""
    ncl, = struct.unpack('>I', f[8:12]); eo = 0x20 + 0x20 * ncl
    def ent(i):
        b = f[eo + i * 16:eo + i * 16 + 16]; no = struct.unpack('>I', b'\0' + b[1:4])[0]
        a, c, fl, ci = struct.unpack('>IIHH', b[4:16]); return b[0], no, a, c, fl, ci
    total = ent(0)[3]; names = eo + total * 16; stack = [('', total)]
    for i in range(1, total):
        while len(stack) > 1 and i >= stack[-1][1]: stack.pop()
        t, no, a, c, fl, ci = ent(i)
        p = (stack[-1][0] + '/' if stack[-1][0] else '') + f[names + no:f.index(b'\0', names + no)].decode()
        if t & 1: stack.append((p, c))
        else: yield p, ci, (a if fl & 4 else a << 5), c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--title', required=True); ap.add_argument('--version', type=int, required=True)
    ap.add_argument('--path', required=True, help='path inside the title, e.g. code/Turbo.rpx')
    ap.add_argument('--otp', required=True, help='your own otp.bin'); ap.add_argument('--out', required=True)
    a = ap.parse_args()
    base = 'http://ccs.cdn.c.shop.nintendowifi.net/ccs/download/%s/' % a.title
    tmd, tik = get(base, 'tmd.%d' % a.version), get(base, 'cetk')
    n, = struct.unpack('>H', tmd[0x1DE:0x1E0])
    contents = [struct.unpack('>IHHQ', tmd[0xB04 + i * 0x30:0xB04 + i * 0x30 + 16]) for i in range(n)]
    common = open(a.otp, 'rb').read()[0xE0:0xF0]
    key = AES.new(common, AES.MODE_CBC, tik[0x1DC:0x1E4] + b'\0' * 8).decrypt(tik[0x1BF:0x1CF])
    cid, idx, typ, _ = contents[0]
    fst = decrypt(key, get(base, '%08x' % cid), idx, typ)
    if fst[:4] != b'FST\0': sys.exit('FST not found: wrong otp.bin / key?')
    for path, ci, off, size in fst_files(fst):
        if path == a.path:
            cid, idx, typ, _ = contents[ci]
            data = decrypt(key, get(base, '%08x' % cid), idx, typ)[off:off + size]
            open(a.out, 'wb').write(data); print('wrote', a.out, len(data), 'bytes'); return
    sys.exit('%s not found in the title' % a.path)


if __name__ == '__main__':
    main()
