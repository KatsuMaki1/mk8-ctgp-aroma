"""Build a scoped Wii Remote +/- cup-page patch for EUR81 Cemu and Aroma."""
from pathlib import Path
import sys,json,struct,tempfile,shutil,zipfile
import rpxlib,retarget,costume_patch as patch,game_options as native
from mkpack import parse_hax,write_hax
SOURCE=Path(__file__).parent/'native/wiimote_cups.c'
MARKER=b'MK8_WIIMOTE_CUP_PAGES_V1';HOOK=0x0253c31c;WORD=0x7c0802a6
OUT=Path('C:/Users/evant/Documents/Codex/2026-10-25/files-mentioned-by-the-user-handoff/outputs')
def cemu(source,output):
 raw,sections=rpxlib.load(source)
 code=next(s for s in sections if s['addr']==0x02b10000);data=next(s for s in sections if s['addr']==0x10300000);info=next(s for s in sections if s['t']==0x80000004)
 if MARKER in code['data']:raise ValueError('Wiimote patch already installed')
 if rpxlib.word_at(sections,HOOK)!=WORD:raise ValueError('Unknown key-poll prologue')
 cb=(code['addr']+len(code['data'])+0xfff)&~0xfff;db=(data['addr']+len(data['data'])+0xfff)&~0xfff
 assert cb<0x02c00000 and db<0x10310000
 with tempfile.TemporaryDirectory() as tmp:text,mutable,symbols=native.compile_module(Path(tmp),code_address=cb,data_address=db,hooks={'wiikey':(HOOK,WORD)},source=SOURCE)
 target=next(s for s in sections if s['addr']<=HOOK<s['addr']+len(s['data']));b=bytearray(target['data']);struct.pack_into('>I',b,HOOK-target['addr'],patch.branch(HOOK,symbols['wiimote_cup_poll']));target['data']=bytes(b)
 code['data']+=bytes(cb-code['addr']-len(code['data']))+text;data['data']+=bytes(db-data['addr']-len(data['data']))+mutable
 fi=bytearray(info['data']);struct.pack_into('>I',fi,4,max(struct.unpack_from('>I',fi,4)[0],((cb+len(text)+255)&~255)-0x02000000));struct.pack_into('>I',fi,12,max(struct.unpack_from('>I',fi,12)[0],((db+len(mutable)+255)&~255)-0x10000000));info['data']=bytes(fi)
 result=patch.repack(raw,sections);output.parent.mkdir(parents=True,exist_ok=True);output.write_bytes(result)
 _,check=rpxlib.load(output)
 for s in sections:
  if s['t']!=0x80000003:assert s['data']==next(t['data'] for t in check if t['i']==s['i'])
 manifest={'source_sha256':patch.digest(raw),'output_sha256':patch.digest(result),'symbols':symbols,'native_hook':hex(HOOK),'native_original_word':hex(WORD),'hardware_tested':False}
 Path(str(output)+'.json').write_text(json.dumps(manifest,indent=2)+'\n');return manifest
def console(base,folder):
 features=json.loads((base/'Features.json').read_text())
 for n,h in features['files'].items():assert patch.digest((base/n).read_bytes())==h,n
 code=(base/'Code.bin').read_bytes();data=(base/'Data.bin').read_bytes();assert MARKER not in code
 patches=parse_hax((base/'Patches.hax').read_bytes());verify=parse_hax((base/'Verify.hax').read_bytes());a=HOOK+retarget.GT_SHIFT
 assert [x for x,b in patches]==[x for x,b in verify]
 assert not any(x<=a<x+len(b) for x,b in patches)
 co=(len(code)+4095)&~4095;do=(len(data)+4095)&~4095
 with tempfile.TemporaryDirectory() as tmp:text,mutable,symbols=native.compile_module(Path(tmp),code_address=retarget.CB+co,data_address=retarget.DB+do,hooks={'wiikey':(a,WORD)},source=SOURCE,cflags=('-DGD_SHIFT='+hex(retarget.GD_SHIFT),))
 code+=bytes(co-len(code))+text;code+=bytes(-len(code)%4)+struct.pack('>I',0x4e800020);data+=bytes(do-len(data))+mutable
 patches.append((a,struct.pack('>I',patch.branch(a,symbols['wiimote_cup_poll']))));verify.append((a,struct.pack('>I',WORD)))
 dest=folder/'sd/cafeloader/000500001010ED00';dest.mkdir(parents=True,exist_ok=False)
 shutil.copy2(base/'Addr.bin',dest/'Addr.bin');(dest/'Code.bin').write_bytes(code);(dest/'Data.bin').write_bytes(data);(dest/'Patches.hax').write_bytes(write_hax(patches));(dest/'Verify.hax').write_bytes(write_hax(verify))
 features['features'].append('Wii Remote -/+ changes cup pages in GP, VS and online voting; GamePad/Classic/Pro unchanged')
 features['wiimote_cups']={'symbols':symbols,'hook':hex(a),'hardware_tested':False}
 features['files']={n:patch.digest((dest/n).read_bytes()) for n in features['files']};(dest/'Features.json').write_text(json.dumps(features,indent=2)+'\n')
 rollback=folder/'rollback/sd/cafeloader/000500001010ED00';shutil.copytree(base,rollback)
 assert len(patches)==81
 zpath=folder.with_suffix('.zip')
 with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED) as z:
  for p in sorted((folder/'sd').rglob('*')):
   if p.is_file():z.write(p,p.relative_to(folder).as_posix())
  z.comment=b'CTGP Wii Remote cup paging: - previous, + next. Merge sd contents on SD with MK8 closed. EUR81, existing pack required. Test build: real Wii Remote validation pending.'
 with zipfile.ZipFile(zpath) as z:assert z.testzip() is None
 return {'zip':str(zpath),'patches':len(patches),'symbols':symbols,'hardware_tested':False}
def build():
 source=Path('C:/Users/evant/AppData/Roaming/Cemu/mlc01/usr/title/0005000e/1010ed00/code/Turbo.rpx')
 candidate=OUT/'Cemu/Turbo_Wiimote_Cups_EUR81.rpx';print(json.dumps(cemu(source,candidate),indent=2))
 base=OUT/'WiiU/Mises_a_jour/WiiU_Boltthunder4_Cups_Addon/sd/cafeloader/000500001010ED00'
 print(json.dumps(console(base,OUT/'WiiU/Mises_a_jour/WiiU_Wiimote_Cups'),indent=2))
if __name__=='__main__':build()
