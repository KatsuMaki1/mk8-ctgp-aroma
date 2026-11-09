from pathlib import Path
import zipfile,json,hashlib,time
ROOT=Path(r'C:/Users/evant/Documents/Codex/2026-10-25/files-mentioned-by-the-user-handoff')
DIR=ROOT/'outputs/WiiU'
BASE=DIR/'CTGP_Aroma_COMPLET_SD_v026_Bolt_1page_2026-11-01.zip'
UPDATE=DIR/'Mises_a_jour/CTGP_WiiU_MAJ_Optimisations_R3_Options_R7_TEST_2026-11-04.zip'
OUT=DIR/'CTGP_WiiU_COMPLET_SD_R7_Optimisations_R3_2026-11-04.zip'
PART=OUT.with_suffix('.zip.partial')
assert not OUT.exists() and not PART.exists()
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(4*1048576),b''):h.update(b)
 return h.hexdigest()
assert digest(UPDATE)=='aed0c330191bfe647067d38757eec7b3097c9cbdf1c0c605bfa5bf94e8abbf4b'
manifest={}
with zipfile.ZipFile(BASE) as base,zipfile.ZipFile(UPDATE) as update:
 bm=json.loads(base.read('sd/CTGP_manifest.json'))['files']
 um=json.loads(update.read('sd/CTGP_MAJ_R7_manifest.json'))['files']
 selected={n:base for n in base.namelist() if not n.endswith('/')}
 selected.update({n:update for n in update.namelist() if not n.endswith('/')})
 selected.pop('sd/CTGP_manifest.json',None);selected.pop('sd/CTGP_README.txt',None)
 assert len(selected)==len(set(selected))
 print('Merging',len(selected),'files',flush=True)
 with zipfile.ZipFile(PART,'w',zipfile.ZIP_DEFLATED,compresslevel=1,allowZip64=True) as out:
  for i,(name,source) in enumerate(sorted(selected.items()),1):
   assert name.startswith('sd/') and '..' not in Path(name).parts
   assert not name.lower().endswith(('.rpx','.tik','.key'))
   assert not any(x in name.lower() for x in ['network_services','account.dat','keys.txt'])
   h=hashlib.sha256();size=0
   with source.open(name) as src,out.open(name,'w',force_zip64=True) as dst:
    for b in iter(lambda:src.read(4*1048576),b''):dst.write(b);h.update(b);size+=len(b)
   check=(um if source is update else bm).get(name)
   if check:assert h.hexdigest()==check['sha256'],name
   manifest[name]={'size':size,'sha256':h.hexdigest()}
   if i%150==0:print('Packed',i,'/',len(selected),flush=True)
  readme=('CTGP Wii U EUR v81 - COMPLETE PACK R7 / OPTIMIZATIONS R3 - 2026-11-04\n\n'
   'Includes the full v026 pack and cumulative R7 update. No older patch is needed.\n'
   'Back up your SD. Close MK8, copy the CONTENTS of sd/ to your SD root, replace files, and fully restart the console.\n'
   'Only one mk8-ct.wps plugin should be active. DSI diagnostics are retained.\n'
   'Read LIRE_MOI_MAJ_R7.txt for optimization details and known limitations.\n'
   '60 FPS is a target, not guaranteed. Textures are less detailed. Wii U validation pending.\n'
   'Country flag in online lobby remains unresolved; TT150/200 records/ghosts remain shared.\n').encode()
  out.writestr('sd/CTGP_README.txt',readme)
  manifest['sd/CTGP_README.txt']={'size':len(readme),'sha256':hashlib.sha256(readme).hexdigest()}
  out.writestr('sd/CTGP_manifest.json',json.dumps({'release':'R7 complete / optimizations R3','full_pack':True,'region':'EUR','game_version':81,'console_tested':False,'tt_records_separated':False,'files':manifest},indent=2))
print('Verifying every member',flush=True)
with zipfile.ZipFile(PART) as z:
 assert len(z.namelist())==len(set(z.namelist()))
 assert all(n.startswith('sd/') for n in z.namelist())
 for name,meta in manifest.items():
  h=hashlib.sha256();size=0
  with z.open(name) as f:
   for b in iter(lambda:f.read(4*1048576),b''):h.update(b);size+=len(b)
  assert size==meta['size'] and h.hexdigest()==meta['sha256'],name
 assert json.loads(z.read('sd/CTGP_manifest.json'))['files']==manifest
PART.rename(OUT)
result={'complete':{'path':str(OUT),'bytes':OUT.stat().st_size,'sha256':digest(OUT),'files':len(manifest)+1},'update':{'path':str(UPDATE),'bytes':UPDATE.stat().st_size,'sha256':digest(UPDATE)},'all_member_hashes_and_crc':'passed','root':'sd/'}
(ROOT/'work/optimization_r3/full_package_verification.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result),flush=True)
