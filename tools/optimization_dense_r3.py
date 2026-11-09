"""Decor-only LOD0 reduction preserving every draw/culling descriptor."""
from pathlib import Path
import json,sys,subprocess,struct,shutil,hashlib,time
from optimization_r3 import ROOT,WORK
import szs
DENSE=WORK/'optimization_dense_r3';DLL=DENSE/'bin/model_optimizer.dll'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def call(args):
 p=subprocess.run([str(a) for a in args],capture_output=True,text=True)
 if p.returncode:raise RuntimeError((p.stdout+p.stderr)[-1600:])
 return p.stdout
def prepare():
 rows=json.loads((ROOT/'audit.json').read_text())
 for i,row in enumerate(rows,1):
  d=row['directory'];source=ROOT/d/'model.bfres';folder=DENSE/d;folder.mkdir(exist_ok=True)
  if not source.exists() or (folder/'exported.json').exists():continue
  try:
   call(['dotnet',DLL,'dense_export',source,folder/'meshes'])
   (folder/'exported.json').write_text(json.dumps({'source_sha256':sha(source)}))
  except Exception as e:(folder/'export_error.json').write_text(json.dumps({'reason':str(e)}))
  print('Dense export',i,'/',len(rows),d,flush=True)
 node=shutil.which('node') or 'C:/Users/evant/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe'
 module=Path(__file__).resolve().parents[1]/'work/optimization_r3_tool/meshopt_simplifier.module.mjs'
 subprocess.run([node,str(Path(__file__).parent/'model_optimizer/simplify_dense.mjs'),module.as_uri(),str(DENSE)],check=True)

def finish(wait=False):
 rows=json.loads((ROOT/'audit.json').read_text());results=[]
 for i,audit in enumerate(rows,1):
  row=dict(audit)
  ready=ROOT/row['directory']/'result.json'
  failed=ROOT/row['directory']/'error.json'
  while row['status']=='audited' and not ready.exists() and not failed.exists():
   if not wait:raise RuntimeError('Main model pass is not finished')
   time.sleep(2)
  if ready.exists():row=json.loads(ready.read_text())
  elif failed.exists():row=json.loads(failed.read_text())
  d=row['directory'];folder=DENSE/d;original=ROOT/d/'model.bfres'
  result={'directory':d,'status':'unchanged','nondegenerate_triangles_removed':0}
  if (folder/'result.json').exists():results.append(json.loads((folder/'result.json').read_text()));continue
  if row['status']!='optimized_verified':results.append(result);continue
  source=ROOT/d/'optimized.bfres'
  try:
   # Also validate the earlier pass against all protected lower LODs, not
   # just LOD0, before admitting its output to this cumulative release.
   call(['dotnet',DLL,'verify',original,ROOT/d/'meshes',source])
  except Exception as e:
   result.update(status='preserve_input',reason=str(e));results.append(result)
   folder.mkdir(exist_ok=True);(folder/'result.json').write_text(json.dumps(result,indent=2));continue
  plans=list((folder/'meshes').glob('*.newidx')) if (folder/'meshes').exists() else []
  if not plans:results.append(result);continue
  try:
   before=source.read_bytes();after=bytearray(before);ranges=[]
   meta=json.loads((folder/'meshes/meshes.json').read_text())
   for m in meta:
    p=folder/'meshes'/(str(m['id'])+'.newidx')
    if not p.exists():continue
    size=2 if '16' in m['index_format'] else 4;order='<' if 'Little' in m['index_format'] else '>'
    old=(folder/'meshes'/(str(m['id'])+'.idx')).read_bytes();new=p.read_bytes();assert len(old)==len(new)==m['indices']*4
    def encode(data):
     ids=struct.unpack('<'+'I'*(len(data)//4),data)
     return struct.pack(order+('H' if size==2 else 'I')*len(ids),*(x-m['first'] for x in ids))
    offset=m['buffer_offset'];oldbytes=encode(old);payload=encode(new)
    assert before[offset:offset+len(oldbytes)]==oldbytes,'Index buffer changed since export'
    after[offset:offset+len(payload)]=payload;ranges.append((offset,offset+len(payload)))
   cursor=0
   for a,b in sorted(ranges):
    if a>cursor:assert before[cursor:a]==after[cursor:a]
    cursor=max(cursor,b)
   assert before[cursor:]==after[cursor:] and len(before)==len(after)
   candidate=folder/'optimized.bfres';candidate.write_bytes(after)
   tex=folder/'textures';tex.mkdir(exist_ok=True);(tex/'textures.json').write_text('[]')
   call(['dotnet',DLL,'verify',source,folder/'meshes',candidate])
   container=json.loads((ROOT/d/'archive.json').read_text());raw=(ROOT/d/'source.raw').read_bytes()
   if container['container']=='FRES':payload=bytes(after)
   else:
    offset=container['member_offset'];length=container['member_length'];assert length==len(after)
    payload=raw[:offset]+after+raw[offset+length:]
   stage=folder/'encoded.raw';stage.write_bytes(payload)
   out=DENSE/'content/course'/d/'course_model.szs';out.parent.mkdir(parents=True,exist_ok=True)
   wszst='C:/Program Files/Wiimm/SZS/wszst.exe'
   call([wszst,'compress',stage,'--dest',out,'--yaz0','--compr=1','--overwrite','--max-file-size=512m'])
   check=folder/'recheck.raw';call([wszst,'decompress',out,'--dest',check,'--overwrite','--max-file-size=512m']);assert check.read_bytes()==payload
   stats=json.loads((folder/'simplified.json').read_text())
   result.update(status='optimized_verified',nondegenerate_triangles_removed=sum(x['removed'] for x in stats),
    output_sha256=sha(out),index_metadata_unchanged=True,protected_lods_verified=True)
  except Exception as e:result.update(status='preserve_R3',reason=str(e))
  results.append(result);(folder/'result.json').write_text(json.dumps(result,indent=2));print('Dense verified',i,'/',len(rows),d,result['status'],result['nondegenerate_triangles_removed'],flush=True)
 summary={'courses_changed':sum(r['status']=='optimized_verified' for r in results),
  'nondegenerate_triangles_removed':sum(r['nondegenerate_triangles_removed'] for r in results),
  'preserved_inputs':[r for r in results if r['status']=='preserve_input'],'draw_counts_offsets_bounds_lods_preserved':True,'wiiu_fps_measured':False}
 (DENSE/'report.json').write_text(json.dumps(results,indent=2));(DENSE/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary),flush=True)
if __name__=='__main__':{'prepare':prepare,'finish':finish,'finish_wait':lambda:finish(True)}[sys.argv[1]]()
