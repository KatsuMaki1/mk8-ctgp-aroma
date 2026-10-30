"""Patch BFRES index buffers and FTEX data in place, preserving all other bytes.

Inputs are exported by Program.cs and simplify.mjs. No BFRES reserialization.
"""
from pathlib import Path
import struct,json,re,hashlib
def patch(folder):
    folder=Path(folder);original=(folder/'model.bfres').read_bytes();data=bytearray(original);ranges=[]
    def u(p):return struct.unpack_from('>I',original,p)[0]
    def ref(p):return p+struct.unpack_from('>i',original,p)[0] if u(p) else 0
    def string(p):return original[p:original.index(0,p)].decode()
    def put(p,b):
        assert 0<=p<=len(data)-len(b)
        data[p:p+len(b)]=b;ranges.append((p,p+len(b)))
    def word(p,v):put(p,struct.pack('>I',v))
    shapes={}
    for match in re.finditer(b'FSHP',original):
        p=match.start()
        try:
            name=string(ref(p+4));mesh=ref(p+0x24);buffer=ref(mesh+0x14);offset=ref(buffer+0x14)
            shapes[(name,offset)]=(p,mesh,buffer)
        except (ValueError,UnicodeDecodeError,struct.error):continue
    changed=[]
    for row in json.loads((folder/'meshes/meshes.json').read_text()):
        p=folder/'meshes'/(str(row['id'])+'.newidx')
        if not p.exists():continue
        _,mesh,buffer=shapes[(row['Name'],row['buffer_offset'])]
        assert u(mesh+8)==row['indices'] and u(mesh+0x18)==row['first']
        assert struct.unpack_from('>H',original,mesh+12)[0]==1
        sub=ref(mesh+0x10);assert u(sub)==0 and u(sub+4)==row['indices']
        b=p.read_bytes();ids=struct.unpack('<'+'I'*(len(b)//4),b);relative=[x-row['first'] for x in ids]
        fmt=row['index_format'];size=2 if '16' in fmt else 4;endian='<' if 'Little' in fmt else '>'
        payload=struct.pack(endian+('H' if size==2 else 'I')*len(ids),*relative)
        oldsize=u(buffer+4);assert oldsize==row['indices']*size and len(payload)<oldsize
        offset=row['buffer_offset'];assert offset==ref(buffer+0x14)
        before=original[offset:offset+oldsize]
        exported=(folder/'meshes'/(str(row['id'])+'.idx')).read_bytes();allids=struct.unpack('<'+'I'*(len(exported)//4),exported)
        assert struct.pack(endian+('H' if size==2 else 'I')*len(allids),*(x-row['first'] for x in allids))==before
        put(offset,payload+bytes(oldsize-len(payload)));word(buffer+4,len(payload));word(mesh+8,len(ids));word(sub+4,len(ids))
        changed.append({'name':row['Name'],'before_triangles':row['indices']//3,'after_triangles':len(ids)//3})
    textures={}
    for match in re.finditer(b'FTEX',original):
        p=match.start()
        try:textures[string(ref(p+0xa8))]=p
        except (ValueError,UnicodeDecodeError,struct.error):continue
    texchanges=json.loads((folder/'textures/textures.json').read_text())
    for t in texchanges:
        p=textures[t['Name']];assert u(p+8)==t['old_width'] and u(p+12)==t['old_height']
        b=(folder/'textures'/(str(t['id'])+'.data')).read_bytes();m=(folder/'textures'/(str(t['id'])+'.mips')).read_bytes()
        oldb,oldm=u(p+0x24),u(p+0x2c);assert len(b)<=oldb and len(m)<=oldm
        assert oldb+oldm==t['old_bytes']
        put(ref(p+0xb0),b+bytes(oldb-len(b)))
        if oldm:put(ref(p+0xb4),m+bytes(oldm-len(m)))
        for off,key in [(8,'width'),(12,'height'),(0x14,'mip_count'),(0x34,'tile_mode'),(0x38,'swizzle'),(0x3c,'alignment'),(0x40,'pitch')]:word(p+off,t[key])
        word(p+0x24,len(b));word(p+0x2c,len(m));word(p+0x78,0);word(p+0x7c,t['mip_count'])
        for i in range(13):word(p+0x44+i*4,t['offsets'][i] if i<len(t['offsets']) else 0)
        for i,v in enumerate(t['registers']):word(p+0x8c+i*4,v)
    # Exact diff coverage: nothing outside the declared draw/texture ranges changes.
    cursor=0
    for a,b in sorted(ranges):
        if a>cursor:assert original[cursor:a]==data[cursor:a],'Unrelated bytes changed'
        cursor=max(cursor,b)
    assert original[cursor:]==data[cursor:]
    out=folder/'optimized.bfres';out.write_bytes(data)
    report={'changed_meshes':changed,'textures':texchanges,'patch_ranges':ranges,'original_sha256':hashlib.sha256(original).hexdigest(),'optimized_sha256':hashlib.sha256(data).hexdigest(),'all_unrelated_bytes_unchanged':True}
    (folder/'patch_report.json').write_text(json.dumps(report,indent=2))
    print(folder.name,'patched meshes',len(changed),'textures',len(texchanges),'texture MiB saved',round(sum(x['old_bytes']-x['bytes'] for x in texchanges)/1048576,2),flush=True)
if __name__=='__main__':
    import sys
    for folder in sorted(Path(sys.argv[1]).glob('Gu_*')):
        if (folder/'meshes/meshes.json').exists():patch(folder)
