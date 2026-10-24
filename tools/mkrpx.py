#!/usr/bin/env python3
"""Build a Cemu-ready Turbo.rpx with the CTGP-Cafe release code baked in.

  python mkrpx.py --rpx Turbo.rpx --pack "<...>/cafeloader/000500001010EC00" --out Turbo_ctgp.rpx

Takes the unmodified Mario Kart 8 v64 or v81 RPX plus the console release files (Code.bin, Data.bin, Patches.hax),
retargets the blob from the console layout to the unshifted RPX layout (see retarget.py), applies the
patch list inside the RPX sections (neutralising the load-time relocations that would overwrite patched
vtable pointers) and appends the blob as two new sections.
"""
import argparse, struct, sys, zlib, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rpxlib, retarget

T_ADDR = 0x02B10000          # blob code (64K aligned, inside the original text region 0x02B02B00..0x02B20C20: textSize stays unchanged)
D_ADDR = 0x10300020          # blob data (D % 0x10000 == 0x20, past bss + SDA window)
D_SIZE = 0x3000             # data section size (Data.bin + zero bss; max referenced offset is 0x28E8)
GT_SHIFT, GD_SHIFT = retarget.GT_SHIFT, retarget.GD_SHIFT
SENTINELS_V64 = [(0x02677548, 0x4BFFFEED), (0x0254D938, 0x386002CC)]   # untouched v64 words (the release target)
SENTINELS = [(0x02677548, 0x2C030000), (0x0254D938, 0x386001A4), (0x0253D6E0, 0x4BFFFE39)]   # untouched v81 words
SH = struct.Struct('>10I')


def comp(data):
    return struct.pack('>I', len(data)) + zlib.compress(bytes(data), 9)


def parse_hax(hax):
    cnt, = struct.unpack('>H', hax[:2]); p = 2; out = []
    for _ in range(cnt):
        ln, addr = struct.unpack('>HI', hax[p:p+6]); out.append((addr, hax[p+6:p+6+ln])); p += 6 + ln
    assert p == len(hax), 'Patches.hax has trailing bytes'
    return out


def sec_for(S, addr):
    for s in S:
        if s['t'] == 1 and s['addr'] <= addr < s['addr'] + len(s['data']) and s['fl'] & 2:
            return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--rpx', required=True); ap.add_argument('--pack', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--keep-text-size', action='store_true', help='debug: do not grow fileinfo.textSize (T must lie inside the original text region)')
    ap.add_argument('--keep-data-size', action='store_true', help='debug: do not grow fileinfo.dataSize')
    ap.add_argument('--grow-data', type=lambda x: int(x, 0), default=0, help='debug (with --null): grow fileinfo.dataSize by this many bytes')
    ap.add_argument('--text-flags', type=lambda x: int(x, 0), default=0x6, help='debug: sh_flags of the code section')
    ap.add_argument('--text-only', action='store_true', help='debug: add only the code section')
    ap.add_argument('--null', action='store_true', help='debug: rewrite the file only (no new sections, no patches, sizes untouched)')
    ap.add_argument('--probe-addr', type=lambda x: int(x, 0), help='debug: console blob address to overwrite with a branch to the probe code')
    ap.add_argument('--probe-bin', help='debug: raw PPC probe code (position independent) appended to the blob')
    ap.add_argument('--v64-rpx', help='MK8 v64 Turbo.rpx (the release target); required when --rpx is a v81 RPX')
    ap.add_argument('--no-patch', action='store_true', help='debug: add the sections but apply no patches')
    ap.add_argument('--T', type=lambda x: int(x, 0), default=T_ADDR); ap.add_argument('--D', type=lambda x: int(x, 0), default=D_ADDR)
    a = ap.parse_args()
    T, D = a.T, a.D

    src, S = rpxlib.load(a.rpx)
    v64 = [rpxlib.word_at(S, a) for a, _ in SENTINELS_V64] == [w for _, w in SENTINELS_V64]
    v81 = [rpxlib.word_at(S, a) for a, _ in SENTINELS] == [w for _, w in SENTINELS]
    if not (v64 or v81): sys.exit('not an unmodified MK8 v64 or v81 RPX')
    print('detected MK8', 'v64 (the release target)' if v64 else 'v81')
    if any(s['name'] == '.ctgp_text' for s in S): sys.exit('this RPX already has CTGP sections; use a clean Turbo.rpx')
    by = {s['name']: s for s in S}
    code = open(os.path.join(a.pack, 'Code.bin'), 'rb').read(); data = open(os.path.join(a.pack, 'Data.bin'), 'rb').read()
    patches = [] if (a.no_patch or a.null) else parse_hax(open(os.path.join(a.pack, 'Patches.hax'), 'rb').read())

    # 1. retarget the blob
    maps = None
    if v81:                                   # the release is built for v64: port every game address v64 -> v81
        import vmap
        if not a.v64_rpx or not os.path.isfile(a.v64_rpx): sys.exit('porting to v81 needs the MK8 v64 Turbo.rpx (--v64-rpx); see tools/nus_fetch.py')
        maps = vmap.Maps(a.v64_rpx, a.rpx)
    gt = (lambda c: maps.text(c - GT_SHIFT)) if maps else None
    gd = (lambda c: maps.data2(c - GD_SHIFT)) if maps else None
    blob = retarget.Blob(code, data)
    code2, data2, st = blob.retarget(T, D, gt, gd)
    print('retarget:', st)
    data2 = b'\0' * 0x20 + data2 + b'\0' * (D_SIZE - len(data2))   # the blob also uses the 0x20 bytes before Data.bin (refs down to D-4)
    # The console loader stores its log_printf in the header slot at D-4 and the blob calls it blindly: point it at a `blr` stub.
    code2 = code2 + b'\0' * (-len(code2) % 16); stub = T + len(code2); code2 += struct.pack('>I', 0x4E800020)
    data2 = data2[:0x1C] + struct.pack('>I', stub) + data2[0x20:]
    # Cemu fix: the blob decodes `bl OSDynLoad_*` words with a mask only (word & 0x03FFFFFC). On console the import stub is ahead
    # of the call; Cemu keeps its trampolines below the code, so the offset is negative and needs sign extension.
    # The two `rlwinm rA,rS,0,6,29` at 0F8023D0 / 0F8023E0 become `b stub`; stub = slwi/srawi (sign extend) + clear low bits + b back.
    for site_con, want in ((0x0F8023D0, 0x54AC01BA), (0x0F8023E0, 0x552B01BA)):
        site = site_con - retarget.CB
        assert struct.unpack('>I', code2[site:site+4])[0] == want, 'unexpected blob word at %08X' % site_con
        rs, ra = (want >> 21) & 31, (want >> 16) & 31
        code2 += b'\0' * (-len(code2) % 16); fix = T + len(code2)
        slwi = 0x54000000 | (rs << 21) | (ra << 16) | (6 << 11) | (0 << 6) | (25 << 1)      # rlwinm ra,rs,6,0,25  (= slwi ra,rs,6)
        srawi = 0x7C000670 | (ra << 21) | (ra << 16) | (6 << 11)                              # srawi ra,ra,6
        clr = 0x54000000 | (ra << 21) | (ra << 16) | (0 << 11) | (0 << 6) | (29 << 1)       # rlwinm ra,ra,0,0,29
        code2 += b''.join(struct.pack('>I', w) for w in (slwi, srawi, clr, 0x48000000 | (((T + site + 4) - (fix + 12)) & 0x03FFFFFC)))
        code2 = code2[:site] + struct.pack('>I', 0x48000000 | ((fix - (T + site)) & 0x03FFFFFC)) + code2[site+4:]
    if a.probe_addr:
        code2 += b'\0' * (-len(code2) % 16); pr = T + len(code2); code2 += open(a.probe_bin, 'rb').read()
        site = a.probe_addr - retarget.CB; off = pr - (T + site)
        code2 = code2[:site] + struct.pack('>I', 0x48000000 | (off & 0x03FFFFFC)) + code2[site + 4:]
        print('probe at %08X -> %08X' % (T + site, pr))

    # 2. apply Patches.hax inside the RPX sections
    text, rodata, dsec = by['.text'], by['.rodata'], by['.data']
    for s in (text, rodata, dsec, by['.rela.text'], by['.rela.rodata'], by['.rela.data']): s['data'] = bytearray(s['data']); s['dirty'] = False
    relas = {id(sec): sec_r for sec, sec_r in ((rodata, by['.rela.rodata']), (dsec, by['.rela.data']), (text, by['.rela.text']))}
    def blob_addr(console): return T + (console - retarget.CB)
    rt = by['.rela.text']['data']
    text_relocs = {struct.unpack('>I', rt[k:k+4])[0] for k in range(0, len(rt), 12)}
    n_text = n_ptr = 0
    for caddr, new in patches:
        assert len(new) == 4
        w = struct.unpack('>I', new)[0]
        if retarget.GT_LO <= caddr < retarget.GT_HI:
            ra = caddr - GT_SHIFT; sec = text
            if maps:
                i64 = (ra - maps.tm.base64) // 4; ra81 = maps.text(ra)
                if ra81 is None or maps.tm.k64[i64] != maps.tm.k81[(ra81 - maps.tm.base81) // 4]: sys.exit('patch site %08X has no equivalent in v81' % ra)
                ra = ra81
            if w >> 26 == 18:                                      # b/bl into the blob
                off = w & 0x03FFFFFC
                if off & 0x02000000: off -= 0x04000000
                t = caddr + off; assert retarget.CB <= t < retarget.CB + len(code), 'hook target outside blob'
                w = retarget.encode_branch(w, ra, blob_addr(t))
            # no relocation may cover a patched text word
            if ra in text_relocs: sys.exit('relocation covers patched text word %08X' % ra)
            n_text += 1
        elif retarget.GD_LO <= caddr < retarget.GD_HI:
            ra = caddr - GD_SHIFT
            if maps:
                r = maps.slot2(ra)
                if r is None: sys.exit('data patch slot %08X has no equivalent in v81' % ra)
                ra = r[0]
            sec = sec_for(S, ra)
            assert sec in (rodata, dsec), 'data patch outside .rodata/.data'
            if not (retarget.CB <= w < retarget.CB + len(code)): sys.exit('data patch %08X is not a blob pointer: %08X' % (ra, w))
            w = blob_addr(w)
            rel = relas[id(sec)]['data']; hit = 0
            for k in range(0, len(rel), 12):                       # pointer = sym1(.text base) + addend: move the addend
                o, info, add = struct.unpack('>III', rel[k:k+12])
                if o == ra:
                    assert info & 0xFF == 1, 'unexpected reloc type at %08X' % ra
                    symv = 0x02000000                              # sym 1 is the .text section symbol (checked below)
                    struct.pack_into('>I', rel, k + 8, w - symv); hit += 1
            assert hit == 1, 'expected exactly one relocation at %08X, found %d' % (ra, hit)
            relas[id(sec)]['dirty'] = True
            n_ptr += 1
        else:
            sys.exit('patch address %08X outside game text/data' % caddr)
        o = ra - sec['addr']
        sec['data'][o:o+4] = struct.pack('>I', w); sec['dirty'] = True
    print('patches: %d text, %d data pointers' % (n_text, n_ptr))
    # sym 1 must be the .text section symbol with value 0x02000000
    st_ = by['.symtab']['data']; sv = struct.unpack('>IIIBBH', st_[16:32])
    assert sv[1] == 0x02000000, 'symbol 1 is not the .text base (%08X)' % sv[1]

    # 3. new sections (inserted before the CRC / fileinfo sections)
    names = bytearray(by['.shstrtab']['data'])
    def add_name(n):       # reuse a suffix of an existing name (".text" in ".rela.text"): growing .shstrtab breaks Cemu's loader
        o = bytes(names).rfind(n.encode() + b'\0')
        assert o >= 0, 'no existing %s suffix in .shstrtab' % n
        return o
    new = [] if a.null else [dict(n=add_name('.text'), t=1, fl=a.text_flags, addr=T, data=code2, align=0x20),
           dict(n=add_name('.data'), t=1, fl=0x3, addr=D - 0x20, data=data2, align=0x20)]
    if a.text_only: new = new[:1]
    assert bytes(names) == by['.shstrtab']['data'], '.shstrtab must stay untouched'
    tail = [s for s in S if s['t'] in (0x80000003, 0x80000004)]
    body = [s for s in S if s['t'] not in (0x80000003, 0x80000004)]
    assert [s['i'] for s in body] == list(range(len(body)))
    for k, ns in enumerate(new):
        ns.update(i=len(body) + k, link=0, info=0, ent=0, size=len(ns['data']), off=0, raw=ns['data'], name='.new%d' % k)
    order = body + new + tail
    for i, s in enumerate(order): s['i'] = i

    # 4. fileinfo
    fi = [s for s in S if s['t'] == 0x80000004][0]; fib = bytearray(fi['data'])
    if a.null: a.keep_text_size = a.keep_data_size = True
    text_end = T + len(code2); data_end = D - 0x20 + len(data2)
    old_ts, old_ds = struct.unpack('>II', fib[4:8] + fib[12:16])
    if a.text_only: a.keep_data_size = True
    ts = old_ts if a.keep_text_size else max(old_ts, ((text_end + 0x1F) & ~0x1F) - 0x02000000)
    ds = old_ds if a.keep_data_size else max(old_ds, ((data_end + 0xFF) & ~0xFF) - 0x10000000)
    struct.pack_into('>I', fib, 4, ts); struct.pack_into('>I', fib, 12, ds)
    if a.null and a.grow_data: ds = old_ds + a.grow_data
    print('fileinfo textSize %X -> %X, dataSize %X -> %X' % (old_ts, ts, old_ds, ds))
    fi['data'] = fib

    # 5. raw bytes (recompress what changed), CRC table
    for s in order:
        if s['t'] == 8: s['raw'] = b''; continue
        if s.get('dirty'): s['raw'] = comp(s['data']) if s['fl'] & 0x08000000 else bytes(s['data'])
        elif 'raw' not in s or s in new: s['raw'] = bytes(s['data'])
        s['size'] = len(s['raw']) if s['t'] != 8 else s['size']
    crcs = bytearray()
    crc_sec = [s for s in order if s['t'] == 0x80000003][0]
    for s in order:
        v = 0 if (s is crc_sec or s['t'] == 8) else zlib.crc32(bytes(s['data'])) & 0xFFFFFFFF
        crcs += struct.pack('>I', v)
    crc_sec['data'] = bytes(crcs); crc_sec['raw'] = bytes(crcs); crc_sec['size'] = len(crcs)
    for s in tail: s['raw'] = bytes(s['data']); s['size'] = len(s['raw'])

    # 6. layout: ELF header, SHT at 0x40, then section data (original relative order for old ones)
    hdr = bytearray(src[:0x40]); n = len(order)
    pos = 0x40 + n * 40; pos = (pos + 0xF) & ~0xF
    placed = sorted([s for s in order if s['t'] != 8], key=lambda s: (s.get('off', 0) if s not in new else 1 << 40, s['i']))
    for s in placed:
        s['off_new'] = pos; pos = (pos + len(s['raw']) + 0xF) & ~0xF
    out = bytearray(pos)
    for s in placed: out[s['off_new']:s['off_new'] + len(s['raw'])] = s['raw']
    struct.pack_into('>I', hdr, 0x20, 0x40); struct.pack_into('>H', hdr, 0x30, n)    # e_shoff, e_shnum (e_shstrndx unchanged)
    out[:0x40] = hdr
    for s in order:
        row = SH.pack(s['n'], s['t'], s['fl'], s['addr'], s.get('off_new', 0) if s['t'] != 8 else 0, s['size'], s['link'], s['info'], s['align'], s['ent'])
        out[0x40 + s['i'] * 40:0x40 + (s['i'] + 1) * 40] = row
    open(a.out, 'wb').write(out)
    print('wrote', a.out, len(out), 'bytes,', n, 'sections')


if __name__ == '__main__':
    main()
