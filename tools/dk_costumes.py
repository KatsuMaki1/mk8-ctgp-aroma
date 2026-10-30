"""Stage DK variants and merge their individual menu icons without replacing menus."""
from pathlib import Path
import argparse, hashlib, io, json, struct, zipfile, subprocess, tempfile
from PIL import Image, ImageOps
import backup, bflim, costumes, szs

def unpack(data):
    return szs.yaz0_decode(data) if data[:4] == b'Yaz0' else data

def hashed_member(packed, name):
    raw = unpack(packed)
    if raw[:4] != b'SARC': raise ValueError('Expected SARC')
    offset = struct.unpack_from('>I', raw, 12)[0]
    matches = []
    for i in range(struct.unpack_from('>H', raw, 26)[0]):
        h, attr, a, b = struct.unpack_from('>IIII', raw, 32+i*16)
        if h == szs.sarc_hash(name): matches.append(raw[offset+a:offset+b])
    if len(matches) != 1: raise ValueError('Missing or ambiguous archive member: '+name)
    return matches[0]

def merge_hashed(packed, additions):
    """Preserve named/unnamed SARC entries and add texture hashes directly."""
    raw = unpack(packed)
    if raw[:4] != b'SARC': raise ValueError('Expected SARC')
    count = struct.unpack_from('>H',raw,26)[0]
    offset = struct.unpack_from('>I',raw,12)[0]
    old_sfnt = 32 + count*16
    names = raw[old_sfnt:offset]
    entries = {}
    positions = {}
    for i in range(count):
        h,attr,a,b = struct.unpack_from('>IIII',raw,32+i*16)
        if h in entries: raise ValueError('Duplicate SARC hash')
        entries[h] = (attr,raw[offset+a:offset+b])
        positions[h] = (a,b)
    original = dict(entries)
    for name,data in additions.items():
        h=szs.sarc_hash(name)
        if h in entries and entries[h][1]!=data: raise ValueError('Texture hash collision')
        entries[h] = entries.get(h,(0,data))
    new_offset=(32+len(entries)*16+len(names)+8191)&~8191
    header=bytearray(raw[:32]);struct.pack_into('>H',header,26,len(entries))
    nodes=bytearray();blob=bytearray(raw[offset:])
    for h,(attr,data) in sorted(entries.items()):
        if h in positions:
            a,b = positions[h]
        else:
            blob.extend(b'\0'*((-len(blob))%2048))
            a=len(blob);blob.extend(data);b=len(blob)
        nodes.extend(struct.pack('>IIII',h,attr,a,b))
    result=header+nodes+names
    result.extend(b'\0'*(new_offset-len(result)));result.extend(blob)
    struct.pack_into('>II',result,8,len(result),new_offset)
    # Every original hash, attributes and payload is retained byte-for-byte.
    actual={}
    for i in range(len(entries)):
        h,attr,a,b=struct.unpack_from('>IIII',result,32+i*16)
        actual[h]=(attr,bytes(result[new_offset+a:new_offset+b]))
    if actual!=entries or any(actual[h]!=v for h,v in original.items()): raise ValueError('SARC verification failed')
    return szs.yaz0_store(result) if packed[:4]==b'Yaz0' else bytes(result)

def install_menu_icons(base,content):
    base,content=Path(base),Path(content)
    target=content/'ui/cmn/menu.szs'
    source=target if target.exists() else base/'ui/cmn/menu.szs'
    icons={}
    for label in ('FunkyKong','Snorlax'):
        root=content/'custom/costumes/DK'/label
        manifest=json.loads((root/'manifest.json').read_text())
        data=(root/manifest['icon']).read_bytes()
        if hashlib.sha256(data).hexdigest()!=manifest['icon_sha256']: raise ValueError('Icon checksum mismatch')
        icons[manifest['icon']]=data
    result=merge_hashed(source.read_bytes(),icons)
    # Menu heaps also hold the compressed input buffer. Literal-only Yaz0
    # needlessly grows it by tens of MB; use the installed native compressor.
    compressor = Path(r'C:\Program Files\Wiimm\SZS\wszst.exe')
    if not compressor.is_file(): raise ValueError('wszst compressor required for menu icons')
    with tempfile.TemporaryDirectory(prefix='mk8-menu-icons-') as tmp:
        src, dst = Path(tmp)/'menu.sarc', Path(tmp)/'menu.szs'
        src.write_bytes(unpack(result))
        subprocess.run([str(compressor),'compress',str(src),'--yaz0','--dest',str(dst)],check=True,capture_output=True)
        compressed=dst.read_bytes()
        if unpack(compressed)!=unpack(result): raise ValueError('Menu compression roundtrip failed')
        result=compressed
    backup.save(content,target,tag='before_dk_direct_icons')
    costumes.atomic_write(target,result)
    for n,d in icons.items():
        if hashed_member(result,n)!=d: raise ValueError('Icon verification failed')
    print('Verified both icons directly in menu.szs; all original entries preserved')

def stage(base, content, funky, snorlax):
    base, content = Path(base), Path(content)
    original = costumes.inspect_model((base/'driver/DK.szs').read_bytes())
    template = hashed_member((base/'ui/cmn/menu.szs').read_bytes(), 'timg/tc_Chara_DK^l.bflim')
    writes, icons, manifests = {}, {}, []
    horn = (base/'ui/cmn/a_race/timg/ym_HornEmblemDK_00^h.bflim').read_bytes()
    for variant, label, source in ((1,'FunkyKong',funky),(2,'Snorlax',snorlax)):
        with zipfile.ZipFile(source) as archive:
            model = archive.read('content/driver/DK.szs')
            info = costumes.inspect_model(model)
            if not set(original['skeletal_animations']).issubset(info['skeletal_animations']):
                raise ValueError('Missing DK animations: '+label)
            if variant == 1:
                icon = hashed_member(archive.read('content/ui/cmn/menu.szs'), 'timg/tc_Chara_DK^l.bflim')
            else:
                image = Image.open(io.BytesIO(archive.read('Icons/MenuIcon.png'))).convert('RGBA')
                image = ImageOps.pad(image, (128,128), method=Image.Resampling.LANCZOS, color=(0,0,0,0))
                icon = bflim.encode_rgba8(image, template)
                if bflim.decode_rgba8(icon).tobytes() != image.tobytes(): raise ValueError('Icon roundtrip failed')
        root = content/'custom/costumes/DK'/label
        writes[root/'driver/DK.szs'] = model
        name = 'timg/ct_Chara_'+label+'^l.bflim'
        icons[name] = icon
        writes[root/name] = icon
        writes[content/f'ui/cmn/a_race/timg/ym_HornEmblemDK_0{variant}^h.bflim'] = horn
        manifest = {'variant':variant,'name':label,'source':str(source),'model':info,
                    'icon':name,'icon_sha256':hashlib.sha256(icon).hexdigest(),
                    'note':'Authored internal BFRES names preserved; gameplay validation required.'}
        manifests.append(manifest)
        writes[root/'manifest.json'] = (json.dumps(manifest,indent=2)+'\n').encode()
    target = content/'ui/cmn/ctgp.szs'
    packed = target.read_bytes(); raw = unpack(packed)
    entries, offset, version = szs.sarc_info(raw)
    if any(not n or szs.sarc_hash(n) != h for n,d,h,start in entries): raise ValueError('ctgp.szs must have valid named members')
    files = {n:d for n,d,h,start in entries}
    for n,d in icons.items():
        if n in files and files[n] != d: raise ValueError('Icon conflict: '+n)
    updated = {**files,**icons}
    aligns = szs.sarc_aligns(raw); aligns.update({n:2048 for n in icons})
    rebuilt = szs.sarc_write(list(updated.items()), aligns, version)
    if {n:d for n,d,h,start in szs.sarc_info(rebuilt)[0]} != updated: raise ValueError('Archive verification failed')
    # Preflight all resources before changing any file.
    for path,data in writes.items():
        if path.exists() and path.read_bytes() != data: raise ValueError('Existing resource differs: '+str(path))
    backup.save(content,target,tag='before_dk_costume_icons')
    for path,data in writes.items(): costumes.atomic_write(path,data)
    costumes.atomic_write(target,szs.yaz0_store(rebuilt) if packed[:4] == b'Yaz0' else rebuilt)
    print('Staged DK variants, two menu icons, and variant horn dependencies; preserved',len(files),'existing CTGP members')
    for m in manifests: print(m['name'],m['model']['models'])

if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--base',required=True);p.add_argument('--content',required=True)
    p.add_argument('--funky',required=True);p.add_argument('--snorlax',required=True)
    a=p.parse_args();stage(a.base,a.content,a.funky,a.snorlax)
