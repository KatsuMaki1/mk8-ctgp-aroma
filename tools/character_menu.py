"""Add one named character part and the authored R.O.B. icon to current CTGP UI."""
from pathlib import Path
import json,struct,subprocess,tempfile
import character_assets as assets,bflyt,szs

LAYOUTS=(0xbb79d54b,0x480a7cb8)

def coordinates(index):return (-260.+104.*(index%6),228.-76.*(index//6),0.68,0.68)

def texture_reference(section,name):
    n=struct.unpack_from('>H',section,8)[0]
    offsets=struct.unpack_from('>%dI'%n,section,12)
    names=[bflyt.cstr(section[12+o:]) for o in offsets]
    if name in names:return section
    names.append(name);strings=bytearray();pointers=[]
    for value in names:
        pointers.append(len(names)*4+len(strings));strings.extend(value.encode()+bytes(1))
    header=bytearray(section[:12]);struct.pack_into('>H',header,8,len(names))
    result=header+struct.pack('>%dI'%len(names),*pointers)+strings
    result.extend(bytes(-len(result)%4));struct.pack_into('>I',result,4,len(result))
    return result

def layout(data):
    parts=[(t,bytearray(data[o:o+n])) for t,o,n in bflyt.sections(data)]
    parts=[(t,texture_reference(b,'tc_Chara_ROB^l.bflim') if t=='txl1' else b) for t,b in parts]
    indices=[]
    for i,(t,b) in enumerate(parts):
        name=bflyt.cstr(b[12:36]) if t=='prt1' else ''
        if name.startswith('L_Chara_') and name[8:].isdigit():
            index=int(name[8:]);indices.append(index)
            if index>=36:raise ValueError('Character layout already expanded')
            x,y,sx,sy=coordinates(index)
            struct.pack_into('>ff',b,44,x,y);struct.pack_into('>ff',b,68,sx,sy)
    if indices!=list(range(36)):raise ValueError('Unexpected character parts')
    last=next(i for i,(t,b) in enumerate(parts) if t=='prt1' and bflyt.cstr(b[12:36])=='L_Chara_35')
    new=bytearray(parts[last][1]);new[12:36]=b'L_Chara_36'.ljust(24,bytes(1))
    # Stock DLC parts start hidden and are revealed by their own animation.
    # The new independent part has no stock visibility animation.
    new[8]|=1
    x,y,sx,sy=coordinates(36);struct.pack_into('>ff',new,44,x,y);struct.pack_into('>ff',new,68,sx,sy)
    parts.insert(last+1,('prt1',new))
    header=bytearray(data[:20]);body=b''.join(b for t,b in parts)
    struct.pack_into('>I',header,12,20+len(body));struct.pack_into('>H',header,16,len(parts))
    result=bytes(header)+body
    if len(bflyt.sections(result))!=len(parts):raise ValueError('Layout readback differs')
    return result

def animation(data):
    result=bytearray(data);changed=0
    for t,p,size in bflyt.sections(data):
        if t!='pai1':continue
        block=data[p:p+size];count=struct.unpack_from('>H',block,14)[0];table=struct.unpack_from('>I',block,16)[0]
        for entry in struct.unpack_from('>%dI'%count,block,table):
            name=bflyt.cstr(block[entry:entry+28])
            if not name.startswith('L_Chara_') or not name[8:].isdigit():continue
            index=int(name[8:])
            if index>=36:raise ValueError('Unexpected animation target')
            x,y,sx,sy=coordinates(index);values={0:x,1:y,6:sx,7:sy}
            for rel in struct.unpack_from('>%dI'%block[entry+28],block,entry+32):
                tag=entry+rel;kind=block[tag:tag+4]
                if kind not in (b'FLPA',b'FLVI'):continue
                for r in struct.unpack_from('>%dI'%block[tag+4],block,tag+8):
                    target=tag+r;channel=block[target+1];curve=block[target+2]
                    n=struct.unpack_from('>H',block,target+4)[0];off=struct.unpack_from('>I',block,target+8)[0]
                    if kind==b'FLPA' and channel in values:
                        if curve!=2:raise ValueError('Unexpected pane animation curve')
                        for k in range(n):struct.pack_into('>ff',result,p+target+off+k*12+4,values[channel],0.)
                        changed+=1
                    elif kind==b'FLVI':
                        if curve!=1:raise ValueError('Unexpected visibility curve')
                        for k in range(n):struct.pack_into('>H',result,p+target+off+k*8+4,1)
    if not changed:raise ValueError('No character transforms')
    return bytes(result)

def replace_archive(data,replacements,additions):
    raw=szs.yaz0_decode(data) if data[:4]==b'Yaz0' else data
    original=assets.hashed_entries(raw)
    count=struct.unpack_from('>H',raw,26)[0];off=struct.unpack_from('>I',raw,12)[0]
    old_sfnt=32+count*16;names=raw[old_sfnt:off]
    items={h:(attr,a,b) for h,attr,a,b in struct.iter_unpack('>IIII',raw[32:old_sfnt])}
    if not set(replacements)<=set(items):raise ValueError('Missing replacement member')
    all_values={**replacements}
    for name,d in additions.items():
        h=szs.sarc_hash(name)
        if h in items:raise ValueError('Icon hash already exists')
        items[h]=(0,0,0);all_values[h]=d
    newoff=(32+len(items)*16+len(names)+8191)&~8191
    # Repack once in original physical order. Do not leave dead copies of the
    # replaced layouts/animations in the fixed-budget menu heap.
    blob=bytearray();positions={}
    order=sorted(items,key=lambda h:(h not in original,items[h][1],h))
    for h in order:
        attr,a,b=items[h]
        if h in all_values:payload=all_values[h]
        else:payload=raw[off+a:off+b]
        alignment=2048 if h not in original else 4
        if h in original:
            while alignment<8192 and (off+a)%(alignment*2)==0:alignment*=2
        blob.extend(bytes((-(newoff+len(blob)))%alignment));a=len(blob);blob.extend(payload);b=len(blob)
        positions[h]=(a,b)
    nodes=bytearray()
    for h,(attr,_,_) in sorted(items.items()):
        a,b=positions[h];nodes.extend(struct.pack('>IIII',h,attr,a,b))
    header=bytearray(raw[:32]);struct.pack_into('>H',header,26,len(items))
    struct.pack_into('>II',header,8,newoff+len(blob),newoff)
    result=header+nodes+names;result.extend(bytes(newoff-len(result)));result.extend(blob)
    before=assets.hashed_entries(raw);after=assets.hashed_entries(bytes(result))
    if any(after[h]!=(replacements.get(h,d)) for h,d in before.items()):raise ValueError('Unrelated menu member differs')
    return bytes(result)

def prepare(content,staged,output):
    content,staged,output=map(Path,(content,staged,output))
    old=(content/'ui/cmn/menu.szs').read_bytes();entries=assets.hashed_entries(old)
    replacements={h:layout(entries[h]) for h in LAYOUTS}
    for h,d in entries.items():
        if d[:4]==b'FLAN' and b'L_Chara_00' in d:replacements[h]=animation(d)
    import bflim
    authored=(staged/'files/custom/characters/ROB/menu/timg/tc_Chara_ROB^l.bflim').read_bytes()
    image=bflim.decode_rgba8(authored)
    footer=bytearray(authored[-40:]);footer[34]=23
    size=16384;struct.pack_into('>I',footer,12,size+40);struct.pack_into('>I',footer,36,size)
    icon=bflim.encode_bc3(image,bytes(size)+bytes(footer))
    raw=replace_archive(old,replacements,{'timg/tc_Chara_ROB^l.bflim':icon})
    with tempfile.TemporaryDirectory() as tmp:
        source=Path(tmp)/'menu.sarc';dest=Path(tmp)/'menu.szs';source.write_bytes(raw)
        subprocess.run(['C:/Program Files/Wiimm/SZS/wszst.exe','compress',str(source),'--yaz0','--dest',str(dest)],check=True,capture_output=True)
        result=dest.read_bytes()
    if szs.yaz0_decode(result)!=raw:raise ValueError('Menu compression readback differs')
    output.mkdir(parents=True,exist_ok=True);(output/'menu.szs').write_bytes(result)
    manifest={'source_sha256':assets.digest(old),'output_sha256':assets.digest(result),'changed_members':[hex(h) for h in replacements],
              'added_icon_sha256':assets.digest(icon),'status':'uninstalled-candidate'}
    (output/'menu.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('content','staged','output'):p.add_argument('--'+n,required=True,type=Path)
    a=p.parse_args();print(json.dumps(prepare(a.content,a.staged,a.output),indent=2))
