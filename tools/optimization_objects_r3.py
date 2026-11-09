"""Texture-only optimization of heavy private map objects and skyboxes."""
from pathlib import Path
import json,os,hashlib,shutil
import cup0,optimization_r2 as o
from optimization_r3 import WORK,MAIN,STAGE
ROOT=WORK/'optimization_objects_r3'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run():
 ROOT.mkdir(exist_ok=True);groups={}
 for p in (MAIN/'custom').rglob('*.bfres'):
  rel=p.relative_to(MAIN)
  if rel.parts[1] not in ('bcp','bolt_assets','course_assets'):continue
  source=STAGE/rel if (STAGE/rel).exists() else p
  if source.stat().st_size<4*1048576 and not source.stem.lower().startswith('vr'):continue
  digest=sha(source);g=groups.setdefault(digest,{'source':str(source),'sha256':digest,'paths':[]})
  g['paths'].append(rel.as_posix())
 manifest=[];root=ROOT/'source_content';root.mkdir(exist_ok=True)
 for index,g in enumerate(groups.values()):
  directory=f'Asset_{index:03}';g['directory']=directory;manifest.append(g)
  dest=root/'course'/directory/'course_model.szs';dest.parent.mkdir(parents=True,exist_ok=True)
  if dest.exists():assert sha(dest)==g['sha256']
  else:
   try:os.link(g['source'],dest)
   except OSError:shutil.copy2(g['source'],dest)
 (root/'data.cup0').write_bytes(b'private asset catalog')
 (ROOT/'source_manifest.json').write_text(json.dumps(manifest,indent=2))
 o.ROOT=ROOT;o.CONTENT=root;o.DLL=WORK/'optimization_r3/bin/model_optimizer.dll'
 o.ENV=dict(os.environ,CTGP_OPT_PROFILE='R3');os.environ['R2_STOP']='10000'
 # Reuse only the audited model/texture pipeline; actors, skeletons and all
 # vertex/index buffers remain unchanged (no simplification stage here).
 class Track:
  def __init__(self,g):self.dir=g['directory'];self.name=g['paths'][0]
 class Cup:
  tracks=[Track(g) for g in manifest]
 cup0.parse=lambda unused:[Cup()]
 print('Unique private models',len(manifest),'paths',sum(len(g['paths']) for g in manifest),flush=True)
 if not (ROOT/'audit.json').exists():o.audit()
 o.prepare();o.build();o.aggregate()
 rows=json.loads((ROOT/'report.json').read_text())
 summary={'audited_unique_models':len(rows),'optimized':sum(r['status']=='optimized_verified' for r in rows),
          'texture_bytes_saved_unique':sum(r.get('texture_bytes_saved',0) for r in rows),'geometry_changed':False,
          'unchanged':[r for r in rows if r['status']!='optimized_verified'],'runtime_validation':'pending'}
 (ROOT/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary),flush=True)
if __name__=='__main__':run()
