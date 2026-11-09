"""Audit and optimize every playable CUP0 course, keeping unsupported inputs intact."""
from pathlib import Path
import sys,os,json,subprocess,hashlib,io,struct
import cup0,szs
ROOT=Path('C:/Users/evant/Documents/Codex/2026-10-25/files-mentioned-by-the-user-handoff/work/optimization_r2')
CONTENT=Path('C:/Users/evant/AppData/Roaming/Cemu/mlc01/usr/title/0005000e/1010ed00/content')
DLL=ROOT/'bin_verify/model_optimizer.dll';WSZST='C:/Program Files/Wiimm/SZS/wszst.exe'
ENV=dict(os.environ,CTGP_OPT_PROFILE='R2')
def sha(b):return hashlib.sha256(b).hexdigest()
def call(args):
 p=subprocess.run([str(x) for x in args],capture_output=True,text=True,env=ENV)
 if p.returncode:raise RuntimeError((p.stderr+p.stdout)[-1500:])
 return p.stdout
def model(mode,folder):return call(['dotnet',DLL,mode,folder/'model.bfres',folder if mode=='profile' else folder/('meshes' if mode=='export' else 'textures')])
def audit():
 ROOT.mkdir(parents=True,exist_ok=True);tracks={t.dir:t.name for c in cup0.parse((CONTENT/'data.cup0').read_bytes()) for t in c.tracks if t.dir!='Ginvalid'}
 report=[]
 for n,(d,name) in enumerate(tracks.items(),1):
  folder=ROOT/d;folder.mkdir(exist_ok=True);row={'directory':d,'name':name}
  try:
   source=CONTENT/'course'/d/'course_model.szs';raw=source.read_bytes();row['source_sha256']=sha(raw);row['source_bytes']=len(raw)
   if not (folder/'model.bfres').exists():
    arc=folder/'source.raw'
    if raw[:4]==b'Yaz0':call([WSZST,'decompress',source,'--dest',arc,'--overwrite','--max-file-size=512m']);data=arc.read_bytes()
    else:data=raw;arc.write_bytes(data)
    meta={'container':data[:4].decode(),'source_sha256':sha(raw)}
    if data[:4]==b'FRES':bfres=data
    elif data[:4]!=b'SARC':raise ValueError('Non-standard model and texture signatures; keep original')
    else:
     # Names in old SARC files can be non-UTF8. Locate the BFRES using raw
     # node offsets and preserve the complete container byte-for-byte.
     off=struct.unpack_from('>I',data,12)[0];count=struct.unpack_from('>H',data,0x1a)[0];models=[]
     for i in range(count):
      h,attr,start,end=struct.unpack_from('>IIII',data,0x20+16*i);start+=off;end+=off
      if data[start:start+4]==b'FRES':models.append((start,end-start,data[start:end]))
     if len(models)!=1:raise ValueError('Expected one BFRES; found '+str(len(models)))
     start,size,bfres=models[0];meta.update(member_offset=start,member_length=size)
    (folder/'model.bfres').write_bytes(bfres);(folder/'archive.json').write_text(json.dumps(meta,indent=2))
   meta=json.loads((folder/'archive.json').read_text());assert meta['source_sha256']==sha(raw),'Source changed since extraction'
   if 'source_signature' in meta:raise ValueError('Non-standard model and texture signatures; keep original')
   if not (folder/'profile.json').exists():model('profile',folder)
   p=json.loads((folder/'profile.json').read_text());row.update(triangles=sum(x['triangles'] for x in p['shapes']),texture_bytes=sum(x['bytes'] for x in p['textures']),shapes=len(p['shapes']),textures=len(p['textures']),status='audited')
  except Exception as e:row.update(status='unchanged_unsupported',reason=str(e))
  report.append(row);(ROOT/'audit.json').write_text(json.dumps(report,indent=2));print(n,'/',len(tracks),d,row['status'],flush=True)
 return report
def prepare():
 from PIL import Image
 import numpy as np
 rows=json.loads((ROOT/'audit.json').read_text())
 for n,row in enumerate(rows,1):
  if row['status']!='audited':continue
  folder=ROOT/row['directory']
  try:
   if (folder/'prepared.json').exists():continue
   model('export',folder);model('textures',folder)
   textures=json.loads((folder/'profile.json').read_text())['textures'];resized=[]
   for file in (folder/'textures').glob('*.basebc'):
    t=textures[int(file.stem)];name=t['Name'].lower();readable=any(s in name for s in ('road','ground','asphalt','logo','sign','arrow','text','start','line','zebra'));bake=any(s in name for s in ('bake','light','shadow','aomap')) or name in ('b l','b');detail=any(s in name for s in ('_nrm','_spm','normal','specular'));cap=(512 if readable or bake else 256) if ENV.get('CTGP_OPT_PROFILE')=='R3' else (512 if detail else 1024 if readable or bake else 512)
    drop=0
    while max(t['Width']>>drop,t['Height']>>drop)>cap:drop+=1
    codec=1 if t['format']=='T_BC1_UNorm' else 3
    image=Image.frombytes('RGBA',(t['Width'],t['Height']),file.read_bytes(),'bcn',codec)
    image=image.resize((max(1,t['Width']>>drop),max(1,t['Height']>>drop)),Image.Resampling.LANCZOS)
    out=io.BytesIO();image.save(out,format='DDS',pixel_format='DXT1' if codec==1 else 'DXT5');bc=out.getvalue()[128:]
    check=Image.frombytes('RGBA',image.size,bc,'bcn',codec);mse=float(np.mean((np.array(check,dtype=float)-np.array(image,dtype=float))**2));psnr=float(10*np.log10(255**2/max(mse,1e-10)))
    if psnr<28:continue # Keep this original texture rather than accept poor recompression.
    file.with_suffix('.resampled').write_bytes(bc);resized.append({'name':t['Name'],'psnr_db':psnr,'size':list(image.size)})
   model('textures',folder);(folder/'prepared.json').write_text(json.dumps({'resized':resized},indent=2))
   print('Prepared',n,'/',len(rows),row['directory'],flush=True)
  except Exception as e:
   row.update(status='unchanged_unsupported',reason=str(e));(ROOT/'audit.json').write_text(json.dumps(rows,indent=2));print('Preserving unsupported model',row['directory'],str(e)[-200:],flush=True)
def build():
 sys.path.insert(0,str(Path(__file__).parent/'model_optimizer'));import patch
 rows=json.loads((ROOT/'audit.json').read_text());result=[]
 for n,row in enumerate(rows,1):
  if not int(os.environ.get('R2_START','0'))<=n-1<int(os.environ.get('R2_STOP','80')):continue
  folder=ROOT/row['directory']
  if not (folder/'prepared.json').exists() or row['status']!='audited':result.append(row);continue
  try:
   existing=folder/'result.json'
   if existing.exists():result.append(json.loads(existing.read_text()));continue
   patch.patch(folder)
   try:call(['dotnet',DLL,'verify',folder/'model.bfres',folder/'meshes',folder/'optimized.bfres'])
   except RuntimeError as error:
    if not any(s in str(error) for s in ('Protected shape changed','Index roundtrip mismatch')):raise
    # Shared index buffers can also serve a protected shape. Keep all geometry
    # on this course intact, while retaining independently verified textures.
    for indices in (folder/'meshes').glob('*.newidx'):indices.replace(indices.with_suffix('.discardedidx'))
    row['geometry_fallback']='Shared/protected index buffers: geometry unchanged'
    patch.patch(folder);call(['dotnet',DLL,'verify',folder/'model.bfres',folder/'meshes',folder/'optimized.bfres'])
   changes=json.loads((folder/'patch_report.json').read_text());tris=sum(x['before_triangles']-x['after_triangles'] for x in changes['changed_meshes']);memory=sum(x['old_bytes']-x['bytes'] for x in changes['textures'])
   row.update(triangles_removed=tris,texture_bytes_saved=memory,changed_shapes=len(changes['changed_meshes']),changed_textures=len(changes['textures']))
   if tris or memory:
    original=(folder/'source.raw').read_bytes();meta=json.loads((folder/'archive.json').read_text());optimized=(folder/'optimized.bfres').read_bytes()
    if meta['container']=='SARC':
     if 'member_offset' in meta:
      start,size=meta['member_offset'],meta['member_length'];assert len(optimized)==size
      optimized=original[:start]+optimized+original[start+size:]
     else:
      ents=[(x,optimized if x==meta['member'] else b) for x,b,h in szs.sarc_read(original)];optimized=szs.sarc_write(ents,meta['alignments'],meta['version'])
      assert all(b==dict(ents)[x] for x,b,h in szs.sarc_read(original) if x!=meta['member'])
    if 'source_signature' in meta:optimized=bytes.fromhex(meta['source_signature'])+optimized[4:]
    stage=folder/'encoded.raw';stage.write_bytes(optimized);dest=ROOT/'content/course'/row['directory']/'course_model.szs';dest.parent.mkdir(parents=True,exist_ok=True)
    call([WSZST,'compress',stage,'--dest',dest,'--yaz0','--compr=1','--overwrite','--max-file-size=512m'])
    check=folder/'recheck.raw';call([WSZST,'decompress',dest,'--dest',check,'--overwrite','--max-file-size=512m']);assert check.read_bytes()==optimized
    row.update(status='optimized_verified',output_sha256=sha(dest.read_bytes()),output_bytes=dest.stat().st_size)
   else:row['status']='unchanged_no_safe_reduction'
   existing.write_text(json.dumps(row,indent=2));print('Verified',n,'/',len(rows),row['directory'],'triangles -'+str(tris),'texture MiB -'+str(round(memory/1048576,1)),flush=True)
  except Exception as e:
   # Never publish a failing candidate even if encoding already produced a file.
   dest=ROOT/'content/course'/row['directory']/'course_model.szs'
   if dest.exists():dest.unlink()
   row.update(status='unchanged_unsupported',reason=str(e));print('Keeping original',row['directory'],str(e)[-200:],flush=True)
   (folder/'error.json').write_text(json.dumps(row,indent=2))
  result.append(row)
  if not os.environ.get('R2_WORKER'):(ROOT/'report.json').write_text(json.dumps(result,indent=2))
 if not os.environ.get('R2_WORKER'):(ROOT/'report.json').write_text(json.dumps(result,indent=2))
def aggregate():
 rows=json.loads((ROOT/'audit.json').read_text());result=[]
 for row in rows:
  folder=ROOT/row['directory'];p=folder/'result.json';e=folder/'error.json'
  if p.exists():row=json.loads(p.read_text())
  elif e.exists():row=json.loads(e.read_text())
  elif row['status']=='audited':raise ValueError('Course not processed: '+row['directory'])
  if (folder/'archive.json').exists() and 'source_signature' in json.loads((folder/'archive.json').read_text()):row['reason']='Non-standard model and texture signatures; original preserved'
  result.append(row)
 (ROOT/'report.json').write_text(json.dumps(result,indent=2));print('All',len(result),'courses accounted for',flush=True)
if __name__=='__main__':{'audit':audit,'prepare':prepare,'build':build,'aggregate':aggregate}[sys.argv[1]]()
