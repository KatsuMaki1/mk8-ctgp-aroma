"""Install only verified R2 content in Cemu, backing up every changed model."""
from pathlib import Path
import json,hashlib,shutil,datetime
import costume_patch,costumes
from optimization_r2 import ROOT,CONTENT
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run():
 costume_patch.ensure_cemu_closed();report=json.loads((ROOT/'report.json').read_text());assert len(report)==80
 rows=[x for x in report if x['status']=='optimized_verified'];backup=ROOT/'cemu_backup';assert not backup.exists()
 for x in rows:
  rel=Path('course')/x['directory']/'course_model.szs'
  assert sha(CONTENT/rel)==x['source_sha256'],'Installed source changed: '+str(rel)
  assert sha(ROOT/'content'/rel)==x['output_sha256']
 backup.mkdir()
 for x in rows:
  rel=Path('course')/x['directory']/'course_model.szs';dst=backup/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(CONTENT/rel,dst)
 state={'time':datetime.datetime.now().isoformat(),'status':'backed_up','target':str(CONTENT),'files':rows};(backup/'state.json').write_text(json.dumps(state,indent=2));costume_patch.ensure_cemu_closed()
 try:
  for x in rows:
   rel=Path('course')/x['directory']/'course_model.szs';costumes.atomic_write(CONTENT/rel,(ROOT/'content'/rel).read_bytes());assert sha(CONTENT/rel)==x['output_sha256']
 except BaseException:
  for x in rows:
   rel=Path('course')/x['directory']/'course_model.szs';costumes.atomic_write(CONTENT/rel,(backup/rel).read_bytes())
  state['status']='rolled_back';(backup/'state.json').write_text(json.dumps(state,indent=2));raise
 state['status']='installed_and_verified';(backup/'state.json').write_text(json.dumps(state,indent=2));print('Installed with verified backups:',len(rows),'models')
if __name__=='__main__':run()
