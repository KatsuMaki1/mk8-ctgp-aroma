"""Give the Booster animated bird its own definition, preserving legacy Bird."""
import copy
import byml_dump

def prepare(objflow,source_objflow,courses):
    rows=byml_dump.parse(objflow);source=byml_dump.parse(source_objflow)
    old=next(r for r in rows if r['ObjId']==1170)
    desired=next(r for r in source if r['ObjId']==1170)
    if old['ResName']==desired['ResName']:return objflow,{},None
    used={r['ObjId'] for r in rows+source}
    alias=next(n for n in range(9020,10000) if n not in used)
    new=copy.deepcopy(old);new['ObjId']=alias;new['ResName']=desired['ResName'][:]
    rows.append(new);rows.sort(key=lambda r:r['ObjId'])
    updates={}
    for name,data in courses.items():
        d=byml_dump.parse(data);changed=0
        for obj in d.get('Obj',[]):
            if obj.get('ObjId')==1170:obj['ObjId']=alias;changed+=1
        if not changed:continue
        d['MapObjIdList']=[alias if n==1170 else n for n in d['MapObjIdList']]
        output=byml_dump.build(d)
        if byml_dump.parse(output)!=d:raise ValueError('Object alias BYAML roundtrip failed')
        updates[name]=output
    out=byml_dump.build(rows)
    if next(r for r in byml_dump.parse(out) if r['ObjId']==1170)!=old:raise ValueError('Legacy bird changed')
    return out,updates,alias
