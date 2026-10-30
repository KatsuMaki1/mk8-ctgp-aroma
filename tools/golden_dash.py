"""Build a content-only Golden Dash overlay for the validated Aroma v0.20 pack."""
import argparse, hashlib, json, struct
from pathlib import Path
from zipfile import ZipFile
import byml_dump, cup0, szs

TITLE='000500001010ED00'
TRACKS=(
    ('Gu_WaterPark','Gu_BcpParis','Paris Promenade','Tour','Gu_FirstCircuit'),
    ('G3ds_MusicPark','Gu_BcpToad','Toad Circuit','3DS','Gu_WaterPark'),
    ('G64_PeachCircuit','Gu_BcpChoco','Choco Mountain','N64','Gu_Cake'),
    ('Dwii_WariosMine','Gu_BcpCoconut','Coconut Mall','Wii','Gu_DossunIseki'),
)
def sha(b):return hashlib.sha256(b).hexdigest()

def table(b,o):
    count=struct.unpack_from('>I',b,o)[0]&0xffffff
    return [b[o+x:b.index(0,o+x)].decode() for x in struct.unpack_from('>'+str(count)+'I',b,o+4)]

def merge_objects(base,source,ids):
    """Keep existing definitions unchanged; add only required, absent object IDs."""
    old=byml_dump.parse(base);other=byml_dump.parse(source)
    existing={x['ObjId']:x for x in old};lookup={x['ObjId']:x for x in other}
    added=sorted(set(ids)-existing.keys())
    if not added:return base,[]
    kt,st=struct.unpack_from('>II',base,4);keys=table(base,kt);strings=table(base,st)
    src_keys=table(source,struct.unpack_from('>I',source,4)[0]);src_strings=table(source,struct.unpack_from('>I',source,8)[0])
    root=struct.unpack_from('>I',source,16)[0];n=struct.unpack_from('>I',source,root)[0]&0xffffff
    vals=root+4+((n+3)&~3)
    nodes={other[i]['ObjId']:struct.unpack_from('>I',source,vals+4*i)[0] for i in range(n)}
    out=bytearray(base)
    def reserve(size):
        out.extend(bytes(-len(out)%4));o=len(out);out.extend(bytes(size));return o
    def clone(t,v,field=None):
        if t==0xa0:
            text=src_strings[v]
            if text not in strings:strings.append(text)
            return strings.index(text)
        if t==0xc0:
            count=struct.unpack_from('>I',source,v)[0]&0xffffff
            # Wave archive's collision arrays include newer-game categories.
            # The v81 object table defines the supported array lengths.
            if field in ('Item','ItemObj','Kart','KartObj'):count=len(old[0][field])
            original_count=struct.unpack_from('>I',source,v)[0]&0xffffff
            if count>original_count:raise ValueError('Collision array too short')
            pos=reserve(4+((count+3)&~3)+4*count);struct.pack_into('>I',out,pos,0xc0000000|count)
            src_vals=v+4+((original_count+3)&~3);dst_vals=pos+4+((count+3)&~3)
            for i in range(count):
                typ=source[v+4+i];out[pos+4+i]=typ
                value=clone(typ,struct.unpack_from('>I',source,src_vals+4*i)[0])
                struct.pack_into('>I',out,dst_vals+4*i,value)
            return pos
        if t==0xc1:
            count=struct.unpack_from('>I',source,v)[0]&0xffffff;pos=reserve(4+8*count)
            struct.pack_into('>I',out,pos,0xc1000000|count)
            entries=[]
            for i in range(count):
                word,value=struct.unpack_from('>II',source,v+4+8*i);key=src_keys[word>>8];typ=word&255
                if key not in keys:raise ValueError('New object key unsupported: '+key)
                entries.append((keys.index(key),typ,clone(typ,value,key)))
            for i,(key,typ,value) in enumerate(sorted(entries)):struct.pack_into('>II',out,pos+4+8*i,key<<8|typ,value)
            return pos
        if t not in (0xd0,0xd1,0xd2,0xd3,0xff):raise ValueError('Unsupported object value type '+hex(t))
        return v
    offsets={}
    old_root=struct.unpack_from('>I',base,16)[0];count=len(old);old_vals=old_root+4+((count+3)&~3)
    for i,obj in enumerate(old):offsets[obj['ObjId']]=struct.unpack_from('>I',base,old_vals+4*i)[0]
    for id in added:offsets[id]=clone(0xc1,nodes[id])
    # Existing value-string indices remain stable, including all old nodes.
    text=[s.encode()+b'\0' for s in strings];size=4+4*(len(text)+1)+sum(map(len,text));pos=reserve(size)
    struct.pack_into('>I',out,pos,0xc2000000|len(text));cursor=4+4*(len(text)+1)
    for i,s in enumerate(text):struct.pack_into('>I',out,pos+4+4*i,cursor);out[pos+cursor:pos+cursor+len(s)]=s;cursor+=len(s)
    struct.pack_into('>I',out,pos+4+4*len(text),cursor);struct.pack_into('>I',out,8,pos)
    count=len(offsets);root=reserve(4+((count+3)&~3)+4*count);struct.pack_into('>I',out,root,0xc0000000|count)
    for i,id in enumerate(sorted(offsets)):
        out[root+4+i]=0xc1;struct.pack_into('>I',out,root+4+((count+3)&~3)+4*i,offsets[id])
    struct.pack_into('>I',out,16,root)
    parsed=byml_dump.parse(bytes(out));result={x['ObjId']:x for x in parsed}
    if any(result[id]!=obj for id,obj in existing.items()):raise ValueError('Existing object changed')
    for id in added:
        expected=dict(lookup[id])
        for field in ('Item','ItemObj','Kart','KartObj'):expected[field]=expected[field][:len(old[0][field])]
        if result[id]!=expected:raise ValueError('New object roundtrip mismatch')
    # An append-only root points backwards to old children. Our parser accepts
    # that, but MK8's reader rejects it (VRMenu lookup crashed at 022C3998).
    # Rebuild with native-compatible table/node ordering, then compare values.
    rebuilt=byml_dump.build(parsed)
    if byml_dump.parse(rebuilt)!=parsed:raise ValueError('Canonical object table roundtrip mismatch')
    return rebuilt,added

def prefetch(stream):
    """FSTM -> one-block FSTP with the first five interleaved ADPCM blocks."""
    if stream[:8]!=b'FSTM\xfe\xff\x00\x40':raise ValueError('Expected big-endian Wii U stream')
    refs={struct.unpack_from('>H',stream,20+12*i)[0]:struct.unpack_from('>II',stream,24+12*i) for i in range(struct.unpack_from('>H',stream,16)[0])}
    info_at,info_size=refs[0x4000];data_at,data_size=refs[0x4002]
    info=bytearray(stream[info_at:info_at+info_size]);meta=8+struct.unpack_from('>I',info,12)[0]
    codec,_,channels=struct.unpack_from('>BBB',info,meta)
    if codec!=2 or not 1<=channels<=16:raise ValueError('Expected DSP ADPCM music')
    blocks,block_size=struct.unpack_from('>II',info,meta+16)
    if blocks<5:raise ValueError('Music too short for prefetch')
    sample_at=data_at+8+struct.unpack_from('>I',info,meta+52)[0]
    payload=stream[sample_at:sample_at+5*channels*block_size]
    if len(payload)!=5*channels*block_size:raise ValueError('Truncated music')
    pdat_at=64+info_size;sample_out=pdat_at+44
    struct.pack_into('>I',info,meta+52,sample_out)
    pdat=struct.pack('>11I',0x50444154,44+len(payload),1,0,0,0,16,len(payload),0,0,0)+payload
    header=bytearray(64);struct.pack_into('>4sHHIIHH',header,0,b'FSTP',0xfeff,64,0x10000,sample_out+len(payload),2,0)
    struct.pack_into('>HHII',header,20,0x4000,0,64,info_size);struct.pack_into('>HHII',header,32,0x4004,0,pdat_at,len(pdat))
    return bytes(header)+info+pdat

def build(archive,baseline,game,output):
    archive,baseline,game,output=map(Path,(archive,baseline,game,output))
    if output.exists():raise ValueError('Use a new output directory')
    original_cups=(baseline/'data.cup0').read_bytes();cups=cup0.parse(original_cups)
    golden=next(c for c in cups if c.name=='Golden Dash Cup')
    if golden.type!=1 or any(t.dir!='Ginvalid' for t in golden.tracks):raise ValueError('Unexpected Golden Dash baseline')
    target=output/'sd/cafeloader/vol'/TITLE/'content';inventory={};needed_ids=set()
    def write(rel,b):
        p=target/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
        if p.read_bytes()!=b:raise ValueError('Write verification failed: '+rel)
        inventory[rel]={'sha256':sha(b),'size':len(b)}
    with ZipFile(archive) as z:
        files=z.namelist();prefix='Booster Course Pass Wave 1/'
        for slot,(source,directory,name,tag,donor) in enumerate(TRACKS):
            src=prefix+('aoc/content/0015/' if source.startswith('D') else 'content/')+'course/'+source+'/'
            names=[n for n in files if n.startswith(src) and not n.endswith('/')]
            if not all(src+n in files for n in cup0.REQUIRED):raise ValueError('Missing course assets: '+name)
            for n in names:write('course/'+directory+'/'+n[len(src):],z.read(n))
            muunt=z.read(src+'course_muunt.byaml');needed_ids.update(byml_dump.parse(muunt)['MapObjIdList'])
            # 200cc must not fall back to an unrelated underlying course list.
            write('course/'+directory+'/course_muunt_200.byaml',muunt)
            bank=(game/'course'/donor/('SNDG_'+donor+'.bars')).read_bytes()
            entries,_,version=szs.sarc_info(bank);rewritten=[]
            native_stems=set()
            for n,b,h,a in entries:
                if n.endswith(('_N.bfstp','_F.bfstp')) and n.startswith('pBGM_'):native_stems.add(n[:-8])
            if len(native_stems)!=1:raise ValueError('Unexpected native music bank: '+donor)
            stem=native_stems.pop();unique=('pBGM_CT_'+sha(directory.encode())[:len(stem)-8].upper())
            if len(unique)!=len(stem):raise ValueError('Music path length mismatch')
            music_stem={'Gu_WaterPark':'pBGM_WU_WATER_PARK','G3ds_MusicPark':'pBGM_3DS_MUSIC_PARK','G64_PeachCircuit':'pBGM_N64_PEACH_CIRCUIT','Dwii_WariosMine':'pBGM_WII_WARIOSMINE'}[source]
            streams={suffix:z.read(prefix+'content/audio/stream/'+music_stem+suffix+'.bfstm') for suffix in ('_N','_F')}
            for suffix,b in streams.items():write('audio/stream/'+unique+suffix+'.bfstm',b)
            for n,b,h,a in entries:
                if n==stem+'_N.bfstp':b=prefetch(streams['_N'])
                elif n==stem+'_F.bfstp':b=prefetch(streams['_F'])
                elif n=='_param.bin':
                    for suffix in ('_N','_F'):
                        old=(stem+suffix+'.bfstm').encode();new=(unique+suffix+'.bfstm').encode()
                        if old not in b:raise ValueError('Music stream reference missing')
                        b=b.replace(old,new)
                rewritten.append((n,b))
            write('course/'+directory+'/SNDG_'+directory+'.bars',szs.sarc_write(rewritten,szs.sarc_aligns(bank,0x20),version))
            pic='custom/cPict_'+directory+'.bflim'
            preview=next(n for n in files if 'Inject in to menu.szs/' in n and n.endswith('ym_CoursePict_'+source+'_00^o.bflim'))
            write(pic,z.read(preview));golden.tracks[slot]=cup0.Track(directory,pic,name,tag)
        merged,added=merge_objects((baseline/'data/objflow.byaml').read_bytes(),z.read(prefix+'content/data/objflow.byaml'),needed_ids)
        write('data/objflow.byaml',merged)
        # Only the new objects' models/support files; preserve unrelated global arrows.
        for n in files:
            if not n.startswith(prefix+'content/mapobj/') or n.endswith('/'):continue
            rel=n[len(prefix+'content/'):];obj=rel.split('/')[1]
            if obj not in ('GlideBoard','GlideStand','KakiwariPackunFlower','KakiwariPackunFlower_FX','VRCnsw11','VRCnsw12','VRCnsw13','VRCnsw14'):continue
            b=z.read(n)
            if (baseline/rel).exists() and (baseline/rel).read_bytes()!=b:raise ValueError('Shared asset conflict: '+rel)
            write(rel,b)
    # Page 4 is the engine's existing playable custom replacement page.
    # Position zero aliases the four Mushroom Cup base tracks, matching banks above.
    cup0.make_playable(cups,golden,golden.tracks[0]);payload=cup0.build(cups)
    if golden.type!=4 or golden.icon!=0:raise ValueError('Golden Dash slot donor mapping changed')
    for old,new in zip(cup0.parse(original_cups),cups):
        if old.name!='Golden Dash Cup' and old!=new:raise ValueError('Unrelated cup changed')
    write('data.cup0',payload);write('custom/cup0',payload)
    manifest={'kind':'Golden Dash content overlay','requires':'validated Aroma v0.20 and existing CTGP content','console_tested':False,'archive_sha256':sha(archive.read_bytes()),'baseline_cup0_sha256':sha(original_cups),'baseline_objflow_sha256':sha((baseline/'data/objflow.byaml').read_bytes()),'new_object_ids':added,'golden_cup':vars(golden)|{'tracks':[vars(t) for t in golden.tracks]},'files':inventory}
    (output/'Verification.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (output/'LIRE_MOI.txt').write_text('GOLDEN DASH CUP - correctif de contenu Aroma v0.20, MK8 EUR v81\n\nCopie le CONTENU du dossier sd a la racine de ta SD. Fusionne cafeloader et remplace les fichiers demandes, apres sauvegarde. Garde ton plugin Aroma v0.20 actuel. Redemarre le jeu.\n\nLa Golden Dash Cup devient une coupe jouable sur la page de remplacements personnalises (type 4). Utilise L/R pour parcourir les pages. Paris Promenade, Toad Circuit, Choco Mountain et Coconut Mall sont relies a leurs nouveaux dossiers. Les autres coupes sont conservees.\n\nCet ajout necessite ton pack CTGP deja installe. Il ne contient ni nouveau plugin, ni RPX, ni menu Speedometer ON/OFF, ni drift rose. Les objets existants sont conserves ; seuls six objets requis sont ajoutes. Musiques et prechargements sont prepares depuis les flux du ZIP.\n\nFichiers verifies automatiquement ; les quatre courses restent a tester sur Wii U, en 150cc puis 200cc.\n\nRetour arriere : restaure tes copies precedentes de data.cup0, custom/cup0 et data/objflow.byaml. Les nouveaux dossiers peuvent rester sans etre references.\n',encoding='utf-8')
    print('Built',output,'with',len(inventory),'files; new object IDs',added)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('archive','baseline','game','output'):p.add_argument('--'+n,required=True)
    a=p.parse_args();build(a.archive,a.baseline,a.game,a.output)
