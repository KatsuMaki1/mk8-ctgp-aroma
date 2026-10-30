"""Prepare and install vehicle icons on a tracked additional-slot prototype."""
import argparse, json, struct, subprocess, tempfile
from pathlib import Path
from PIL import Image
import bflim, costumes, costume_patch as patch
from dk_costumes import hashed_member, merge_hashed, unpack
import szs

from vehicle_catalog import CHOICES
NAMES=tuple(c['key'] for c in CHOICES)

def prepare(content, images, output):
    content,images,output=map(Path,(content,images,output))
    source=content/'ui/cmn/menu.szs';before=source.read_bytes()
    # Native part panes are 200x128. Use the established RGBA8 menu format,
    # expanding its surface rather than stretching a square character image.
    footer=bytearray(hashed_member(before,'timg/tc_Chara_DK^l.bflim')[-40:])
    struct.pack_into('>I',footer,12,131072+40)
    struct.pack_into('>HHH',footer,28,200,128,8192)
    struct.pack_into('>I',footer,36,131072)
    template=bytes(131072)+footer
    compressed_template=hashed_member(before,'timg/tc_KP_K_Wld^q.bflim')
    icons={}
    output.mkdir(parents=True,exist_ok=True)
    for name in NAMES:
        image=Image.open(images/(name+'.png')).convert('RGBA')
        if image.size!=(200,128):raise ValueError('Expected 200x128 transparent part render')
        member='timg/ct_KP_'+name+'^q.bflim'
        try:data=hashed_member(before,member)
        except ValueError:data=bflim.encode_bc3(image,compressed_template)
        icons[member]=data
        (output/(name+'.bflim')).write_bytes(data)
    merged=merge_hashed(before,icons)
    compressor=Path(r'C:\Program Files\Wiimm\SZS\wszst.exe')
    with tempfile.TemporaryDirectory(prefix='mk8-vehicle-icons-') as tmp:
        src,dst=Path(tmp)/'menu.sarc',Path(tmp)/'menu.szs'
        src.write_bytes(unpack(merged))
        subprocess.run([str(compressor),'compress',str(src),'--yaz0','--dest',str(dst)],check=True,capture_output=True)
        after=dst.read_bytes()
    if unpack(after)!=unpack(merged):raise ValueError('Compressed archive roundtrip failed')
    for name,data in icons.items():
        if hashed_member(after,name)!=data:raise ValueError('Icon member verification failed')
    (output/'menu.szs').write_bytes(after)
    meta={'input_sha256':patch.digest(before),'output_sha256':patch.digest(after),
          'members':{n:patch.digest(d) for n,d in icons.items()},'dimensions':[200,128]}
    (output/'manifest.json').write_text(json.dumps(meta,indent=2)+'\n')
    print('Prepared',len(icons),'icons; all existing menu members preserved:',len(before),'->',len(after),'bytes')
    return meta

def install(content,candidate,prepared):
    patch.ensure_cemu_closed()
    content,candidate,prepared=map(lambda p:Path(p).resolve(),(content,candidate,prepared))
    backup=content.parent/'code_backups/VehicleSlots'
    state_path=backup/'state.json';old_state=state_path.read_bytes();state=json.loads(old_state)
    if state.get('status')=='restored':raise ValueError('Install vehicle slots first')
    if state.get('icons'):raise ValueError('Vehicle icons already installed; restore before replacing')
    rpx=content.parent/'code/Turbo.rpx';before_rpx=rpx.read_bytes()
    menu=content/'ui/cmn/menu.szs';before_menu=menu.read_bytes();after_menu=(prepared/'menu.szs').read_bytes()
    meta=json.loads((prepared/'manifest.json').read_text())
    manifest=json.loads(Path(str(candidate)+'.json').read_text())
    if patch.digest(before_rpx)!=state['rpx_after']:raise ValueError('Tracked vehicle RPX changed')
    if patch.digest(candidate.read_bytes())!=manifest['output_sha256']:raise ValueError('Candidate RPX changed')
    if manifest.get('vehicle_slots',{}).get('icons')!=list(meta['members']):raise ValueError('Candidate icon names differ')
    if (patch.digest(before_menu),patch.digest(after_menu))!=(meta['input_sha256'],meta['output_sha256']):raise ValueError('Menu baseline/candidate changed')
    for name,sha in meta['members'].items():
        if patch.digest(hashed_member(after_menu,name))!=sha:raise ValueError('Icon payload changed')
    for name,pm in state['parameters'].items():
        if patch.digest((content/'common/mush'/(name+'.bin')).read_bytes())!=pm['output_sha256']:raise ValueError('Vehicle table changed')
    cs=content.parent/'code_backups/MarioCostumeSelector/state.json';before_cs=cs.read_bytes()
    snapshots={'menu.szs.before-icons':before_menu,'Turbo.rpx.before-icons':before_rpx,
               'vehicle-state.before-icons.json':old_state,'selector-state.before-icons.json':before_cs}
    for name,data in snapshots.items():
        path=backup/name
        if path.exists() and path.read_bytes()!=data:raise ValueError('Conflicting icon backup: '+name)
    for name,data in snapshots.items():costumes.atomic_write(backup/name,data)
    try:
        costumes.atomic_write(menu,after_menu)
        patch.install(candidate,content)
        state['rpx_after']=manifest['output_sha256'];state['icons']=meta
        costumes.atomic_write(state_path,(json.dumps(state,indent=2)+'\n').encode())
    except Exception:
        costumes.atomic_write(menu,before_menu);costumes.atomic_write(rpx,before_rpx)
        costumes.atomic_write(cs,before_cs);costumes.atomic_write(state_path,old_state)
        raise
    print('Installed both custom vehicle icons and selector; full vehicle rollback includes menu archive')

def upgrade(content,prepared):
    """Replace only tracked custom icons; retain every native/DK menu member."""
    patch.ensure_cemu_closed();content,prepared=Path(content).resolve(),Path(prepared).resolve()
    backup=content.parent/'code_backups/VehicleSlots';sp=backup/'state.json';old_state=sp.read_bytes();state=json.loads(old_state)
    menu=content/'ui/cmn/menu.szs';before=menu.read_bytes();after=(prepared/'menu.szs').read_bytes()
    meta=json.loads((prepared/'manifest.json').read_text())
    if patch.digest(before)!=state['icons']['output_sha256'] or patch.digest(after)!=meta['output_sha256']:raise ValueError('Menu baseline/candidate changed')
    allowed={szs.sarc_hash(n) for n in meta['members']}
    old={h:d for n,d,h,start in szs.sarc_info(unpack(before))[0]}
    new={h:d for n,d,h,start in szs.sarc_info(unpack(after))[0]}
    if set(old)-set(new) or any(new[h]!=d for h,d in old.items() if h not in allowed):raise ValueError('Unrelated menu resource changed')
    for name,sha in state['icons']['members'].items():
        if patch.digest(old.get(szs.sarc_hash(name),b''))!=sha:raise ValueError('Owned icon changed outside installation')
    for name,sha in meta['members'].items():
        if patch.digest(new.get(szs.sarc_hash(name),b''))!=sha:raise ValueError('Candidate icon changed')
    revision=backup/('menu-revision-'+patch.digest(before)[:16]);revision.mkdir(exist_ok=True)
    for name,data in [('menu.szs',before),('vehicle-state.json',old_state)]:
        p=revision/name
        if p.exists() and p.read_bytes()!=data:raise ValueError('Menu revision backup conflict')
        costumes.atomic_write(p,data)
    try:
        costumes.atomic_write(menu,after)
        state['icons']['output_sha256']=meta['output_sha256'];state['icons']['members']=meta['members']
        costumes.atomic_write(sp,(json.dumps(state,indent=2)+'\n').encode())
    except Exception:
        costumes.atomic_write(menu,before);costumes.atomic_write(sp,old_state);raise
    print('Upgraded tracked icons; all native/DK menu payloads and full rollback retained')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['prepare','install','upgrade'])
    p.add_argument('--content',required=True);p.add_argument('--images');p.add_argument('--output');p.add_argument('--candidate');p.add_argument('--prepared');a=p.parse_args()
    if a.command=='prepare':
        if not a.images or not a.output:p.error('prepare requires --images and --output')
        prepare(a.content,a.images,a.output)
    elif a.command=='upgrade':
        if not a.prepared:p.error('upgrade requires --prepared')
        upgrade(a.content,a.prepared)
    else:
        if not a.candidate or not a.prepared:p.error('install requires --candidate and --prepared')
        install(a.content,a.candidate,a.prepared)
