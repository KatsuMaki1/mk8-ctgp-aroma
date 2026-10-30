"""Build the current complete Cemu mod overlay, with no user account/save data."""
from pathlib import Path
import json,zipfile,hashlib,sys
from aroma_bundle import DIRS
import cup0
OUT=Path('C:/Users/evant/Documents/Codex/2026-10-25/files-mentioned-by-the-user-handoff/outputs')
CONTENT=Path('C:/Users/evant/AppData/Roaming/Cemu/mlc01/usr/title/0005000e/1010ed00/content')
RPX=OUT/'Cemu/Turbo_Wiimote_Cups_EUR81.rpx'
DEST=OUT/'Cemu/CTGP_Cemu_COMPLET_R2_Wiimote_2026-10-30.zip'
PREFIX='mlc01/usr/title/0005000e/1010ed00/'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
 return h.hexdigest()
assert not DEST.exists(),'Do not overwrite an existing shared release'
meta=json.loads(Path(str(RPX)+'.json').read_text());assert sha(RPX)==meta['output_sha256'];assert sha(CONTENT.parent/'code/Turbo.rpx')==meta['output_sha256']
files={}
for d in DIRS:
 for p in (CONTENT/d).rglob('*'):
  if p.is_file() and p.suffix.lower() not in ('.bak','.json') and '.bak.' not in p.name:
   files['content/'+p.relative_to(CONTENT).as_posix()]=p
files['content/data.cup0']=CONTENT/'data.cup0';files['code/Turbo.rpx']=RPX
assert sha(CONTENT/'data.cup0')==sha(CONTENT/'custom/cup0')
cups=cup0.parse((CONTENT/'data.cup0').read_bytes());assert len(cups)==31
tracks={t.dir for c in cups for t in c.tracks if t.dir!='Ginvalid'};assert len(tracks)==80
for d in tracks:
 for required in cup0.REQUIRED:assert 'content/course/'+d+'/'+required in files
r2=json.loads((OUT/'Documentation/Optimization_R2-manifest.json').read_text())
for rel,m in r2['files'].items():assert sha(CONTENT/rel)==m['after_sha256']
manifest={'platform':'Cemu','date':'2026-10-30','region':'EUR','update_version':81,'cup0_records':31,'custom_course_directories':80,'optimized_courses':74,'wiimote_cup_controls':'Cemu user-confirmed; real console pending','online_disconnect':'unresolved','files':{}}
with zipfile.ZipFile(DEST,'w',zipfile.ZIP_DEFLATED,compresslevel=1,allowZip64=True) as z:
 for i,(rel,p) in enumerate(sorted(files.items()),1):
  before=p.stat();h=sha(p);z.write(p,PREFIX+rel);after=p.stat()
  assert (before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns),'Source changed: '+rel
  manifest['files'][PREFIX+rel]={'bytes':after.st_size,'sha256':h}
  if i%300==0:print('Cemu full pack',i,'/',len(files),flush=True)
 # Keep the source credits without extra folders at the archive root.
 with zipfile.ZipFile(OUT/'WiiU/CTGP_Aroma_COMPLET_SD_R2_Wiimote_2026-10-30.zip') as source:credits=source.comment
 comment=b'CTGP Cemu complete R2 + Wii Remote cup controls, EUR v81. Close Cemu and merge mlc01 into the actual MLC data location. Base game/update/DLC/emulator are not included. No accounts, certificates, saves or personal settings are included. The local fixed Xapfish 2.6 executable remains a separate friends-menu fix. Experimental Cemu menu retained. Online disconnect remains unresolved.\n\n'+credits
 assert len(comment)<=65535;z.comment=comment
print('Verifying Cemu archive...',flush=True)
with zipfile.ZipFile(DEST) as z:
 assert z.testzip() is None and len(z.namelist())==len(files)
 assert {n.split('/')[0] for n in z.namelist()}=={'mlc01'}
 for item in z.infolist():
  h=hashlib.sha256()
  with z.open(item) as f:
   for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
  assert h.hexdigest()==manifest['files'][item.filename]['sha256']
(OUT/'Documentation/Cemu_R2_Wiimote-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
summary={'archive':str(DEST),'bytes':DEST.stat().st_size,'sha256':sha(DEST),'files':len(files),'crc_and_per_file_sha256':'passed','cups':31,'custom_course_directories':80}
(OUT/'Documentation/Cemu_R2_Wiimote-full-zip.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2),flush=True)
