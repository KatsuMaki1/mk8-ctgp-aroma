"""Build an experimental additional-parts selector, preserving costume hooks."""
import argparse,json
from pathlib import Path
import costume_patch as patch
import vehicle_catalog as catalog

VEHICLE_HOOKS={
'vehicle_config':(0x0242b660,0x2c040000),
'vehicle_type':(0x0245d3e4,0x9421ffd8),
'vehicle_setup':(0x025a4980,0x9421ff68),
'vehicle_body':(0x025a514c,0x9421ffc0),
'vehicle_tire':(0x025a5c14,0x7c0802a6),
'vehicle_names':(0x02554b74,0x9421ffb0),
'vehicle_recipe':(0x0242bddc,0x9421fea8),
'vehicle_prefix':(0x0242bcd0,0x9421ff98),
'vehicle_icon':(0x02557754,0x7c0802a6),
'vehicle_audio_body':(0x02069024,0x281a0028),
'vehicle_race_body':(0x021941b4,0x81830020),
'vehicle_effects':(0x021ae8f8,0x7c0802a6),
'vehicle_body_name':(0x024527b0,0x7c0802a6),
'vehicle_unit_body':(0x021bc354,0x90de0054),
'vehicle_unit_tire':(0x021bc390,0x91430000),
}
GATEWAY = ['.balign 4','.global costume_vehicle_config','costume_vehicle_config:',
           'stwu 1,-64(1)','mflr 0','stw 0,68(1)',
           'stw 4,8(1)','stw 5,12(1)','stw 6,16(1)','stw 7,20(1)','stw 8,24(1)',
           'mfctr 0','stw 0,28(1)','mfcr 0','stw 0,32(1)','mfxer 0','stw 0,36(1)',
           'bl vehicle_config_impl',
           'lwz 4,8(1)','lwz 5,12(1)','lwz 6,16(1)','lwz 7,20(1)','lwz 8,24(1)',
           'lwz 0,28(1)','mtctr 0','lwz 0,32(1)','mtcrf 255,0','lwz 0,36(1)','mtxer 0',
           'lwz 0,68(1)','mtlr 0','addi 1,1,64','blr']
def alias_assembly(reg,choices,label,index=False):
    out=[]
    for i,c in enumerate(choices):
        extra=c['id']+bool(index);donor=c['donor']+bool(index)
        out += [f'cmpwi {reg},{extra}',f'bne {label}_next_{i}',f'li {reg},{donor}',f'b {label}_done',f'{label}_next_{i}:']
    return out+[f'{label}_done:']

GATEWAY += ['.balign 4','.global costume_vehicle_audio_body','costume_vehicle_audio_body:',
            'stwu 1,-16(1)','stw 12,4(1)',
            'lis 12,vehicle_audio_seen@ha','stw 26,vehicle_audio_seen@l(12)']
GATEWAY += alias_assembly(26,catalog.BODIES,'vehicle_audio',True)
GATEWAY += ['lwz 12,4(1)','addi 1,1,16','cmplwi 26,40','b return_vehicle_audio_body']
GATEWAY += ['.balign 4','.global costume_vehicle_race_body','costume_vehicle_race_body:',
            'lwz 12,0x20(3)','lwz 3,0x54(12)',
            'stwu 1,-16(1)','stw 0,8(1)','mfcr 0','stw 0,12(1)']
GATEWAY += alias_assembly(3,catalog.BODIES,'vehicle_race_body')
GATEWAY += ['lwz 0,12(1)','mtcrf 255,0','lwz 0,8(1)','addi 1,1,16','blr']
for _name,_reg,_choices,_store in [
    ('vehicle_unit_body',6,catalog.BODIES,'stw 6,0x54(30)'),
    ('vehicle_unit_tire',10,catalog.TIRES,'stw 10,0(3)')]:
    GATEWAY += ['.balign 4',f'.global costume_{_name}',f'costume_{_name}:',
                'stwu 1,-16(1)',f'stw {_reg},4(1)','stw 0,8(1)','mfcr 0','stw 0,12(1)']
    GATEWAY += alias_assembly(_reg,_choices,_name)
    GATEWAY += [_store,'lwz 0,12(1)','mtcrf 255,0','lwz 0,8(1)',f'lwz {_reg},4(1)',
                'addi 1,1,16',f'b return_{_name}']
STRIDES={0x0242e890:(0x1d880015,0x1d880000+21+len(catalog.TIRES)),
         0x0242e8fc:(0x1d9e0027,0x1d9e0000+39+len(catalog.BODIES))}

def build(source,out):
    old_hooks,old_flags,old_static,old_assembly=patch.HOOKS,patch.EXTRA_CFLAGS,patch.STATIC_PATCHES,patch.EXTRA_ASSEMBLY
    try:
        patch.HOOKS={**old_hooks,**VEHICLE_HOOKS};patch.EXTRA_CFLAGS=['-DVEHICLE_SLOTS'];patch.STATIC_PATCHES=STRIDES;patch.EXTRA_ASSEMBLY=GATEWAY
        manifest=patch.build(source,out)
        manifest['vehicle_slots']={'body':39,'tire':21,'body_base':7,'tire_base':12,
                                   'requires':['common/mush/Parts.bin','common/mush/Performance.bin','custom/vehicles/manifest.json'],
                                   'icons':[catalog.icon(c) for c in catalog.CHOICES], 'bodies':catalog.BODIES,'tires':catalog.TIRES,
                                   'labels':'Numeric Common.msbt IDs 0x7000..0x7004'}
        Path(str(out)+'.json').write_text(json.dumps(manifest,indent=2)+'\n')
        return manifest
    finally:
        patch.HOOKS,patch.EXTRA_CFLAGS,patch.STATIC_PATCHES,patch.EXTRA_ASSEMBLY=old_hooks,old_flags,old_static,old_assembly


def install(candidate,parameters,content):
    import costumes
    import vehicle_tables
    patch.ensure_cemu_closed()
    content=Path(content).resolve();candidate=Path(candidate).resolve();parameters=Path(parameters).resolve()
    manifest=json.loads(Path(str(candidate)+'.json').read_text())
    if manifest.get('vehicle_slots',{}).get('body')!=39 or manifest['vehicle_slots'].get('tire')!=21:
        raise ValueError('Expected additional-vehicle-slot candidate')
    if patch.digest(candidate.read_bytes())!=manifest['output_sha256']: raise ValueError('Candidate checksum failed')
    assets=json.loads((content/'custom/vehicles/manifest.json').read_text())
    for name,info in assets['resources'].items():
        if patch.digest((content/'custom/vehicles'/name).read_bytes())!=info['sha256']: raise ValueError('Changed vehicle model: '+name)
    pm=json.loads((parameters/'manifest.json').read_text())
    target=content.parent/'code/Turbo.rpx';rpx_before=target.read_bytes()
    cs=content.parent/'code_backups/MarioCostumeSelector/state.json';cs_before=cs.read_bytes()
    backup=content.parent/'code_backups/VehicleSlots';backup.mkdir(parents=True,exist_ok=True)
    state_path=backup/'state.json'
    if state_path.exists():
        state=json.loads(state_path.read_text())
        if patch.digest(rpx_before)==state['rpx_after']:
            for name in ('Parts','Performance'):
                if patch.digest((content/'common/mush'/(name+'.bin')).read_bytes())!=state['parameters'][name]['output_sha256']:
                    raise ValueError('Installed parameter table changed')
            return target
        if state.get('status')!='restored' or patch.digest(rpx_before)!=state['rpx_before']:
            raise ValueError('Existing vehicle installation state differs; restore before replacing')
    writes={};saved={}
    messages=json.loads((parameters/'messages.json').read_text())
    message_writes={};message_saved={}
    for rel,meta in messages.items():
        path=content/rel;after=(parameters/'messages'/rel).read_bytes()
        if patch.digest(after)!=meta['output_sha256']:raise ValueError('Changed message candidate')
        if path.exists()!=meta['existed']:raise ValueError('Message baseline existence differs: '+rel)
        before=path.read_bytes() if path.exists() else None
        source=before if before is not None else Path(meta['source']).read_bytes()
        if patch.digest(source)!=meta['input_sha256']:raise ValueError('Message baseline checksum mismatch')
        message_writes[path]=after;message_saved[path]=before
    for name,axes in [('Parts',vehicle_tables.PART_AXES),('Performance',vehicle_tables.PERF_AXES)]:
        path=content/'common/mush'/(name+'.bin');before=path.read_bytes();after=(parameters/(name+'.bin')).read_bytes()
        if patch.digest(before)!=pm[name]['source_sha256'] or patch.digest(after)!=pm[name]['output_sha256']:
            raise ValueError('Parameter baseline/candidate checksum failed: '+name)
        donors={'body':[c['donor'] for c in manifest['vehicle_slots']['bodies']],
                'tire':[c['donor'] for c in manifest['vehicle_slots']['tires']]} if 'bodies' in manifest['vehicle_slots'] else None
        vehicle_tables.verify(before,after,axes,donors);writes[path]=after;saved[path]=before
    snapshots={backup/'Turbo.rpx.before-vehicles':rpx_before,backup/'selector-state.before.json':cs_before,
               **{backup/(p.name+'.before-vehicles'):d for p,d in saved.items()}}
    snapshots.update({backup/'messages'/p.relative_to(content):d for p,d in message_saved.items() if d is not None})
    writes.update(message_writes);saved.update(message_saved)
    for path,data in snapshots.items():
        if path.exists() and path.read_bytes()!=data: raise ValueError('Different vehicle backup already exists')
    for path,data in snapshots.items(): costumes.atomic_write(path,data)
    try:
        for path,data in writes.items(): costumes.atomic_write(path,data)
        patch.install(candidate,content)
        state={'rpx_before':patch.digest(rpx_before),'rpx_after':manifest['output_sha256'],
               'target':str(target),'parameters':pm,'messages':messages,'status':'experimental-awaiting-gameplay-test'}
        costumes.atomic_write(state_path,(json.dumps(state,indent=2)+'\n').encode())
    except Exception:
        for path,data in saved.items():
            if data is not None:costumes.atomic_write(path,data)
            elif path.exists() and path.read_bytes()==writes[path]:path.unlink()
        if patch.digest(target.read_bytes()) in (manifest['output_sha256'],patch.digest(rpx_before)):
            costumes.atomic_write(target,rpx_before);costumes.atomic_write(cs,cs_before)
        raise
    print('Installed RPX and verified parameter tables; previous selector and tables backed up')
    return target

def restore(content):
    import costumes
    patch.ensure_cemu_closed();content=Path(content).resolve();backup=content.parent/'code_backups/VehicleSlots'
    state=json.loads((backup/'state.json').read_text());target=content.parent/'code/Turbo.rpx'
    if str(target)!=state['target'] or patch.digest(target.read_bytes())!=state['rpx_after']: raise ValueError('RPX changed outside vehicle prototype')
    previous=(backup/'Turbo.rpx.before-vehicles').read_bytes()
    if patch.digest(previous)!=state['rpx_before']: raise ValueError('Previous RPX checksum failed')
    writes={target:previous,content.parent/'code_backups/MarioCostumeSelector/state.json':(backup/'selector-state.before.json').read_bytes()}
    if state.get('icons'):
        menu=content/'ui/cmn/menu.szs';old=(backup/'menu.szs.before-icons').read_bytes();meta=state['icons']
        if patch.digest(menu.read_bytes())!=meta['output_sha256'] or patch.digest(old)!=meta['input_sha256']:
            raise ValueError('Vehicle menu archive/backup changed')
        writes[menu]=old
    for name,meta in state['parameters'].items():
        path=content/'common/mush'/(name+'.bin');old=(backup/(name+'.bin.before-vehicles')).read_bytes()
        if patch.digest(path.read_bytes())!=meta['output_sha256'] or patch.digest(old)!=meta['source_sha256']: raise ValueError('Table checksum mismatch')
        writes[path]=old
    remove=[]
    for rel,meta in state.get('messages',{}).items():
        path=content/rel
        if patch.digest(path.read_bytes())!=meta['output_sha256']:raise ValueError('Installed message changed: '+rel)
        if meta['existed']:
            old=(backup/'messages'/rel).read_bytes()
            if patch.digest(old)!=meta['input_sha256']:raise ValueError('Message backup checksum failed')
            writes[path]=old
        else:remove.append(path)
    for path,data in writes.items(): costumes.atomic_write(path,data)
    for path in remove:path.unlink()
    state['status']='restored';costumes.atomic_write(backup/'state.json',(json.dumps(state,indent=2)+'\n').encode())
    print('Restored previous costume selector and original parameter tables')

def upgrade(candidate,content):
    """Update only the tracked executable; keep tables, messages and icons."""
    import costumes
    patch.ensure_cemu_closed();content=Path(content).resolve();candidate=Path(candidate).resolve()
    backup=content.parent/'code_backups/VehicleSlots';sp=backup/'state.json'
    old_state=sp.read_bytes();state=json.loads(old_state)
    target=content.parent/'code/Turbo.rpx';before=target.read_bytes()
    cs=content.parent/'code_backups/MarioCostumeSelector/state.json';old_cs=cs.read_bytes()
    manifest=json.loads(Path(str(candidate)+'.json').read_text())
    if state.get('status')=='restored' or patch.digest(before)!=state['rpx_after']:raise ValueError('Vehicle baseline changed')
    if patch.digest(candidate.read_bytes())!=manifest['output_sha256']:raise ValueError('Candidate changed')
    if (manifest.get('vehicle_slots',{}).get('body'),manifest.get('vehicle_slots',{}).get('tire'))!=(39,21):raise ValueError('Incompatible slot IDs')
    for name,meta in state['parameters'].items():
        if patch.digest((content/'common/mush'/(name+'.bin')).read_bytes())!=meta['output_sha256']:raise ValueError('Vehicle parameters changed')
    for rel,meta in state.get('messages',{}).items():
        if patch.digest((content/rel).read_bytes())!=meta['output_sha256']:raise ValueError('Vehicle messages changed')
    if state.get('icons'):
        if patch.digest((content/'ui/cmn/menu.szs').read_bytes())!=state['icons']['output_sha256']:raise ValueError('Vehicle menu changed')
        if manifest['vehicle_slots'].get('icons')!=list(state['icons']['members']):raise ValueError('Required icons differ')
    elif isinstance(manifest['vehicle_slots'].get('icons'),list):raise ValueError('Install required icons first')
    revision=backup/('revision-'+state['rpx_after'][:16]);revision.mkdir(exist_ok=True)
    for name,data in [('Turbo.rpx',before),('vehicle-state.json',old_state),('selector-state.json',old_cs)]:
        path=revision/name
        if path.exists() and path.read_bytes()!=data:raise ValueError('Revision backup conflict')
        costumes.atomic_write(path,data)
    try:
        patch.install(candidate,content)
        state['rpx_after']=manifest['output_sha256'];state['status']='experimental-awaiting-gameplay-test'
        costumes.atomic_write(sp,(json.dumps(state,indent=2)+'\n').encode())
    except Exception:
        costumes.atomic_write(target,before);costumes.atomic_write(cs,old_cs);costumes.atomic_write(sp,old_state)
        raise
    print('Upgraded tracked vehicle executable; tables, labels and icons retained')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=('build','install','restore','upgrade'),nargs='?',default='build')
    p.add_argument('--rpx');p.add_argument('--out');p.add_argument('--candidate')
    p.add_argument('--parameters');p.add_argument('--content');a=p.parse_args()
    if a.command=='build':
        if not a.rpx or not a.out:p.error('build requires --rpx and --out')
        m=build(a.rpx,a.out);print('Built additional vehicle slots:',m['code_bytes'],'native code bytes')
    elif a.command=='install':
        if not all((a.candidate,a.parameters,a.content)):p.error('install requires --candidate, --parameters, --content')
        install(a.candidate,a.parameters,a.content)
    elif a.command=='upgrade':
        if not a.candidate or not a.content:p.error('upgrade requires --candidate and --content')
        upgrade(a.candidate,a.content)
    else:
        if not a.content:p.error('restore requires --content')
        restore(a.content)
