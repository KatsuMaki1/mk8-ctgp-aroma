"""Declare the shared native Animal Crossing spectator manager in Wii U ports."""
import byml_dump
import byml_edit

def fix(data):
    d=byml_dump.parse(data);ids=set(d.get('MapObjIdList',[]))
    if not ids.intersection((1137,1138,1139)) or 1140 in ids:return data,False
    # Wii U manager1140 allocates the shared transform pool for A/B/C/D,
    # counting all four managers. It is needed even with zero visible D actors.
    d['MapObjIdList']=sorted(ids|{1140},reverse=True)
    # Zero D actors need the manager's shared pool, not a D model resource.
    # Keep the original string/path tables in their original positions.
    result=byml_edit.root_arrays(data,{'MapObjIdList':d['MapObjIdList']})
    if byml_dump.parse(result)!=d:raise ValueError('Animal dependency roundtrip failed')
    return result,True
