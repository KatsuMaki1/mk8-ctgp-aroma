"""Prepare independent R.O.B. resources without overriding Morton or menus.

This is staging only. A runtime driver-slot extension is required to load these
resources. Full menu/common/MSBT files supplied by replacement mods are ignored.
"""
from pathlib import Path
import argparse, hashlib, json, struct
import costumes, szs, character_tables

def digest(data): return hashlib.sha256(data).hexdigest()

def independent_bfres(raw,name='ROB'):
    """Give a driver file a distinct resource name, preserving model keys."""
    if raw[:10]!=b'FRES\x03\x04\x00\x04\xfe\xff' or struct.unpack_from('>I',raw,12)[0]!=len(raw):
        raise ValueError('Unexpected Wii U BFRES')
    encoded=name.encode('ascii')
    if not encoded or len(encoded)>32:raise ValueError('Invalid resource name')
    result=bytearray(raw);result.extend(bytes(-len(result)%4))
    at=len(result);result.extend(struct.pack('>I',len(encoded))+encoded+bytes(1));result.extend(bytes(-len(result)%4))
    struct.pack_into('>i',result,20,at+4-20);struct.pack_into('>I',result,12,len(result))
    # These dictionaries include the model/animation names expected by the
    # native Morton rig. Only the root file name is independent.
    for field in (0x20,0x24,0x28):
        if costumes.bfres_names(raw,field)!=costumes.bfres_names(result,field):raise ValueError('Driver dictionary changed')
    return bytes(result)

def hashed_entries(data):
    raw = szs.yaz0_decode(data) if data[:4] == b'Yaz0' else data
    if raw[:4] != b'SARC': raise ValueError('Expected SARC')
    off = struct.unpack_from('>I', raw, 12)[0]
    count = struct.unpack_from('>H', raw, 26)[0]
    entries = {}
    for h, attr, a, b in struct.iter_unpack('>IIII', raw[32:32+16*count]):
        if h in entries or not 0 <= a <= b <= len(raw)-off:
            raise ValueError('Invalid SARC directory')
        entries[h] = raw[off+a:off+b]
    return entries

def prepare(source, base, content, output):
    source, base, content, output = map(Path, (source, base, content, output))
    if output.exists(): raise ValueError('Staging destination already exists')
    model = (source/'driver/Morton.szs').read_bytes()
    info = costumes.inspect_model(model)
    original = costumes.inspect_model((base/'driver/Morton.szs').read_bytes())
    if 'Morton' not in info['models']: raise ValueError('Wrong donor model')
    files = {}
    # Private paths keep the author's model/internal bank names unchanged.
    resources = ['driver/Morton.szs', 'audio/driver/SNDG_Morton.bars',
                 'audio/driver_menu/SNDG_M_Morton.bars']
    resources += [p.relative_to(source).as_posix() for folder in ('kart', 'ui/cmn/a_menu', 'ui/cmn/a_race')
                  for p in sorted((source/folder).rglob('*')) if p.is_file()]
    for rel in resources:
        data = (source/rel).read_bytes()
        if rel.endswith('.bars'): hashed_entries(data)
        files['custom/characters/ROB/'+rel] = data
    icons = {}
    for archive, names in (
        ('menu', ['tc_Chara_Morton^l.bflim']),
        ('common', ['tc_MapChara_Morton^l.bflim','tc_edChara_Morton^l.bflim'])):
        entries = hashed_entries((source/('ui/cmn/'+archive+'.szs')).read_bytes())
        for name in names:
            key = szs.sarc_hash('timg/'+name)
            if key not in entries: continue
            dest = 'timg/'+name.replace('Morton','ROB')
            icons[dest] = entries[key]
            files['custom/characters/ROB/'+archive+'/'+dest] = entries[key]
    if 'timg/tc_Chara_ROB^l.bflim' not in icons:
        raise ValueError('Missing authored character icon')
    params = {}
    for name in ('Parts','Performance'):
        rel='common/mush/'+name+'.bin'
        old=(content/rel).read_bytes()
        new=character_tables.expand(old)
        files[rel]=new
        params[rel]={'source_sha256':digest(old),'output_sha256':digest(new)}
    # Ensure that donor 28 really resolves to Morton in this exact input.
    drvr=dict(character_tables.sections((content/'common/mush/Parts.bin').read_bytes())[1])[b'DRVR']
    pool=struct.unpack_from('>I',drvr,8)[0]
    nameoff=struct.unpack_from('>I',drvr,12+28*500+16)[0]
    if drvr[pool+nameoff:pool+nameoff+4] != b'Mtn'+bytes(1):
        raise ValueError('Driver 28 is not Morton')
    manifest={'format':'mk8-independent-character-staging-v1','character_id':37,
              'name':'R.O.B.','stats_donor':28,'stats_donor_name':'Morton',
              'model':info,'missing_donor_animations':sorted(set(original['skeletal_animations'])-set(info['skeletal_animations'])),
              'parameters':params,'icons':{n:digest(d) for n,d in icons.items()},
              'status':'staged-only; runtime-slot-extension-required',
              'files':{n:{'sha256':digest(d),'bytes':len(d)} for n,d in files.items()}}
    output.mkdir(parents=True)
    for rel,data in files.items():
        p=output/'files'/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('source','base','content','output'):p.add_argument('--'+name,required=True,type=Path)
    args=p.parse_args()
    result=prepare(args.source,args.base,args.content,args.output)
    print(json.dumps({k:result[k] for k in ('status','character_id','stats_donor_name','icons','missing_donor_animations')},indent=2))
