"""Resumable all-custom-course Wii U performance pass; no live content writes."""
from pathlib import Path
import os,sys,json,shutil,subprocess,hashlib
import cup0,optimization_r2 as o
WORK=Path('C:/Users/evant/Documents/Codex/2026-10-25/files-mentioned-by-the-user-handoff/work')
ROOT=WORK/'optimization_r3'
MAIN=Path('C:/Users/evant/AppData/Roaming/Cemu/mlc01/usr/title/0005000e/1010ed00/content')
STAGE=WORK/'booster_pass_20261031/r4/content'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def configure():
 o.ROOT=ROOT;o.CONTENT=ROOT/'source_content';o.DLL=ROOT/'bin/model_optimizer.dll'
 o.ENV=dict(os.environ,CTGP_OPT_PROFILE='R3');os.environ['R2_STOP']='10000'

def snapshot():
 configure();root=o.CONTENT;root.mkdir(parents=True,exist_ok=True)
 catalog=STAGE/'data.cup0';shutil.copy2(catalog,root/'data.cup0')
 tracks={t.dir:t.name for c in cup0.parse(catalog.read_bytes()) for t in c.tracks if t.dir!='Ginvalid'}
 reports=[]
 for folder in ['optimization_r2','bcp_vs_optimization_r4']:
  reports.append((WORK/folder,{r['directory']:r for r in json.loads((WORK/folder/'report.json').read_text())}))
 manifest=[]
 for directory,name in tracks.items():
  source=MAIN/'course'/directory/'course_model.szs';base_hash=digest(source)
  if (STAGE/'course'/directory/'course_model.szs').exists():source=STAGE/'course'/directory/'course_model.szs'
  for folder,report in reports:
   old=report.get(directory);candidate=folder/'content/course'/directory/'course_model.szs'
   if old and old['status']=='optimized_verified' and candidate.exists() and digest(source) in (old['source_sha256'],old['output_sha256']):
    assert digest(candidate)==old['output_sha256'];source=candidate
  dest=root/'course'/directory/'course_model.szs';dest.parent.mkdir(parents=True,exist_ok=True)
  if dest.exists():assert digest(dest)==digest(source),'Source snapshot changed; use a new work directory'
  else:
   try:os.link(source,dest)
   except OSError:shutil.copy2(source,dest)
  manifest.append({'directory':directory,'name':name,'input':str(source),'input_sha256':digest(source),'main_sha256':base_hash})
 (ROOT/'source_manifest.json').write_text(json.dumps(manifest,indent=2))
 print('Snapshotted',len(manifest),'custom courses; sources remain read-only.',flush=True)

def run():
 configure()
 if not (ROOT/'source_manifest.json').exists():snapshot()
 if not (ROOT/'audit.json').exists():o.audit()
 o.prepare()
 node=shutil.which('node') or 'C:/Users/evant/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe'
 module=Path(__file__).resolve().parents[1]/'work/optimization_r3_tool/meshopt_simplifier.module.mjs'
 if not (ROOT/'geometry_done.json').exists():
  subprocess.run([node,str(Path(__file__).parent/'model_optimizer/simplify.mjs'),module.as_uri(),str(ROOT)],env=o.ENV,check=True)
  (ROOT/'geometry_done.json').write_text(json.dumps({'module_sha256':digest(module),'ratio':0.4,'absolute_error':3,'locked_borders':True}))
 o.build();o.aggregate()
 rows=json.loads((ROOT/'report.json').read_text())
 summary={'audited':len(rows),'optimized':sum(r['status']=='optimized_verified' for r in rows),
          'triangles_removed':sum(r.get('triangles_removed',0) for r in rows),
          'texture_bytes_saved':sum(r.get('texture_bytes_saved',0) for r in rows),
          'unchanged':[r for r in rows if r['status']!='optimized_verified'],
          'wiiu_fps_measured':False,'runtime_validation':'pending'}
 (ROOT/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary),flush=True)
if __name__=='__main__':run()
