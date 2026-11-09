"""Import the user's Boltthunder4 archive into additional CUP0 pages.

Never installs the archive's network patches, whole menus or Common.msbt.
Shared object overrides are staged privately and require the scoped runtime.
"""
from pathlib import Path
import argparse,json,zipfile,hashlib,re,struct,shutil
import cup0,szs,vehicle_messages,byml_dump,sndg

ROOT="Boltthunder4's CT PACK/"
GROUPS=[
 ('Mushroom',1301,[('Gu_FirstCircuit',1401),('Gu_WaterPark',1402),('Gu_Cake',1403),('Gu_DossunIseki',1404)]),
 ('Flower',1302,[('Gu_MarioCircuit',1406),('Gu_City',1405),('Gu_HorrorHouse',1408),('Gu_Expert',1411)]),
 ('Star',1303,[('Gu_Airport',1409),('Gu_Ocean',1410),('Gu_Techno',1407),('Gu_SnowMountain',1412)]),
 ('Special',1304,[('Gu_Cloud',1414),('Gu_Desert',1413),('Gu_BowserCastle',1415),('Gu_RainbowRoad',1416)]),
 ('Shell',1305,[('Gwii_MooMooMeadows',1441),('Gagb_MarioCircuit',1442),('Gds_PukupukuBeach',1443),('G64_KinopioHighway',1445)]),
 ('Banana',1306,[('Ggc_DryDryDesert',1447),('Gsfc_DonutsPlain3',1446),('G64_PeachCircuit',1451),('G3ds_DKJungle',1448)]),
 ('Leaf',1307,[('Gds_WarioStadium',1454),('Ggc_SherbetLand',1449),('G3ds_MusicPark',1452),('G64_YoshiValley',1453)]),
 ('Thunder',1308,[('Gds_TickTockClock',1450),('G3ds_PackunSlider',1444),('Gwii_GrumbleVolcano',1455),('G64_RainbowRoad',1456)]),
 ('DLC02',1309,[('Dgc_YoshiCircuit',1485),('Du_ExciteBike',1482),('Du_DragonRoad',1483),('Du_MuteCity',1484)]),
 ('DLC03',1310,[('Dwii_WariosMine',1481),('Dsfc_RainbowRoad',1486),('Du_IcePark',1487),('Du_Hyrule',1488)]),
 ('DLC04',1311,[('Dgc_BabyPark',1490),('Dagb_CheeseLand',1489),('Du_Animal_Summer',1492),('Du_Woods',1491)]),
 ('DLC05',1312,[('D3ds_NeoBowserCity',1493),('Dagb_RibbonRoad',1494),('Du_Metro',1495),('Du_BigBlue',1496)])]

def sha(data):return hashlib.sha256(data).hexdigest()
def messages(raw):
    pairs,texts=vehicle_messages.unpack(raw)
    return {k:texts[i].decode('utf-16-be',errors='replace').rstrip('\0') for k,i in pairs.items()}
def native_file(game,dlc,course,filename):
    candidates=[game/'course'/course/filename]
    if dlc:candidates+=list(dlc.glob('*/course/'+course+'/'+filename))
    for p in candidates:
        if p.is_file():return p
    raise ValueError('Missing native fallback '+course+'/'+filename)
def bank_stems(raw):
    return sorted({n[:-len('_N.bfstp')] for n,d,h in szs.sarc_read(raw) if n.startswith('pBGM_') and n.endswith('_N.bfstp')})

def plan(archive,baseline,game,dlc):
    archive,baseline,game,dlc=map(Path,(archive,baseline,game,dlc))
    with zipfile.ZipFile(archive) as z:
        names=set(z.namelist());texts=messages(z.read(ROOT+'content/ui/ue/Common.msbt'))
        menu={h:d for n,d,h in szs.sarc_read(szs.yaz0_decode(z.read(ROOT+'content/ui/cmn/menu.szs')))}
        folders={n.split('/')[-2]:n.rsplit('/',1)[0]+'/' for n in names if n.endswith('/course_model.szs')}
        old=cup0.parse((baseline/'data.cup0').read_bytes())
        # The native CTGP cup renderer supports all twelve positions per page.
        places=[(3,i,36+i) for i in range(12)]
        if any(c.type in (3,4) for c in old):raise ValueError('Destination custom pages already used')
        ids={c.cup_id for c in old}
        if ids & {x[2] for x in places}:raise ValueError('Cup animation frame collision')
        object_ids={x['ObjId'] for x in byml_dump.parse((baseline/'data/objflow.byaml').read_bytes())}
        result=[];needed=set()
        for g,(icon_name,msg,tracks) in enumerate(GROUPS):
            page,position,cid=places[g];group={'name':texts[msg],'page':page,'position':position,'cup_id':cid,'tracks':[]}
            icon=ROOT+'content/ui/cmn/a_race/timg/ym_CupIcon'+icon_name+'_130x130^h.bflim'
            if icon not in names:raise ValueError('Missing original cup icon '+icon)
            group['icon_member']=icon
            for s,(source,id) in enumerate(tracks):
                prefix=folders[source]
                preview_source='Du_Animal' if source.startswith('Du_Animal_') else source
                guesses=['timg/ym_CoursePict_'+n+'_00^o.bflim' for n in (source,preview_source)]
                preview=next((n for n in guesses if szs.sarc_hash(n) in menu),None)
                if not preview:raise ValueError('Missing preview for '+source)
                muunt=byml_dump.parse(z.read(prefix+'course_muunt.byaml') if prefix+'course_muunt.byaml' in names
                    else native_file(game,dlc,source,'course_muunt.byaml').read_bytes())
                required=set(muunt.get('MapObjIdList',[]));needed.update(required)
                donor=GROUPS[position][2][s][0]
                # DLC cups are new custom page entries over the first four
                # native cups, so their native music labels must be adjusted.
                donor_bank=native_file(game,dlc,donor,'SNDG_'+donor+'.bars')
                source_bank=prefix+'SNDG_'+source+'.bars'
                bank=z.read(source_bank) if source_bank in names else native_file(game,dlc,source,'SNDG_'+source+'.bars').read_bytes()
                stems=bank_stems(bank)
                if not stems:raise ValueError('No primary music pair in '+source)
                target_stems=bank_stems(donor_bank.read_bytes())
                if not target_stems:raise ValueError('No donor music pair '+donor)
                track={'source':source,'source_prefix':prefix,'name':texts[id],'name_message':id,
                    'directory':'Gu_Bolt%02d'%(g*4+s),'preview_member':preview,
                    'donor':donor,'source_stems':stems,'donor_stems':target_stems,
                    'source_bank':source_bank if source_bank in names else None,'object_ids':sorted(required)}
                group['tracks'].append(track)
            result.append(group)
        missing=needed-object_ids
        if missing:raise ValueError('Object definitions absent from current pack: '+str(sorted(missing)))
        # These four directories share the same CT geometry and objects. Only
        # the native Animal Crossing sound-bank labels differ by season.
        duplicates=[]
        summer=folders['Du_Animal_Summer']
        summer_files={n[len(summer):].replace('Du_Animal_Summer','Du_Animal'):sha(z.read(n)) for n in names if n.startswith(summer) and not n.endswith('/')}
        for season in ('Autumn','Spring','Winter'):
            src='Du_Animal_'+season;prefix=folders[src]
            other={n[len(prefix):].replace(src,'Du_Animal'):sha(z.read(n)) for n in names if n.startswith(prefix) and not n.endswith('/')}
            visual=lambda d:{k:v for k,v in d.items() if not k.startswith('SNDG_')}
            if visual(other)!=visual(summer_files):raise ValueError('Season variant has distinct course assets: '+src)
            duplicates.append(src)
        return {'archive_sha256':sha(archive.read_bytes()),'baseline_cup0_sha256':sha((baseline/'data.cup0').read_bytes()),
                'groups':result,'same_course_seasonal_bank_variants':duplicates,'unique_tracks':48,'new_cups':12}

def stage(archive,baseline,game,dlc,out):
    archive,baseline,game,dlc,out=map(Path,(archive,baseline,game,dlc,out))
    spec=plan(archive,baseline,game,dlc)
    out.mkdir(parents=True,exist_ok=False);content=out/'content';content.mkdir()
    (out/'plan.json').write_text(json.dumps(spec,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    with zipfile.ZipFile(archive) as z:
        names=z.namelist();menu={h:d for n,d,h in szs.sarc_read(szs.yaz0_decode(z.read(ROOT+'content/ui/cmn/menu.szs')))}
        for group in spec['groups']:
            icon=out/'icons'/('cup_%d.bflim'%group['cup_id']);icon.parent.mkdir(exist_ok=True);icon.write_bytes(z.read(group['icon_member']))
            for track in group['tracks']:
                src=track['source_prefix'];directory=track['directory'];dst=content/'course'/directory;dst.mkdir(parents=True)
                for n in names:
                    if not n.startswith(src) or n.endswith('/'):continue
                    f=n[len(src):]
                    if '/' in f or ' - Copy' in f:continue
                    if f=='SNDG_'+track['source']+'.bars':f='SNDG_'+directory+'.bars'
                    (dst/f).write_bytes(z.read(n))
                for f in cup0.REQUIRED:
                    if not (dst/f).exists():
                        original=native_file(game,dlc,track['source'],f)
                        shutil.copy2(original,dst/f)
                        track.setdefault('native_inherited_files',[]).append(f)
                bank=dst/('SNDG_'+directory+'.bars')
                if not bank.exists():shutil.copy2(native_file(game,dlc,track['source'],'SNDG_'+track['source']+'.bars'),bank)
                if not (dst/'course_muunt_200.byaml').exists():shutil.copy2(dst/'course_muunt.byaml',dst/'course_muunt_200.byaml')
                pic=content/'custom'/('cPict_'+directory+'.bflim');pic.parent.mkdir(exist_ok=True);pic.write_bytes(menu[szs.sarc_hash(track['preview_member'])])
                print('Staged',directory,track['name'],flush=True)
        for n in names:
            if '/mapobj/' in n and not n.endswith('/'):
                rel='mapobj/'+n.split('/mapobj/',1)[1];dst=content/'custom/bolt_assets'/rel;dst.parent.mkdir(parents=True,exist_ok=True)
                b=z.read(n)
                if dst.exists() and dst.read_bytes()!=b:raise ValueError('Two conflicting source object assets: '+rel)
                dst.write_bytes(b)
        for n in names:
            if n.startswith(ROOT+'content/audio/stream/') and not n.endswith('/'):
                dst=out/'source_audio'/Path(n).name;dst.parent.mkdir(exist_ok=True);dst.write_bytes(z.read(n))
        for src in spec['same_course_seasonal_bank_variants']:
            n=next(n for n in names if n.endswith('/'+src+'/SNDG_'+src+'.bars'))
            dst=out/'source_seasonal_banks'/Path(n).name;dst.parent.mkdir(exist_ok=True);dst.write_bytes(z.read(n))
        credits=out/'credits';credits.mkdir()
        for n in ('README.txt','CREDITS.txt','Install Instructions.txt'):(credits/n).write_bytes(z.read(n))
    (out/'plan.json').write_text(json.dumps(spec,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    return spec

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['plan','stage'])
    for n in ('archive','baseline','game','dlc','out'):p.add_argument('--'+n,required=True)
    a=p.parse_args()
    if a.command=='plan':
        j=plan(a.archive,a.baseline,a.game,a.dlc);Path(a.out).write_text(json.dumps(j,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    else:stage(a.archive,a.baseline,a.game,a.dlc,a.out)
