"""Transactional install/restore for the independent R.O.B. Cemu prototype."""
from pathlib import Path
import argparse,json
import character_assets as assets,character_tables,costumes,costume_patch as patch

def plan(content,candidate,staged,menu):
    content,candidate,staged,menu=map(Path,(content,candidate,staged,menu))
    meta=json.loads(Path(str(candidate)+'.json').read_text())
    old_rpx=content.parent/'code/Turbo.rpx'
    if assets.digest(old_rpx.read_bytes())!=meta['source_sha256']:raise ValueError('Installed RPX differs from build baseline')
    if assets.digest(candidate.read_bytes())!=meta['output_sha256']:raise ValueError('Candidate RPX changed')
    ui=json.loads((menu/'menu.json').read_text())
    if assets.digest((content/'ui/cmn/menu.szs').read_bytes())!=ui['source_sha256']:raise ValueError('Installed menu changed')
    payload=(menu/'menu.szs').read_bytes()
    if assets.digest(payload)!=ui['output_sha256']:raise ValueError('Candidate menu changed')
    manifest=json.loads((staged/'manifest.json').read_text());writes={old_rpx:candidate.read_bytes(),content/'ui/cmn/menu.szs':payload}
    for rel,m in manifest['files'].items():
        data=(staged/'files'/rel).read_bytes()
        if assets.digest(data)!=m['sha256']:raise ValueError('Staged asset changed: '+rel)
        path=content/rel
        if rel in manifest['parameters']:
            old=path.read_bytes()
            if assets.digest(old)!=manifest['parameters'][rel]['source_sha256']:raise ValueError('Installed parameters changed')
            character_tables.verify(old,data)
        elif path.exists() and path.read_bytes()!=data:raise ValueError('Private resource conflict: '+rel)
        writes[path]=data
    return writes,meta

def install(content,candidate,staged,menu):
    patch.ensure_cemu_closed()
    content=Path(content).resolve();writes,meta=plan(content,candidate,staged,menu)
    root=content.parent/'code_backups/IndependentROB';state_path=root/'state.json'
    if state_path.exists():raise ValueError('Existing character installation state; restore it first')
    root.mkdir(parents=True,exist_ok=True);records=[]
    for n,(path,data) in enumerate(writes.items()):
        before=path.read_bytes() if path.exists() else None
        saved=root/'files'/('%04d.bin'%n)
        if before is not None:
            saved.parent.mkdir(parents=True,exist_ok=True);saved.write_bytes(before)
            if saved.read_bytes()!=before:raise ValueError('Backup readback failed')
        records.append({'target':str(path),'backup':str(saved) if before is not None else None,
                        'before':assets.digest(before) if before is not None else None,'after':assets.digest(data)})
    state={'status':'installing','prototype':meta,'files':records}
    costumes.atomic_write(state_path,(json.dumps(state,indent=2)+'\n').encode())
    applied=[]
    try:
        for (path,data),record in zip(writes.items(),records):
            costumes.atomic_write(path,data);applied.append(record)
            if assets.digest(path.read_bytes())!=record['after']:raise ValueError('Install readback failed')
    except Exception:
        for record in reversed(applied):
            path=Path(record['target'])
            if record['backup']:costumes.atomic_write(path,Path(record['backup']).read_bytes())
            elif path.is_file():path.unlink()
        state['status']='rolled-back-install-failure'
        costumes.atomic_write(state_path,(json.dumps(state,indent=2)+'\n').encode());raise
    state['status']='installed-awaiting-cemu-test'
    costumes.atomic_write(state_path,(json.dumps(state,indent=2)+'\n').encode())
    return state

def restore(content):
    patch.ensure_cemu_closed();content=Path(content).resolve()
    state_path=content.parent/'code_backups/IndependentROB/state.json';state=json.loads(state_path.read_text())
    if state['status']=='restored':return state
    for record in state['files']:
        path=Path(record['target']).resolve()
        if not path.is_relative_to(content.parent):raise ValueError('Restore target outside update directory')
        if not path.is_file() or assets.digest(path.read_bytes())!=record['after']:raise ValueError('Installed file changed outside prototype')
        if record['backup'] and assets.digest(Path(record['backup']).read_bytes())!=record['before']:raise ValueError('Backup changed')
    for record in reversed(state['files']):
        path=Path(record['target'])
        if record['backup']:costumes.atomic_write(path,Path(record['backup']).read_bytes())
        else:path.unlink()
    state['status']='restored';costumes.atomic_write(state_path,(json.dumps(state,indent=2)+'\n').encode())
    return state

def revise(content,updates,label,prototype=None,new_files=None):
    """Update a known installed test while preserving its original rollback."""
    patch.ensure_cemu_closed();content=Path(content).resolve()
    root=content.parent/'code_backups/IndependentROB';state_path=root/'state.json'
    old_state=state_path.read_bytes();state=json.loads(old_state);records={Path(r['target']):r for r in state['files']}
    updates={Path(p).resolve():d for p,d in updates.items()}
    new_files={Path(p).resolve():h for p,h in (new_files or {}).items()}
    for p in set(updates)-set(records):
        if not p.is_relative_to(content) or p not in new_files:raise ValueError('Revision contains an untracked path')
        before=p.read_bytes() if p.exists() else None
        expected=assets.digest(before) if before is not None else None
        if expected!=new_files[p]:raise ValueError('New dependency baseline changed')
        saved=root/'files'/('addition-%04d.bin'%len(state['files']))
        if before is not None:
            if saved.exists() and saved.read_bytes()!=before:raise ValueError('Dependency backup conflict')
            saved.parent.mkdir(parents=True,exist_ok=True);saved.write_bytes(before)
        record={'target':str(p),'backup':str(saved) if before is not None else None,'before':expected,'after':expected}
        records[p]=record;state['files'].append(record)
    for p in updates:
        current=assets.digest(p.read_bytes()) if p.exists() else None
        if current!=records[p]['after']:raise ValueError('Installed prototype changed')
    if prototype is not None:
        rpx=content.parent/'code/Turbo.rpx'
        if rpx not in updates or assets.digest(updates[rpx])!=prototype['output_sha256']:
            raise ValueError('Revision RPX does not match its manifest')
    revision=root/'revisions'/label
    revision.mkdir(parents=True,exist_ok=False);(revision/'state.json').write_bytes(old_state)
    previous={p:p.read_bytes() if p.exists() else None for p in updates}
    for n,(p,data) in enumerate(previous.items()):
        if data is not None:(revision/('%04d.bin'%n)).write_bytes(data)
    applied=[]
    try:
        for p,data in updates.items():
            costumes.atomic_write(p,data);applied.append(p)
            if assets.digest(p.read_bytes())!=assets.digest(data):raise ValueError('Revision readback differs')
            records[p]['after']=assets.digest(data)
        state.setdefault('revisions',[]).append(label)
        if prototype is not None:state['prototype']=prototype
        costumes.atomic_write(state_path,(json.dumps(state,indent=2)+'\n').encode())
    except Exception:
        for p in reversed(applied):
            if previous[p] is None:p.unlink()
            else:costumes.atomic_write(p,previous[p])
        costumes.atomic_write(state_path,old_state);raise
    return state

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['check','install','restore']);p.add_argument('--content',required=True,type=Path)
    for n in ('candidate','staged','menu'):p.add_argument('--'+n,type=Path)
    a=p.parse_args()
    if a.action=='restore':result=restore(a.content)
    elif a.action=='install':result=install(a.content,a.candidate,a.staged,a.menu)
    else:
        writes,meta=plan(a.content,a.candidate,a.staged,a.menu)
        result={'files':len(writes),'candidate':meta['output_sha256'],'status':'verified-not-installed'}
    print(json.dumps(result,indent=2))
