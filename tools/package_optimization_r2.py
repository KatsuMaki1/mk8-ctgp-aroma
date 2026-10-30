"""Package verified R2 models as updates and a full SD-only console ZIP."""
from pathlib import Path
import json,hashlib,zipfile,sys
from optimization_r2 import ROOT,CONTENT
OUT=ROOT.parent.parent/'outputs';BASE=OUT/'WiiU/CTGP_Aroma_COMPLET_2026-10-28.zip'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
 return h.hexdigest()
def run():
 report=json.loads((ROOT/'report.json').read_text());assert len(report)==80
 changed={x['directory']:x for x in report if x['status']=='optimized_verified'}
 files={('course/'+d+'/course_model.szs'):ROOT/'content/course'/d/'course_model.szs' for d in changed}
 for rel,p in files.items():
  d=p.parent.name;assert sha(p)==changed[d]['output_sha256'];assert sha(CONTENT/rel)==changed[d]['source_sha256'],'Current Cemu source changed'
 manifest={'profile':'R2','baseline':'full 2026-10-28 with R1','audited':len(report),'optimized':len(changed),'unchanged':[x for x in report if x['status']!='optimized_verified'],'triangles_removed':sum(x.get('triangles_removed',0) for x in changed.values()),'texture_bytes_saved_across_courses':sum(x.get('texture_bytes_saved',0) for x in changed.values()),'wiiu_fps_measured':False,'runtime_test':'pending','files':{rel:{'before_sha256':changed[p.parent.name]['source_sha256'],'after_sha256':sha(p),'bytes':p.stat().st_size} for rel,p in files.items()}}
 docs=OUT/'Documentation';docs.mkdir(exist_ok=True);(docs/'Optimization_R2-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');(docs/'Optimization_R2-report.json').write_text(json.dumps(report,indent=2)+'\n')
 print('Verified payload',len(files),'courses; triangles removed',manifest['triangles_removed'],'texture bytes saved',manifest['texture_bytes_saved_across_courses'],flush=True)
 for name,prefix in [('WiiU/Mises_a_jour/WiiU_CTGP_Optimization_R2.zip','sd/cafeloader/vol/000500001010ED00/content/'),('Cemu/Cemu_CTGP_Optimization_R2.zip','mlc01/usr/title/0005000e/1010ed00/content/')]:
  dest=OUT/name;dest.parent.mkdir(parents=True,exist_ok=True);assert not dest.exists()
  with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED,compresslevel=1,allowZip64=True) as z:
   for rel,p in sorted(files.items()):z.write(p,prefix+rel)
   z.comment=b'CTGP optimization R2 test build. Reduced scenery/texture detail; collisions, paths and objects retained. Wii U FPS not yet measured. Keep the previous pack as rollback.'
  with zipfile.ZipFile(dest) as z:assert z.testzip() is None
  print('ZIP verified',dest,dest.stat().st_size,flush=True)
 dest=OUT/'WiiU/CTGP_Aroma_COMPLET_SD_R2_2026-10-30.zip';assert not dest.exists()
 prefix='sd/cafeloader/vol/000500001010ED00/content/'
 with zipfile.ZipFile(BASE) as src,zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED,compresslevel=1,allowZip64=True) as z:
  original=json.loads(src.read('Verification-complete.json'))['files'];entries=[i for i in src.infolist() if i.filename.startswith('sd/')]
  for i,entry in enumerate(entries,1):
   rel=entry.filename.removeprefix(prefix) if entry.filename.startswith(prefix) else None
   if rel in files:z.write(files[rel],entry.filename)
   else:
    h=hashlib.sha256()
    with src.open(entry) as reader,z.open(entry.filename,'w',force_zip64=True) as writer:
     for b in iter(lambda:reader.read(4*1024*1024),b''):writer.write(b);h.update(b)
    assert h.hexdigest()==original[entry.filename[3:]]['sha256']
   if i%300==0:print('Full SD archive',i,'/',len(entries),flush=True)
  credits=[n for n in src.namelist() if n.startswith('credits/') and not n.endswith('/')]
  comment=b'CTGP R2 - 2026-10-30. Full SD pack. Optimization is a test build; Wii U FPS not yet measured. Reduced scenery detail. Online disconnect remains unresolved.\n\n'+b'\n\n'.join(n.encode()+b'\n'+src.read(n) for n in credits)
  assert len(comment)<=65535;z.comment=comment
 with zipfile.ZipFile(dest) as z:
  assert z.testzip() is None and all(n.startswith('sd/') for n in z.namelist());assert len(z.namelist())==len(entries)
 result={'archive':str(dest),'bytes':dest.stat().st_size,'sha256':sha(dest),'crc':'passed','sd_files':len(entries),'optimized_courses':len(changed)}
 (docs/'Optimization_R2-full-zip.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2),flush=True)
if __name__=='__main__':run()
