"""Patch root scalar arrays without reserializing opaque BYAML path tables."""
import struct

def root_arrays(raw,replacements):
    if raw[:2]!=b'BY':raise ValueError('Expected big-endian BYAML')
    out=bytearray(raw);u=lambda at:struct.unpack_from('>I',raw,at)[0]
    version=struct.unpack_from('>H',raw,2)[0];root=u(16 if version==1 else 12)
    def table(at):
        n=u(at)&0xffffff
        return [raw[at+u(at+4+4*i):raw.index(0,at+u(at+4+4*i))].decode() for i in range(n)]
    keys=table(u(4));strings=table(u(8));added=[v for a in replacements.values() for v in a if isinstance(v,str) and v not in strings]
    strings+=list(dict.fromkeys(added))
    def align():out.extend(bytes(-len(out)%4))
    if added:
        align();start=len(out);blobs=[s.encode()+b'\0' for s in strings];offset=4+4*(len(blobs)+1);offsets=[]
        for b in blobs:offsets.append(offset);offset+=len(b)
        offsets.append(offset);out.extend(struct.pack('>I',0xc2000000|len(blobs))+struct.pack('>'+str(len(offsets))+'I',*offsets)+b''.join(blobs))
        struct.pack_into('>I',out,8,start)
    if raw[root]!=0xc1:raise ValueError('Root is not a dictionary')
    entries={keys[u(root+4+8*i)>>8]:root+4+8*i for i in range(u(root)&0xffffff)}
    for key,values in replacements.items():
        entry=entries[key]
        if raw[entry+3]!=0xc0:raise ValueError('Expected root array: '+key)
        align();start=len(out);types=[];words=[]
        for value in values:
            if isinstance(value,str):types.append(0xa0);words.append(strings.index(value))
            elif isinstance(value,int):types.append(0xd1);words.append(value&0xffffffff)
            else:raise TypeError('Only string/integer arrays are supported')
        out.extend(struct.pack('>I',0xc0000000|len(values))+bytes(types)+bytes(-len(types)%4)+struct.pack('>'+str(len(words))+'I',*words))
        struct.pack_into('>I',out,entry+4,start)
    return bytes(out)
