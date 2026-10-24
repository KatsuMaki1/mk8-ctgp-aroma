# Minimal RPX/ELF reader: returns list of sections with decompressed data.
import struct, zlib
def load(path):
    d = open(path, 'rb').read()
    shoff, = struct.unpack('>I', d[0x20:0x24]); ent, num, stri = struct.unpack('>HHH', d[0x2E:0x34])
    S = []
    for i in range(num):
        n, t, fl, addr, off, size, link, info, align, es = struct.unpack('>10I', d[shoff+i*ent:shoff+(i+1)*ent])
        S.append(dict(i=i, n=n, t=t, fl=fl, addr=addr, off=off, size=size, link=link, info=info, align=align, ent=es, raw=d[off:off+size] if t != 8 else b''))
    def dec(s):
        r = s['raw']
        return zlib.decompress(r[4:]) if (s['fl'] & 0x08000000 and s['t'] != 8) else r
    for s in S: s['data'] = dec(s)
    strs = S[stri]['data']
    for s in S: s['name'] = strs[s['n']:strs.index(b'\0', s['n'])].decode()
    return d, S
def word_at(S, a):
    for s in S:
        if s['t'] == 1 and s['addr'] <= a < s['addr'] + len(s['data']) and s['fl'] & 2:
            return struct.unpack('>I', s['data'][a-s['addr']:a-s['addr']+4])[0]
