"""Stage the supplied 48-track replacement pack as independent Booster cups.

Golden Dash and every non-Booster cup are preserved. Nothing is installed by
this builder; source UI, character replacements and global audio are ignored.
"""
from pathlib import Path
import argparse,json,struct,shutil,hashlib,re
import cup0,szs,character_assets,character_voice,byml_dump,golden_dash,console_music,bolt_pack,booster_audio
from booster_mapping import model_sources

# Canonical names. Legacy donor names below are not physical course identities;
# booster_mapping resolves those using the explicit production-order table.
TRACKS=[
('Gu_FirstCircuit','Paris Promenade','Tour'),('Gu_WaterPark','Toad Circuit','3DS'),('Gu_Cake','Choco Mountain','N64'),('Gu_DossunIseki','Coconut Mall','Wii'),
('Gu_MarioCircuit','Tokyo Blur','Tour'),('Gu_City','Shroom Ridge','DS'),('Gu_HorrorHouse','Sky Garden','GBA'),('Gu_Expert','Ninja Hideaway',''),
('Gu_Airport','New York Minute','Tour'),('Gwii_GrumbleVolcano','Mario Circuit 3','SNES'),('Gu_Techno','Kalimari Desert','N64'),('G64_PeachCircuit','Waluigi Pinball','DS'),
('Gu_Cloud','Sydney Sprint','Tour'),('Gu_Desert','Snow Land','GBA'),('Gu_BowserCastle','Mushroom Gorge','Wii'),('Gu_RainbowRoad','Sky-High Sundae',''),
('Dgc_YoshiCircuit','London Loop','Tour'),('Du_ExciteBike','Boo Lake','GBA'),('Du_DragonRoad','Rock Rock Mountain','3DS'),('Dagb_RibbonRoad','Maple Treeway','Wii'),
('Dgc_BabyPark','Berlin Byways','Tour'),('Gsfc_DonutsPlain3','Peach Gardens','DS'),('Gu_SnowMountain','Merry Mountain',''),('G64_KinopioHighway','Rainbow Road','3DS'),
('Gwii_MooMooMeadows','Amsterdam Drift','Tour'),('G3ds_DKJungle','Riverside Park','GBA'),('Ggc_SherbetLand','DK Summit','Wii'),('Dagb_CheeseLand',"Yoshi's Island",''),
('Ggc_DryDryDesert','Bangkok Rush','Tour'),('D3ds_NeoBowserCity','Mario Circuit','DS'),('Du_MuteCity','Waluigi Stadium','GCN'),('Du_Metro','Singapore Speedway','Tour'),
('Gds_WarioStadium','Athens Dash','Tour'),('Gds_PukupukuBeach','Daisy Cruiser','GCN'),('G3ds_MusicPark','Moonview Highway','Wii'),('G64_YoshiValley','Squeaky Clean Sprint',''),
('Gds_TickTockClock','Los Angeles Laps','Tour'),('G3ds_PackunSlider','Sunset Wilds','GBA'),('Gu_Ocean','Koopa Cape','Wii'),('G64_RainbowRoad','Vancouver Velocity','Tour'),
('Dwii_WariosMine','Rome Avanti','Tour'),('Dsfc_RainbowRoad','DK Mountain','GCN'),('Du_IcePark','Daisy Circuit','Wii'),('Du_Woods','Piranha Plant Cove',''),
('Du_Hyrule','Madrid Drive','Tour'),('Du_Animal_Summer',"Rosalina's Ice World",'3DS'),('Gagb_MarioCircuit','Bowser Castle 3','SNES'),('Du_BigBlue','Rainbow Road','Wii')]
# Existing UI icon order differs from chronological wave order.
ICON_FIRST={0:1,1:5,2:9,3:13,8:17,10:21,4:25,5:29,6:33,7:37,9:41,11:45}
MUSIC={
'Gu_MarioCircuit':'WU_CIRCUIT','Gu_Cloud':'WU_CLOUD','Gu_Desert':'WU_DESERT','Gu_RainbowRoad':'WU_RAINBOW_ROAD',
'G64_KinopioHighway':'N64_KINOPIO_HIGHWAY','Gsfc_DonutsPlain3':'SFC_DONUTS_PLAIN3','Dgc_BabyPark':'GC_BABYPARK',
'G3ds_MusicPark':'3DS_MUSIC_PARK','Gds_PukupukuBeach':'WU_OCEAN','Gds_TickTockClock':'DS_TICK_TOCK_CLOCK','Gu_Ocean':'WU_OCEAN','G64_RainbowRoad':'N64_RAINBOW_ROAD'}
EXISTING_MUSIC={'Gwii_GrumbleVolcano':'Gu_Bolt21'}

def sha(b):return hashlib.sha256(b).hexdigest()

def build(root,content,base,encoder):
    root,content,base,encoder=map(Path,(root,content,base,encoder));source=root/'source/DLC 8DX Tracks'
    target=root/'staged/content';target.mkdir(parents=True,exist_ok=True)
    audit=json.loads((root/'course_audit.json').read_text());lookup={x['key']:x for x in audit}
    source_ids=model_sources(json.loads((root/'model_audit.json').read_text()))
    previews=json.loads((root/'preview_names.json').read_text());menu=character_assets.hashed_entries((source/'content/ui/cmn/menu.szs').read_bytes())
    original=(content/'data.cup0').read_bytes();cups=cup0.parse(original);manifest={'baseline_cup0':sha(original),'tracks':[],'files':{}}
    def write(rel,b):
        p=target/rel;p.parent.mkdir(parents=True,exist_ok=True)
        if not p.exists() or p.read_bytes()!=b:p.write_bytes(b)
        manifest['files'][rel]={'sha256':sha(b),'size':len(b)}
    dlc=content.parents[2]/'0005000c/1010ed00.backup/content'
    templates={};required_labels=set()
    for icon,group in enumerate(bolt_pack.GROUPS):
        for slot,(donor,msg) in enumerate(group[2]):
            bank=bolt_pack.native_file(base,dlc,donor,'SNDG_'+donor+'.bars').read_bytes()
            stems=bolt_pack.bank_stems(bank)
            if len(stems)!=1:raise ValueError('Unexpected donor music '+donor)
            templates[icon,slot]=(donor,bank,stems[0])
            required_labels.update(stems[0]+suffix for suffix in ('_N','_F'))
    original_audio=content/'audio/turbo_sound.bfsar';extended=target/'audio/turbo_sound.bfsar'
    archive,cloned=booster_audio.extend(original_audio,extended,required_labels)
    manifest['added_stream_labels']=cloned;manifest['baseline_bfsar']=sha(original_audio.read_bytes())
    if cloned:write('audio/turbo_sound.bfsar',extended.read_bytes())
    needed=set()
    for number,(thumbnail_key,name,tag) in enumerate(TRACKS,1):
        if number<=4:continue
        key=source_ids[number]
        directory='Gu_Bcp%02d'%number;item=lookup[key];folder=Path(item['source']);rel='course/'+directory+'/'
        cup=next(c for c in cups if c.type==1 and ICON_FIRST.get(c.icon,0)<=number<ICON_FIRST.get(c.icon,0)+4)
        slot=number-ICON_FIRST[cup.icon];donor,template,native_stem=templates[cup.icon,slot]
        pre=next(b for n,b,h in szs.sarc_read(template) if n==native_stem+'_N.bfstp')
        channels=console_music.metadata(b'FSTM'+pre[4:])['channels']
        for filename in cup0.REQUIRED+cup0.OPTIONAL:
            if (folder/filename).is_file():write(rel+filename,(folder/filename).read_bytes())
        muunt=(folder/'course_muunt.byaml').read_bytes();needed.update(byml_dump.parse(muunt)['MapObjIdList'])
        muunt200=folder/'course_muunt_200.byaml'
        write(rel+'course_muunt_200.byaml',muunt200.read_bytes() if muunt200.exists() else muunt)
        streams=[s for s in item['streams'] if s.endswith('_N.bfstm')]
        stem=streams[0][:-8] if streams else 'pBGM_'+MUSIC[key]
        music={};reports={}
        for suffix in ('_N','_F'):
            src=source/'content/audio/stream'/(stem+suffix+'.bfstm')
            if not src.exists() and key in EXISTING_MUSIC:
                music_donor=EXISTING_MUSIC[key];raw=(content/'course'/music_donor/('SNDG_'+music_donor+'.bars')).read_bytes()
                names={m.decode() for n,b,h in szs.sarc_read(raw) if n=='_param.bin' for m in re.findall(rb'[A-Za-z0-9_]+[.]bfstm',b) if m.endswith((suffix+'.bfstm').encode())}
                if len(names)!=1:raise ValueError('Ambiguous existing music '+music_donor)
                filename=names.pop();src=content/'audio/stream'/filename
                if not src.exists():src=base/'audio/stream'/filename
            elif not src.exists():src=base/'audio/stream'/(stem+suffix+'.bfstm')
            if not src.exists():raise ValueError('Missing source music '+str(src))
            filename='pBGM_BCP%02d%s.bfstm'%(number,suffix);dest=target/'audio/stream'/filename;dest.parent.mkdir(parents=True,exist_ok=True)
            # Cache an independently decoded, non-silent, loop-preserving stream.
            cache=dest.with_suffix('.json');signature=sha(src.read_bytes())
            cached=json.loads(cache.read_text()) if cache.exists() else {}
            if not dest.exists() or cached.get('source_sha256')!=signature or cached.get('output',{}).get('channels')!=channels:
                report=console_music.normalize(src,dest,encoder,channels=channels);report['source_sha256']=signature;cache.write_text(json.dumps(report,indent=2)+'\n')
            reports[suffix]=json.loads(cache.read_text());music[suffix]=dest.read_bytes();write('audio/stream/'+filename,music[suffix])
        rewritten=[]
        for n,b,h in szs.sarc_read(template):
            if n.startswith('pBGM_') and n.endswith('.bfstp'):b=golden_dash.prefetch(music['_F' if n.endswith('_F.bfstp') else '_N'])
            if n=='_param.bin':
                for old in set(re.findall(rb'pBGM_[A-Za-z0-9_]+[.]bfstm',b)):
                    suffix='_F' if old.endswith(b'_F.bfstm') else '_N';new=('pBGM_BCP%02d%s.bfstm'%(number,suffix)).encode()
                    if len(new)>len(old):raise ValueError('Invalid stream rename')
                    b=b.replace(old,new+bytes(len(old)-len(new)))
            rewritten.append((n,b))
        bank=szs.sarc_write(rewritten,szs.sarc_aligns(template,32),struct.unpack_from('>H',template,16)[0]);bank,dropped=booster_audio.known_bar(bank,archive)
        write(rel+'SNDG_'+directory+'.bars',bank)
        preview_key='Du_Animal' if key.startswith('Du_Animal_') else key;pic='custom/cPict_'+directory+'.bflim'
        write(pic,menu[szs.sarc_hash('timg/'+previews[preview_key])])
        cup.tracks[slot]=cup0.Track(directory,pic,name,tag)
        manifest['tracks'].append({'number':number,'source':key,'directory':directory,'name':name,'tag':tag,'cup':cup.name,'slot':slot,'music':stem,'streams':reports,'native_donor':donor,'native_music_label':native_stem,'unavailable_ambient_labels':dropped})
        print(number,name,flush=True)
    objpath=content/'data/objflow.byaml';merged,added=golden_dash.merge_objects(objpath.read_bytes(),(source/'content/data/objflow.byaml').read_bytes(),needed)
    write('data/objflow.byaml',merged);manifest['baseline_objflow']=sha(objpath.read_bytes());manifest['new_object_ids']=added
    import booster_object_alias,maple_wigglers,animal_dependencies
    for p in (target/'course').glob('Gu_Bcp*/course_muunt*.byaml'):
        fixed,changed=animal_dependencies.fix(p.read_bytes())
        if changed:
            rel=p.relative_to(target).as_posix();write(rel,fixed)
            manifest.setdefault('animal_manager_dependencies',[]).append(rel)
    definitions,changed,alias=booster_object_alias.prepare(merged,
        (source/'content/data/objflow.byaml').read_bytes(),
        {p.relative_to(target).as_posix():p.read_bytes() for p in (target/'course').glob('Gu_Bcp*/course_muunt*.byaml')})
    if alias is not None:
        write('data/objflow.byaml',definitions)
        for rel,data in changed.items():write(rel,data)
    manifest['animated_bird_alias']=alias
    maple=next(t['directory'] for t in manifest['tracks'] if t['name']=='Maple Treeway')
    for filename in ('course_muunt.byaml','course_muunt_200.byaml'):
        rel='course/'+maple+'/'+filename
        fixed,report=maple_wigglers.fix((target/rel).read_bytes());write(rel,fixed)
        manifest.setdefault('wiggler_paths',{})[filename]=report
    assets=[];directories=[]
    for folder in sorted((source/'content/mapobj').iterdir()):
        if not folder.is_dir():continue
        directory=folder.relative_to(source/'content').as_posix()
        # Object loading enumerates directories before opening any files. The
        # private directory must therefore be complete, not a changed-file diff.
        assets.extend((directory,directory+'/'));directories.append(directory)
        entries={}
        for parent in (base/directory,content/directory,folder):
            if parent.is_dir():
                for p in parent.rglob('*'):
                    if p.is_file():entries[p.relative_to(parent).as_posix()]=p
        for filename,p in sorted(entries.items()):
            rel=directory+'/'+filename;private='custom/bcp/'+rel
            if len(private.encode())>=128:raise ValueError('Asset path too long')
            data=p.read_bytes()
            if p.suffix=='.bars':data,dropped=booster_audio.known_bar(data,archive)
            write(private,data);assets.append(rel)
    manifest['scoped_assets']=assets
    manifest['scoped_directories']=directories
    payload=cup0.build(cups);write('data.cup0',payload);write('custom/cup0',payload)
    for old,new in zip(cup0.parse(original),cups):
        if old.type!=1 or old.icon==0:
            if old!=new:raise ValueError('Existing cup changed: '+old.name)
    if len(cups)!=31 or len({t.dir for c in cups if c.type==1 for t in c.tracks})!=48:raise ValueError('Booster mapping incomplete')
    (root/'staged/manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('root','content','base','encoder'):p.add_argument('--'+name,required=True)
    a=p.parse_args();m=build(a.root,a.content,a.base,a.encoder);print('Staged',len(m['tracks']),'courses,',len(m['files']),'files')
