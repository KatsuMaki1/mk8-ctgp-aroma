"""Independent audit of a mkrpx.py output against the source RPX and the release patch list."""
import struct, sys, zlib, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rpxlib, retarget
src_path, out_path, pack = sys.argv[1:4]
maps = None
if len(sys.argv) > 4:
    import vmap; maps = vmap.Maps(sys.argv[4], src_path)      # v81 source: map v64 addresses
def map_text(ra): return maps.text(ra) if maps else ra
def map_slot(ra): return maps.slot2(ra)[0] if maps else ra
sd, S = rpxlib.load(src_path); od, O = rpxlib.load(out_path)
sb = {}; ob = {}
for s in S: sb.setdefault(s['name'], s)
for s in O: ob.setdefault(s['name'], s)     # new sections reuse '.text'/'.data' names; the originals come first
fails = []
def check(c, m):
    if not c: fails.append(m); print('FAIL', m)
# structure
check(od[:4] == b'\x7fELF' and od[0x10:0x14] == sd[0x10:0x14], 'ELF magic/type')
check(struct.unpack('>I', od[0x18:0x1C]) == struct.unpack('>I', sd[0x18:0x1C]), 'entry point unchanged')
crc = [s for s in O if s['t'] == 0x80000003][0]['data']
for s in O:
    if s['t'] == 0x80000003: continue
    want = struct.unpack('>I', crc[s['i']*4:s['i']*4+4])[0]
    got = 0 if s['t'] == 8 else zlib.crc32(s['data']) & 0xFFFFFFFF
    check(want == got, 'crc section %d %s' % (s['i'], s['name']))
check(len(crc) == 4 * len(O), 'crc table length')
# untouched sections identical
changed = {'.text', '.rodata', '.data', '.rela.text', '.rela.rodata', '.rela.data'}
for n, s in sb.items():
    if n in changed or s['t'] in (0x80000003, 0x80000004): continue
    check(n in ob and ob[n]['data'] == s['data'] and ob[n]['addr'] == s['addr'] and ob[n]['fl'] == s['fl'], 'unchanged section %s' % n)
# section header sanity: ranges inside file, no overlap of file data
spans = sorted((s['off'], s['off'] + s['size'], s['name']) for s in O if s['t'] != 8 and s['size'])
for a, b in zip(spans, spans[1:]): check(a[1] <= b[0], 'file overlap %s / %s' % (a[2], b[2]))
check(spans[-1][1] <= len(od), 'section beyond EOF')
# simulate loader relocation (ADDR32 only matters for pointer words) and diff source vs output
def relocated(B, name, relname):
    d = bytearray(B[name]['data']); rel = B[relname]['data']; base = B[name]['addr']
    for k in range(0, len(rel), 12):
        o, info, add = struct.unpack('>III', rel[k:k+12])
        if info & 0xFF == 1 and base <= o < base + len(d):
            struct.pack_into('>I', d, o - base, (0x02000000 + add) & 0xFFFFFFFF)       # sym 1 = .text base
    return d
patches = []
hax = open(os.path.join(pack, 'Patches.hax'), 'rb').read(); cnt, = struct.unpack('>H', hax[:2]); p = 2
for _ in range(cnt):
    ln, a = struct.unpack('>HI', hax[p:p+6]); patches.append((a, hax[p+6:p+6+ln])); p += 6 + ln
code = open(os.path.join(pack, 'Code.bin'), 'rb').read()
T = [s for s in O if s['name'] == '.text' and s['addr'] > 0x02B00000][0]['addr']
exp_data = {}
for a, w in patches:
    wv = struct.unpack('>I', w)[0]
    if a >= retarget.GD_LO: exp_data[map_slot(a - retarget.GD_SHIFT)] = T + wv - retarget.CB
for nm, rn in (('.rodata', '.rela.rodata'), ('.data', '.rela.data')):
    a0, a1 = relocated(sb, nm, rn), relocated(ob, nm, rn); base = sb[nm]['addr']
    diffs = {base + o for o in range(0, len(a0), 4) if a0[o:o+4] != a1[o:o+4]}
    want = {x for x in exp_data if base <= x < base + len(a0)}
    check(diffs == want, '%s relocated diff = patched pointers (diff %d, want %d)' % (nm, len(diffs), len(want)))
    for x in want: check(struct.unpack('>I', a1[x-base:x-base+4])[0] == exp_data[x], 'pointer value at %08X' % x)
# text: only patched words differ
t0, t1 = sb['.text']['data'], ob['.text']['data']; tb = sb['.text']['addr']
diffs = {tb + o for o in range(0, len(t0), 4) if t0[o:o+4] != t1[o:o+4]}
want = {map_text(a - retarget.GT_SHIFT) for a, _ in patches if a < retarget.GD_LO}
check(diffs == want, 'text diff = patched sites (diff %d, want %d)' % (len(diffs), len(want)))
for a, w in patches:
    if a >= retarget.GD_LO: continue
    ra = map_text(a - retarget.GT_SHIFT); got = struct.unpack('>I', t1[ra-tb:ra-tb+4])[0]; wv = struct.unpack('>I', w)[0]
    if wv >> 26 == 18:
        off = got & 0x03FFFFFC
        if off & 0x02000000: off -= 0x04000000
        tgt = ra + off; orig_t = (a + ((wv & 0x03FFFFFC) - (0x04000000 if wv & 0x02000000 else 0)))
        check(tgt == T + (orig_t - retarget.CB) and (got & 3) == (wv & 3), 'hook branch at %08X -> %08X' % (ra, tgt))
    else:
        check(got == wv, 'plain patch at %08X' % ra)
# blob sections
bt, bd = [s for s in O if s['addr'] == T][0], [s for s in O if s['addr'] == 0x10300000][0]
check(sb['.shstrtab']['data'] == ob['.shstrtab']['data'], '.shstrtab untouched')
check(len(bt['data']) >= len(code) and len(bt['data']) % 4 == 0, 'blob text length')
stub = struct.unpack('>I', bd['data'][0x1C:0x20])[0]; check(T + len(code) <= stub < T + len(bt['data']) and struct.unpack('>I', bt['data'][stub - T:stub - T + 4])[0] == 0x4E800020, 'log stub'); check(bd['data'][0x20:0x28] == open(os.path.join(pack, 'Data.bin'), 'rb').read()[:8] and bd['data'][:0x1C] == bytes(0x1C), 'blob data header')
fi = [s for s in O if s['t'] == 0x80000004][0]['data']; ts, ds = struct.unpack('>II', fi[4:8] + fi[12:16])
check(0x02000000 + ts >= T + len(bt['data']), 'textSize covers blob'); check(T >= sb['.text']['addr'] + len(sb['.text']['data']), 'blob after .text'); check(0x10000000 + ds >= 0x10300000 + len(bd['data']), 'dataSize covers blob data')
print('sections', len(O), 'fails', len(fails))
sys.exit(1 if fails else 0)
