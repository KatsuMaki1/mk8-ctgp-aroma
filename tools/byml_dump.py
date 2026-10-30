import struct,sys
def parse(b):
    assert b[:2]==b'BY'
    ver,=struct.unpack('>H',b[2:4]); kt,st,root=struct.unpack('>III',b[4:16])
    if ver == 1: root=struct.unpack_from('>I',b,16)[0]
    def tbl(o):
        n=struct.unpack('>I',b[o:o+4])[0]&0xFFFFFF
        offs=struct.unpack('>%dI'%(n+1),b[o+4:o+8+4*n]); return [b[o+x:b.index(b'\0',o+x)].decode() for x in offs[:-1]]
    keys=tbl(kt); strs=tbl(st)
    def node(t,v):
        if t==0xff: return None
        if t==0xA0: return strs[v]
        if t==0xD0: return bool(v)
        if t in (0xD1,0xD3): return v if t==0xD3 else struct.unpack('>i',struct.pack('>I',v))[0]
        if t==0xD2: return struct.unpack('>f',struct.pack('>I',v))[0]
        if t==0xC0:
            n=b[v+1]<<16|b[v+2]<<8|b[v+3]; ts=b[v+4:v+4+n]; o=v+4+((n+3)&~3)
            return [node(ts[i],struct.unpack('>I',b[o+4*i:o+4*i+4])[0]) for i in range(n)]
        if t==0xC1:
            n=b[v+1]<<16|b[v+2]<<8|b[v+3]; d={}
            for i in range(n):
                e=b[v+4+8*i:v+12+8*i]; k=(e[0]<<16)|(e[1]<<8)|e[2]; d[keys[k]]=node(e[3],struct.unpack('>I',e[4:8])[0])
            return d
        return ('?%x'%t,v)
    return node(b[root],root)

def build(value):
    """Canonical big-endian v1 BYAML: sorted tables, root before child nodes.

    The game reader does not accept the backward child references produced by
    appending a new root to an old file, even if our inspection parser reads it.
    """
    keys=set();strings=set()
    def collect(v):
        if isinstance(v,dict):
            keys.update(v)
            for x in v.values():collect(x)
        elif isinstance(v,list):
            for x in v:collect(x)
        elif isinstance(v,str):strings.add(v)
    collect(value);keys=sorted(keys);strings=sorted(strings);out=bytearray(20)
    def align():out.extend(bytes(-len(out)%4))
    def write_table(values):
        align();pos=len(out);texts=[v.encode()+b'\0' for v in values]
        offset=4+4*(len(texts)+1);offsets=[]
        for text in texts:offsets.append(offset);offset+=len(text)
        offsets.append(offset)
        out.extend(struct.pack('>I',0xc2000000|len(texts))+struct.pack('>'+str(len(offsets))+'I',*offsets)+b''.join(texts))
        return pos
    kt=write_table(keys);st=write_table(strings)
    def write_node(v):
        if isinstance(v,bool):return 0xd0,int(v)
        if isinstance(v,int):
            if not -0x80000000<=v<=0xffffffff:raise ValueError('BYAML integer outside 32-bit range')
            return (0xd1 if v<0x80000000 else 0xd3),v&0xffffffff
        if isinstance(v,float):return 0xd2,struct.unpack('>I',struct.pack('>f',v))[0]
        if isinstance(v,str):return 0xa0,strings.index(v)
        if v is None:return 0xff,0
        if not isinstance(v,(list,dict)):raise TypeError('Unsupported BYAML value: '+str(type(v)))
        align();pos=len(out);n=len(v)
        if isinstance(v,list):
            out.extend(bytes(4+((n+3)&~3)+4*n));struct.pack_into('>I',out,pos,0xc0000000|n)
            for i,x in enumerate(v):
                t,data=write_node(x);out[pos+4+i]=t
                struct.pack_into('>I',out,pos+4+((n+3)&~3)+4*i,data)
            return 0xc0,pos
        out.extend(bytes(4+8*n));struct.pack_into('>I',out,pos,0xc1000000|n)
        for i,k in enumerate(sorted(v)):
            t,data=write_node(v[k]);struct.pack_into('>II',out,pos+4+8*i,keys.index(k)<<8|t,data)
        return 0xc1,pos
    if not isinstance(value,(list,dict)):raise TypeError('BYAML root must be an array or dictionary')
    _,root=write_node(value);struct.pack_into('>2sH4I',out,0,b'BY',1,kt,st,0,root)
    return bytes(out)
if __name__=='__main__':
    import json; d=parse(open(sys.argv[1],'rb').read())
    def show(x,ind=0,maxn=3):
        print(type(x).__name__, list(x.keys())[:30] if isinstance(x,dict) else len(x) if isinstance(x,list) else x)
    show(d)
    for k,v in d.items():
        if isinstance(v,list): print(k,len(v), (list(v[0].items())[:25] if v and isinstance(v[0],dict) else v[:3]))
        else: print(k,v)
