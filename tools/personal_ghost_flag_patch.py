"""Append the personal ghost card display fix to the existing Options build."""
import hashlib,json,struct,sys,tempfile
from pathlib import Path
import rpxlib,game_options,costume_patch as patch
def build(source,output):
 source,output=Path(source),Path(output);raw,sections=rpxlib.load(source)
 meta=json.loads(Path(str(source)+'.json').read_text())
 code=next(s for s in sections if s['addr']==0x02b10000);data=next(s for s in sections if s['addr']==0x10300000)
 if b'CTGP_PERSONAL_GHOST_FLAG_V1' in code['data']:raise ValueError('Already installed')
 address=0x02633428;expected=0x9421ffa8
 if rpxlib.word_at(sections,address)!=expected:raise ValueError('Unknown card entry')
 cb=(code['addr']+len(code['data'])+4095)&~4095;db=(data['addr']+len(data['data'])+4095)&~4095
 with tempfile.TemporaryDirectory() as temporary:
  try:text,state,symbols=game_options.compile_module(Path(temporary),code_address=cb,data_address=db,
   hooks={'personal_flag_card':(address,expected)},source=Path(__file__).parent/'native/personal_ghost_flag.c',
   cflags=(f'-Wl,--defsym,personal_flag_selected_country=0x{meta["symbols"]["selected_country"]:x}',))
  except Exception as error:
   if hasattr(error,'stderr'):print(error.stderr)
   raise
 code['data']+=bytes(cb-code['addr']-len(code['data']))+text;data['data']+=bytes(db-data['addr']-len(data['data']))+state
 s=next(s for s in sections if s['addr']<=address<s['addr']+len(s['data']));body=bytearray(s['data']);struct.pack_into('>I',body,address-s['addr'],patch.branch(address,symbols['personal_flag_card']));s['data']=bytes(body)
 info=next(s for s in sections if s['t']==0x80000004);body=bytearray(info['data'])
 for off,end,base in [(4,cb+len(text),0x02000000),(12,db+len(state),0x10000000)]:struct.pack_into('>I',body,off,max(struct.unpack_from('>I',body,off)[0],((end+255)&~255)-base))
 info['data']=bytes(body);output.write_bytes(patch.repack(raw,sections));_,checked=rpxlib.load(output)
 for s in sections:
  if s['t']!=0x80000003:assert next(c['data'] for c in checked if c['i']==s['i'])==s['data']
 assert rpxlib.word_at(checked,0x024cb344)==0x81630034 and rpxlib.word_at(checked,0x024cc5bc)==0x7c0802a6
 meta['symbols'].update(symbols);meta.update(output_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),personal_flag_source_sha256=hashlib.sha256(raw).hexdigest(),personal_flag_runtime_verified=False)
 Path(str(output)+'.json').write_text(json.dumps(meta,indent=2));print('Personal ghost flag display candidate built; replay/controller data untouched.')
if __name__=='__main__':build(*sys.argv[1:3])
