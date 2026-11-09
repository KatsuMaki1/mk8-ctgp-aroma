"""Remove incompatible optional Animal Crossing spectators without moving path data."""
import struct
import byml_dump
import byml_edit

def fix(raw):
    doc=byml_dump.parse(raw)
    bad={1137,1138,1139,1140}
    keep=[i for i,x in enumerate(doc.get('Obj',[])) if x.get('ObjId') not in bad]
    if len(keep)==len(doc.get('Obj',[])):return raw,False
    out=bytearray(raw)
    u=lambda at:struct.unpack_from('>I',raw,at)[0]
    root=u(16 if raw[2:4]==b'\x00\x01' else 12)
    kt=u(4);n=u(kt)&0xffffff
    keys=[raw[kt+u(kt+4+4*i):raw.index(0,kt+u(kt+4+4*i))].decode() for i in range(n)]
    entries={keys[u(root+4+8*i)>>8]:root+4+8*i for i in range(u(root)&0xffffff)}
    arr=u(entries['Obj']+4);count=u(arr)&0xffffff
    words=arr+4+((count+3)&~3)
    types=bytes(raw[arr+4+i] for i in keep)
    values=b''.join(raw[words+4*i:words+4*i+4] for i in keep)
    block=struct.pack('>I',0xc0000000|len(keep))+types+bytes(-len(types)%4)+values
    out[arr:arr+len(block)]=block
    replacements={'MapObjIdList':[x for x in doc['MapObjIdList'] if x not in bad],
        'MapObjResList':[x for x in doc['MapObjResList'] if x not in ('DL_CmnAnimalA','DL_CmnAnimalB','DL_CmnAnimalC','DL_CmnAnimalD')]}
    result=byml_edit.root_arrays(bytes(out),replacements)
    expected=dict(doc);expected.update(replacements);expected['Obj']=[doc['Obj'][i] for i in keep]
    if byml_dump.parse(result)!=expected:raise ValueError('Unexpected spectator patch change')
    if result[4:20]!=raw[4:20]:raise ValueError('Moved original tables')
    return result,True
