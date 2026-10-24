import struct,sys
def parse(b):
    assert b[:2]==b'BY'
    ver,=struct.unpack('>H',b[2:4]); kt,st,root=struct.unpack('>III',b[4:16])
    def tbl(o):
        n=struct.unpack('>I',b[o:o+4])[0]&0xFFFFFF
        offs=struct.unpack('>%dI'%(n+1),b[o+4:o+8+4*n]); return [b[o+x:b.index(b'\0',o+x)].decode() for x in offs[:-1]]
    keys=tbl(kt); strs=tbl(st)
    def node(t,v):
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
if __name__=='__main__':
    import json; d=parse(open(sys.argv[1],'rb').read())
    def show(x,ind=0,maxn=3):
        print(type(x).__name__, list(x.keys())[:30] if isinstance(x,dict) else len(x) if isinstance(x,list) else x)
    show(d)
    for k,v in d.items():
        if isinstance(v,list): print(k,len(v), (list(v[0].items())[:25] if v and isinstance(v[0],dict) else v[:3]))
        else: print(k,v)
