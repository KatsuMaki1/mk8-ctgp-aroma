"""SD-only rollup update from the existing v026 pack + Pays P2/music mini."""
from pathlib import Path
import hashlib,json,zipfile
from optimization_r3 import WORK,ROOT,STAGE
REPO=Path(__file__).resolve().parents[1]
OUT=WORK.parent/'outputs/WiiU/Mises_a_jour/CTGP_WiiU_MAJ_Optimisations_R3_Options_R7_TEST_2026-11-04.zip'
BASE=WORK.parent/'outputs/WiiU/CTGP_Aroma_COMPLET_SD_v026_Bolt_1page_2026-11-01.zip'
PREFIX='sd/cafeloader/vol/000500001010ED00/content/'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(4*1048576),b''):h.update(b)
 return h.hexdigest()
def run():
 assert not OUT.exists(),'Never overwrite a delivered archive'
 report=json.loads((ROOT/'report.json').read_text());summary=json.loads((ROOT/'summary.json').read_text())
 objects=WORK/'optimization_objects_r3';objrows=json.loads((objects/'report.json').read_text())
 objsummary=json.loads((objects/'summary.json').read_text())
 dense=WORK/'optimization_dense_r3';dense_summary=json.loads((dense/'summary.json').read_text())
 dense_rows={r['directory']:r for r in json.loads((dense/'report.json').read_text())}
 discarded={r['directory'] for r in dense_summary['preserved_inputs']}
 for r in report:
  if r['directory'] in discarded and r['status']=='optimized_verified':
   summary['optimized']-=1
   summary['triangles_removed']-=r.get('triangles_removed',0)
   summary['texture_bytes_saved']-=r.get('texture_bytes_saved',0)
 payload=ROOT/'release/sd/cafeloader/000500001010ED00'
 assert 0<(payload/'Code.bin').stat().st_size<=1048576
 assert 0<(payload/'Data.bin').stat().st_size<=1048576
 assert (payload/'Addr.bin').stat().st_size==8
 assert (payload/'Patches.hax').stat().st_size==(payload/'Verify.hax').stat().st_size
 with zipfile.ZipFile(BASE) as z:baseline=json.loads(z.read('sd/CTGP_manifest.json'))['files']
 entries={};groups={}
 def add(name,path,group):
  path=Path(path);assert name.startswith('sd/') and path.is_file()
  if name in baseline and baseline[name]['sha256']==sha(path):return
  entries[name]=path;groups[name]=group
 for p in STAGE.rglob('*'):
  if p.is_file():add(PREFIX+p.relative_to(STAGE).as_posix(),p,'cumulative_R4_fix')
 sources={r['directory']:r for r in json.loads((ROOT/'source_manifest.json').read_text())}
 for row in report:
  d=row['directory']
  dr=dense_rows.get(d,{})
  if dr.get('status')=='optimized_verified':
   p=dense/'content/course'/d/'course_model.szs';assert sha(p)==dr['output_sha256']
  elif dr.get('status')=='preserve_input':
   p=Path(sources[d]['input']);assert sha(p)==sources[d]['input_sha256']
  elif row['status']=='optimized_verified':
   p=ROOT/'content/course'/d/'course_model.szs';assert sha(p)==row['output_sha256']
  else:p=Path(sources[d]['input']);assert sha(p)==sources[d]['input_sha256']
  add(PREFIX+'course/'+d+'/course_model.szs',p,'course_model')
 objsource={r['directory']:r for r in json.loads((objects/'source_manifest.json').read_text())}
 for row in objrows:
  if row['status']!='optimized_verified':continue
  assert row.get('triangles_removed',0)==0
  p=objects/row['directory']/'optimized.bfres'
  patch=json.loads((p.parent/'patch_report.json').read_text());assert sha(p)==patch['optimized_sha256']
  for rel in objsource[row['directory']]['paths']:add(PREFIX+rel,p,'private_object_texture')
 for p in (ROOT/'release/sd').rglob('*'):
  if p.is_file():add('sd/'+p.relative_to(ROOT/'release/sd').as_posix(),p,'aroma_payload')
 add('sd/wiiu/environments/aroma/plugins/mk8-ct.wps',REPO/'plugin/mk8-ct.wps','aroma_plugin')
 # The old mini contains this music already, but keep it in the rollup so no
 # cumulative update can accidentally revert the user's supplied menu theme.
 add(PREFIX+'audio/stream/BGM_MENU_SINGLE_MULTI.bfstm',REPO/'work/menu_music/BGM_MENU_SINGLE_MULTI.bfstm','menu_music')
 add(PREFIX+'ui/cmn/menu.szs',REPO/'work/options_i18n/menu_native_rows_p4.szs','native_options_layout')
 add('sd/CTGP_NOTICES/LUCIDE_LICENSE.txt',REPO/'work/options_panel/LUCIDE_LICENSE.txt','notice')
 files={n:{'bytes':p.stat().st_size,'sha256':sha(p),'group':groups[n]} for n,p in sorted(entries.items())}
 manifest={'release':'R7 TEST / optimizations R3','region':'EUR','game_version':81,
  'baseline':'Existing full v026 + R4 and Pays P2/menu music mini','full_pack':False,
  'wiiu_fps_measured':False,'console_validated':False,'target_fps':60,
  'country_online_flag_fixed':False,'dsi_screen_preserved':True,
  'courses':summary,'private_objects':objsummary,'additional_geometry':dense_summary,'files':files}
 readme=f'''CTGP Wii U - MISE A JOUR R7 TEST / OPTIMISATIONS R3 - 2026-11-04

Pour le pack EUR v81 deja installe, y compris ton mini patch Pays P2 + musique.
Ce ZIP est une mise a jour cumulative, PAS un pack complet.

Ferme Mario Kart 8. Sauvegarde les fichiers de ta SD avant remplacement.
Copie le CONTENU du dossier sd a la racine de ta SD, accepte les remplacements,
puis redemarre completement la Wii U. Garde un seul plugin mk8-ct.wps actif.
L'ecran DSI/ISI/PROGRAM est conserve pour le diagnostic.

OPTIMISATIONS
{summary['audited']} circuits custom audites, {summary['optimized']} modeles allegeables verifies.
{summary['triangles_removed']:,} triangles de decor retires supplementaires.
{dense_summary['nondegenerate_triangles_removed']:,} autres triangles de decor neutralises dans les modeles a plusieurs groupes/LOD, sans changer leurs descripteurs de dessin.
{summary['texture_bytes_saved']/1048576:.1f} Mio de textures en moins, cumules sur les circuits (pas la memoire d'une seule course).
Textures de decor general/detail limitees a256; routes, textes et eclairages a512.
Les textures seront moins fines. Frontieres et attributs de maillage proteges.
Les collisions, checkpoints et trajets ne sont pas modifies par cette passe.
{objsummary['optimized']} gros objets/ciels prives uniques optimises en textures; leur geometrie reste identique.
Les entrees incompatibles ou sans reduction sure sont conservees, jamais remplacees par un modele incomplet.

60 FPS est un OBJECTIF. Aucune mesure Wii U complete n'a ete effectuee.
Ce patch ne garantit pas60 FPS sur chaque circuit ou configuration VS.
Les reductions de memoire et de triangles ne sont pas un pourcentage de gain FPS.

CORRECTIFS CUMULATIFS
Ordre/apercus BCP, oiseaux et Wigglers Maple, correctif Sky-High Sundae,
routage prive des objets, bandeau des noms de circuits, adaptateur audio ROB R20,
Options natives compactes,119 pays,8 langues EUR et correctif du focus Solo P6.
La musique de menu fournie est conservee. Choix Pays/Langue temporaires par session.
Le drapeau en salon reste en diagnostic; ne pas considerer ce probleme resolu.
Menus/langues et ROB VS ne sont pas certifies sur console par cette livraison.
Les records/fantomes TT150/200 ne sont toujours pas separes.

Verification structurelle et relecture BFRES effectuees; validation console requise.
Pour revenir en arriere, restaure les fichiers sauvegardes avant cette mise a jour.
'''
 clean_fields=['directory','name','status','triangles','triangles_removed','texture_bytes','texture_bytes_saved','changed_shapes','changed_textures','geometry_fallback']
 audit=[dict({k:r[k] for k in clean_fields if k in r},additional_geometry=dense_rows.get(r['directory'],{})) for r in report]
 print('Packing',len(entries),'changed files;',round(sum(p.stat().st_size for p in entries.values())/1048576),'MiB uncompressed',flush=True)
 OUT.parent.mkdir(parents=True,exist_ok=True)
 with zipfile.ZipFile(OUT,'w',zipfile.ZIP_DEFLATED,compresslevel=1,allowZip64=True) as z:
  for i,(n,p) in enumerate(sorted(entries.items()),1):
   z.write(p,n)
   if i%30==0:print('ZIP',i,'/',len(entries),flush=True)
  z.writestr('sd/LIRE_MOI_MAJ_R7.txt',readme)
  z.writestr('sd/CTGP_MAJ_R7_manifest.json',json.dumps(manifest,indent=2))
  z.writestr('sd/CTGP_Optimisation_R3_audit.json',json.dumps(audit,indent=2))
 with zipfile.ZipFile(OUT) as z:
  assert z.testzip() is None
  for n in z.namelist():
   assert n.startswith('sd/') and not n.endswith(('.rpx','.tik','.key'))
   assert not any(t in n.lower() for t in ['network_services','account.dat','80000001','keys.txt'])
  for n,meta in files.items():
   h=hashlib.sha256()
   with z.open(n) as f:
    for block in iter(lambda:f.read(4*1048576),b''):h.update(block)
   assert h.hexdigest()==meta['sha256']
 result={'zip':str(OUT),'bytes':OUT.stat().st_size,'sha256':sha(OUT),'files':len(entries)+3,'crc_and_file_hashes':'passed'}
 (ROOT/'zip_verification.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)
if __name__=='__main__':run()
