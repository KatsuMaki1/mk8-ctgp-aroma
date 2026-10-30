"""Overlay the tested cup-input code pack onto the complete R2 SD archive."""
from pathlib import Path
import zipfile,json,hashlib
from mkpack import parse_hax
OUT=Path('C:/Users/evant/Documents/Codex/2026-10-25/files-mentioned-by-the-user-handoff/outputs')
base=OUT/'WiiU/CTGP_Aroma_COMPLET_SD_R2_2026-10-30.zip'
patch=OUT/'WiiU/Mises_a_jour/WiiU_Wiimote_Cups.zip'
dest=OUT/'WiiU/CTGP_Aroma_COMPLET_SD_R2_Wiimote_2026-10-30.zip'
assert not dest.exists(),'Use a new release name rather than overwrite a shared archive'
with zipfile.ZipFile(base) as src,zipfile.ZipFile(patch) as upd,zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED,compresslevel=1,allowZip64=True) as z:
 additions={i.filename:upd.read(i) for i in upd.infolist() if not i.is_dir()};assert len(additions)==6
 prefix='sd/cafeloader/000500001010ED00/'
 features=json.loads(additions[prefix+'Features.json'])
 for name,h in features['files'].items():assert hashlib.sha256(additions[prefix+name]).hexdigest()==h
 assert len(parse_hax(additions[prefix+'Patches.hax']))==81
 assert all(n.startswith('sd/') for n in src.namelist())
 assert set(additions).issubset(src.namelist())
 expected={}
 for n,item in enumerate(src.infolist(),1):
  if item.filename in additions:
   content=additions[item.filename];z.writestr(item.filename,content);expected[item.filename]=hashlib.sha256(content).hexdigest()
  else:
   h=hashlib.sha256()
   with src.open(item) as reader,z.open(item.filename,'w',force_zip64=True) as writer:
    for b in iter(lambda:reader.read(4*1024*1024),b''):writer.write(b);h.update(b)
   expected[item.filename]=h.hexdigest()
  if n%300==0:print('Complete R2 + Wiimote:',n,'/',len(src.infolist()),flush=True)
 z.comment=src.comment+b'\n\nWii Remote cup paging: Minus = existing L action; Plus = existing R action. GP/VS/online selection. Cemu test user-confirmed; real Wii Remote console test pending. Full pack, no older ZIP needed. Close MK8 and merge the CONTENTS of sd into the SD root.'
print('Verifying every SD file...',flush=True)
with zipfile.ZipFile(dest) as z:
 assert z.testzip() is None and len(z.namelist())==len(expected)
 assert {n.split('/')[0] for n in z.namelist()}=={'sd'}
 for item in z.infolist():
  h=hashlib.sha256()
  with z.open(item) as reader:
   for b in iter(lambda:reader.read(4*1024*1024),b''):h.update(b)
  assert h.hexdigest()==expected[item.filename]
h=hashlib.sha256()
with dest.open('rb') as reader:
 for b in iter(lambda:reader.read(4*1024*1024),b''):h.update(b)
result={'archive':str(dest),'bytes':dest.stat().st_size,'sha256':h.hexdigest(),'sd_files':len(expected),'crc_and_per_file_sha256':'passed','base':'complete R2','wiimote_cups':'Cemu user test passed; console pending'}
(OUT/'Documentation/Full_R2_Wiimote-verification.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2),flush=True)
