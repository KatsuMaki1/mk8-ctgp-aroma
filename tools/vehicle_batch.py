"""Prepare/install the expanded vehicle catalog on a tracked Cemu prototype."""
import argparse,copy,json
from pathlib import Path
import costume_patch as patch
import costumes,vehicle_catalog as catalog,vehicle_tables as tables,vehicle_messages as messages
from dk_costumes import hashed_member

def json_bytes(value):return (json.dumps(value,indent=2)+'\n').encode()

def prepare(base,content,extracted,icons,output):
    base,content,extracted,icons,output=map(Path,(base,content,extracted,icons,output))
    backup=content.parent/'code_backups/VehicleSlots';state=json.loads((backup/'state.json').read_text())
    files={};asset_path=content/'custom/vehicles/manifest.json';assets=json.loads(asset_path.read_text())
    for rel,meta in assets['resources'].items():
        if patch.digest((content/'custom/vehicles'/rel).read_bytes())!=meta['sha256']:raise ValueError('Existing model changed: '+rel)
    specs=[('RedOffroader','red offroader','kart/body/BodyK_Tnk.szs'),
           ('Wildfire','wildfire','kart/body/BodyK_Wld.szs')]
    specs += [('SNESTires','SNES Tires','kart/tire/Tire'+kind+'_Zst.szs') for kind in 'BKT']
    for key,folder,rel in specs:
        payload=(extracted/key/folder/'content'/rel).read_bytes();info=costumes.inspect_model(payload)
        original=next((p/rel for p in (base,content) if (p/rel).is_file()),None)
        if original is None:raise ValueError('Missing donor model: '+rel)
        donor=costumes.inspect_model(original.read_bytes())
        if info['models']!=donor['models']:raise ValueError('Internal model names differ: '+rel)
        missing=set(donor['skeletal_animations'])-set(info['skeletal_animations'])
        if missing:raise ValueError('Missing donor animations: '+repr(missing))
        target=key+'/'+rel;files['custom/vehicles/'+target]=payload
        assets['resources'][target]={'sha256':patch.digest(payload),'bytes':len(payload),
                                    'models':info['models'],'missing_original_animations':[]}
    assets['catalog']={'bodies':catalog.BODIES,'tires':catalog.TIRES}
    files['custom/vehicles/manifest.json']=json_bytes(assets)
    new_state=copy.deepcopy(state)
    donors={'body':[c['donor'] for c in catalog.BODIES],'tire':[c['donor'] for c in catalog.TIRES]}
    for name,axes in [('Parts',tables.PART_AXES),('Performance',tables.PERF_AXES)]:
        original=(backup/(name+'.bin.before-vehicles')).read_bytes()
        if patch.digest(original)!=state['parameters'][name]['source_sha256']:raise ValueError('Original table backup changed')
        result=tables.expand(original,axes,donors);files['common/mush/'+name+'.bin']=result
        new_state['parameters'][name]['output_sha256']=patch.digest(result)
    for rel,meta in state['messages'].items():
        old=(content/rel).read_bytes()
        if patch.digest(old)!=meta['output_sha256']:raise ValueError('Installed message changed')
        result=messages.append(old);files[rel]=result
        new_state['messages'][rel]['output_sha256']=patch.digest(result)
    icon_meta=json.loads((icons/'manifest.json').read_text());menu=(icons/'menu.szs').read_bytes()
    if patch.digest((content/'ui/cmn/menu.szs').read_bytes())!=icon_meta['input_sha256'] or patch.digest(menu)!=icon_meta['output_sha256']:raise ValueError('Icon archive baseline/candidate changed')
    if list(icon_meta['members'])!=[catalog.icon(c) for c in catalog.CHOICES]:raise ValueError('Wrong icon catalog')
    for rel,sha in icon_meta['members'].items():
        if patch.digest(hashed_member(menu,rel))!=sha:raise ValueError('Icon changed')
    files['ui/cmn/menu.szs']=menu
    new_state['icons']['output_sha256']=icon_meta['output_sha256'];new_state['icons']['members']=icon_meta['members']
    new_state['catalog']={'bodies':catalog.BODIES,'tires':catalog.TIRES}
    manifest={'rpx_before':state['rpx_after'],'files':{},'state_after':new_state}
    for rel,data in files.items():
        target=content/rel;before=patch.digest(target.read_bytes()) if target.exists() else None
        dest=output/'files'/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
        manifest['files'][rel]={'before':before,'after':patch.digest(data)}
    (output/'batch.json').write_bytes(json_bytes(manifest))
    print('Prepared',len(files),'files; three additional parts, five catalog choices; original tables and messages preserved')
    return manifest

def install(content,candidate,prepared):
    patch.ensure_cemu_closed()
    content,candidate,prepared=map(lambda p:Path(p).resolve(),(content,candidate,prepared))
    backup=content.parent/'code_backups/VehicleSlots';sp=backup/'state.json';old_state=sp.read_bytes();state=json.loads(old_state)
    meta=json.loads((prepared/'batch.json').read_text());manifest=json.loads(Path(str(candidate)+'.json').read_text())
    rpx=content.parent/'code/Turbo.rpx';before_rpx=rpx.read_bytes()
    cs=content.parent/'code_backups/MarioCostumeSelector/state.json';before_cs=cs.read_bytes()
    if state.get('status')=='restored' or patch.digest(before_rpx)!=state['rpx_after'] or state['rpx_after']!=meta['rpx_before']:raise ValueError('Installed vehicle baseline changed')
    if patch.digest(candidate.read_bytes())!=manifest['output_sha256']:raise ValueError('Candidate changed')
    expected=manifest.get('vehicle_slots',{})
    if expected.get('bodies')!=catalog.BODIES or expected.get('tires')!=catalog.TIRES:raise ValueError('Candidate catalog differs')
    if expected.get('icons')!=list(meta['state_after']['icons']['members']):raise ValueError('Icon requirements differ')
    writes={};saved={}
    for rel,hashes in meta['files'].items():
        target=(content/rel).resolve()
        if not target.is_relative_to(content):raise ValueError('Resource path outside content')
        old=target.read_bytes() if target.exists() else None;data=(prepared/'files'/rel).read_bytes()
        if (patch.digest(old) if old is not None else None)!=hashes['before'] or patch.digest(data)!=hashes['after']:raise ValueError('Baseline/candidate file changed: '+rel)
        writes[target]=data;saved[target]=old
    revision=backup/('catalog-'+manifest['output_sha256'][:16]);revision.mkdir(exist_ok=True)
    snapshots={revision/'Turbo.rpx':before_rpx,revision/'vehicle-state.json':old_state,revision/'selector-state.json':before_cs}
    snapshots.update({revision/'before'/p.relative_to(content):d for p,d in saved.items() if d is not None})
    for path,data in snapshots.items():
        if path.exists() and path.read_bytes()!=data:raise ValueError('Revision backup conflict')
    for path,data in snapshots.items():costumes.atomic_write(path,data)
    try:
        for path,data in writes.items():costumes.atomic_write(path,data)
        patch.install(candidate,content)
        result=meta['state_after'];result['rpx_after']=manifest['output_sha256'];result['status']='experimental-awaiting-five-part-test'
        costumes.atomic_write(sp,json_bytes(result))
    except Exception:
        for path,old in saved.items():
            if old is not None:costumes.atomic_write(path,old)
            elif path.exists() and path.read_bytes()==writes[path]:path.unlink()
        costumes.atomic_write(rpx,before_rpx);costumes.atomic_write(cs,before_cs);costumes.atomic_write(sp,old_state)
        raise
    print('Installed expanded catalog, models, icons, labels, tables and RPX; full rollback baseline retained')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['prepare','install']);p.add_argument('--content',required=True)
    p.add_argument('--base');p.add_argument('--extracted');p.add_argument('--icons');p.add_argument('--output');p.add_argument('--candidate');p.add_argument('--prepared');a=p.parse_args()
    if a.command=='prepare':
        if not all([a.base,a.extracted,a.icons,a.output]):p.error('prepare requires --base, --extracted, --icons, --output')
        prepare(a.base,a.content,a.extracted,a.icons,a.output)
    else:
        if not a.candidate or not a.prepared:p.error('install requires --candidate and --prepared')
        install(a.content,a.candidate,a.prepared)
