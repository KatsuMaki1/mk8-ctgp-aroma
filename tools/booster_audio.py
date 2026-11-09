"""Add absent DLC stream names while preserving all existing sounds and samples."""
from pathlib import Path
import struct,hashlib
import character_voice as voice,szs

def extend(source,dest,labels):
    source,dest=Path(source),Path(dest);archive=voice.Archive(source)
    missing=sorted(set(labels)-set(archive.ids))
    if not missing:return archive,[]
    pairs=[('pBGM_WU_DESERT_F' if n.endswith('_F') else 'pBGM_WU_DESERT_N',n) for n in missing]
    strings,info,ids=voice.clone_sounds(archive,pairs,allowed_kinds=(0x2201,))
    file_kind,file_at,file_size=archive.blocks[2];header=bytearray(archive.header);at=64
    for i,(kind,b) in enumerate(((0x2000,strings),(0x2001,info))):
        struct.pack_into('>HHII',header,20+i*12,kind,0,at,len(b));at+=len(b)
    struct.pack_into('>HHII',header,44,file_kind,0,at,file_size);struct.pack_into('>I',header,12,at+file_size)
    dest.parent.mkdir(parents=True,exist_ok=True);before=hashlib.sha256()
    with source.open('rb') as src,dest.open('wb') as out:
        out.write(header);out.write(strings);out.write(info);src.seek(file_at);remaining=file_size
        while remaining:
            b=src.read(min(1048576,remaining))
            if not b:raise ValueError('Truncated source FILE block')
            before.update(b);out.write(b);remaining-=len(b)
    check=voice.Archive(dest)
    if any(check.lookup(n)!=i for n,i in ids.items()):raise ValueError('Archive labels changed')
    if any(check.sound(i)!=archive.sound(i) for i in range(archive.count)):raise ValueError('Existing sound record changed')
    after=hashlib.sha256()
    with dest.open('rb') as f:
        f.seek(check.blocks[2][1])
        while b:=f.read(1048576):after.update(b)
    if before.digest()!=after.digest():raise ValueError('Sound samples changed')
    return check,missing

def known_bar(data,archive):
    """Keep source ambient sounds known by this installation; drop unknown IDs."""
    output=[];dropped=[]
    for n,b,h in szs.sarc_read(data):
        if n=='_param.bin':
            if b[:8]!=b'BARS\xfe\xff\x00\x20' or voice.u32(b,12)!=84:raise ValueError('Unexpected object bank')
            pool=voice.u32(b,24);records=[]
            for at in range(32,pool,84):
                off=pool+voice.u32(b,at);name=b[off:b.index(0,off)].decode();sound=archive.lookup(name)
                if sound is None:dropped.append(name);continue
                rec=bytearray(b[at:at+84]);struct.pack_into('>I',rec,36,sound&0xffffff);records.append(bytes(rec))
            head=bytearray(b[:32]);newpool=32+84*len(records);size=newpool+len(b)-pool
            struct.pack_into('>I',head,8,size);struct.pack_into('>II',head,20,84*len(records),newpool)
            b=bytes(head)+b''.join(records)+b[pool:]
        output.append((n,b))
    return szs.sarc_write(output,szs.sarc_aligns(data,32),struct.unpack_from('>H',data,16)[0]),dropped
