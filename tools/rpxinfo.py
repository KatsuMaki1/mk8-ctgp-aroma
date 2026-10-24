import struct, sys, zlib
d = open(sys.argv[1], 'rb').read()
print('ident', d[:16].hex(), 'type/mach', d[16:20].hex(), 'entry %08X' % struct.unpack('>I', d[24:28])[0])
e_shoff, = struct.unpack('>I', d[0x20:0x24]); shentsize, shnum, shstrndx = struct.unpack('>HHH', d[0x2E:0x34])
print('shoff', hex(e_shoff), 'shnum', shnum, 'shstrndx', shstrndx, 'phnum', struct.unpack('>H', d[0x2C:0x2E])[0])
S = []
for i in range(shnum):
    n, t, fl, addr, off, size, link, info, align, ent = struct.unpack('>10I', d[e_shoff+i*shentsize:e_shoff+(i+1)*shentsize])
    S.append(dict(i=i, n=n, t=t, fl=fl, addr=addr, off=off, size=size, link=link, info=info, align=align, ent=ent))
strs = d[S[shstrndx]['off']:S[shstrndx]['off']+S[shstrndx]['size']]
if S[shstrndx]['fl'] & 0x08000000: strs = zlib.decompress(strs[4:])
for s in S:
    s['name'] = strs[s['n']:strs.index(b'\0', s['n'])].decode()
    print(f"{s['i']:2d} {s['name']:<16} type={s['t']:08X} fl={s['fl']:08X} addr={s['addr']:08X} off={s['off']:08X} size={s['size']:08X} link={s['link']} info={s['info']} align={s['align']}")
fi = [s for s in S if s['t'] == 0x80000004][0]
raw = d[fi['off']:fi['off']+fi['size']]
if fi['fl'] & 0x08000000: raw = zlib.decompress(raw[4:])
names = 'magic version textSize textAlign dataSize dataAlign loadSize loadAlign tempSize trampAdjust sdaBase sda2Base stackSize filename flags heapSize tagOffset minVersion compressionLevel trampAddition fileInfoPad cafeSdkVersion cafeSdkRevision tlsModuleIndex tlsAlignShift runtimeFileInfoSize'.split()
vals = struct.unpack('>' + 'I'*13 + 'I'*4 + 'I'*2 + 'i' + 'I'*3 + 'HH' + 'HH'.replace('HH','HH') + 'I', raw[:0x60]) if False else None
print('fileinfo', len(raw), raw[:0x60].hex())
for k, o in zip(names, range(0, 0x60, 4)): print(' ', k, hex(struct.unpack('>I', raw[o:o+4])[0]))
