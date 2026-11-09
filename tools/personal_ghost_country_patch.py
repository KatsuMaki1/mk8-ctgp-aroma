"""Set the country on personal ghost cards through the verified native setter."""
from pathlib import Path
import hashlib,json,struct,sys,tempfile
import game_options,rpxlib,costume_patch as patch
def build(source,output):
 source,output=Path(source),Path(output);raw,sections=rpxlib.load(source);meta=json.loads(Path(str(source)+'.json').read_text())
 code=next(s for s in sections if s['addr']==0x02b10000);data=next(s for s in sections if s['addr']==0x10300000)
 if b'CTGP_PERSONAL_CARD_COUNTRY_V2' in code['data']:raise ValueError('Already installed')
 if b'CTGP_PERSONAL_GHOST_FLAG_V1' in code['data']:raise ValueError('Use P63; obsolete card hook must not remain')
 call,native=0x025c67f4,0x025861cc;expected=patch.branch(call,native)|1
 if rpxlib.word_at(sections,call)!=expected:raise ValueError('Unknown personal record setter call')
 cb=(code['addr']+len(code['data'])+4095)&~4095;db=(data['addr']+len(data['data'])+4095)&~4095
 flags=(f'-Wl,--defsym,personal_country_selected=0x{meta["symbols"]["selected_country"]:x}',f'-Wl,--defsym,personal_country_native_set=0x{native:x}')
 with tempfile.TemporaryDirectory() as temporary:
  try:text,state,symbols=game_options.compile_module(Path(temporary),code_address=cb,data_address=db,hooks={},source=Path(__file__).parent/'native/personal_ghost_country.c',cflags=flags)
  except Exception as error:
   if hasattr(error,'stderr'):print(error.stderr)
   raise
 code['data']+=bytes(cb-code['addr']-len(code['data']))+text;data['data']+=bytes(db-data['addr']-len(data['data']))+state
 s=next(s for s in sections if s['addr']<=call<s['addr']+len(s['data']));body=bytearray(s['data']);struct.pack_into('>I',body,call-s['addr'],patch.branch(call,symbols['personal_country_set'])|1);s['data']=bytes(body)
 info=next(s for s in sections if s['t']==0x80000004);body=bytearray(info['data'])
 for off,end,base in [(4,cb+len(text),0x02000000),(12,db+len(state),0x10000000)]:struct.pack_into('>I',body,off,max(struct.unpack_from('>I',body,off)[0],((end+255)&~255)-base))
 info['data']=bytes(body);output.write_bytes(patch.repack(raw,sections));_,checked=rpxlib.load(output)
 for s in sections:
  if s['t']!=0x80000003:assert next(x['data'] for x in checked if x['i']==s['i'])==s['data']
 for a in [0x025c6b5c,0x025c6e9c]:assert rpxlib.word_at(checked,a)==(patch.branch(a,native)|1)
 assert rpxlib.word_at(checked,0x02633428)==0x9421ffa8
 assert rpxlib.word_at(checked,0x024cb344)==0x81630034 and rpxlib.word_at(checked,0x024cc5bc)==0x7c0802a6
 meta['symbols'].update(symbols);meta.update(output_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),personal_country_source_sha256=hashlib.sha256(raw).hexdigest(),personal_country_runtime_verified=False)
 Path(str(output)+'.json').write_text(json.dumps(meta,indent=2));print('Personal setter patched; staff/download setters and controller accessors verified unchanged.')
if __name__=='__main__':build(*sys.argv[1:3])
