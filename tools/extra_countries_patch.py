"""Append expanded country selector to the existing, verified Options build."""
from pathlib import Path
import hashlib,json,struct,tempfile,sys
import rpxlib,game_options,costume_patch as patch

ENTRIES={
 'extra_selected_country':('selected_country',0x3d201031),
 'extra_country_label':('country_label',0x9421fff0),
 'extra_model_value':('model_value',0x9421fff0),
 'extra_model_change':('model_change',0x3d401031),
 'extra_settings_load':('settings_load',0x9421ffa0),
 'extra_settings_save':('settings_save.part.0',0x9421ffc8),
}
ALIASES=['languages','country_choice','options','settings_loaded','settings_dirty',
 'settings_sequence','settings_reads','settings_writes','settings_errors',
 'language_choice','pink_enabled','language_index','settings_language_id',
 'language_set','option_text','settings_transfer']

def build(source,output):
 source,output=Path(source),Path(output)
 raw,sections=rpxlib.load(source);meta=json.loads(Path(str(source)+'.json').read_text())
 code=next(s for s in sections if s['addr']==0x02b10000)
 data=next(s for s in sections if s['addr']==0x10300000)
 if b'CTGP_COUNTRIES_254_V1' in code['data']:raise ValueError('Expansion already present')
 hooks={name:(meta['symbols'][old],word) for name,(old,word) in ENTRIES.items()}
 for address,word in hooks.values():
  if rpxlib.word_at(sections,address)!=word:raise ValueError(f'Unknown entry at {address:08X}')
 relocs={a for s in sections if s['name']=='.rela.text' for a,_,_ in struct.iter_unpack('>III',s['data'])}
 if any(address in relocs for address,_ in hooks.values()):raise ValueError('Relocated entry cannot be patched')
 cb=(code['addr']+len(code['data'])+4095)&~4095
 db=(data['addr']+len(data['data'])+4095)&~4095
 flags=tuple(f'-Wl,--defsym,old_{name}=0x{meta["symbols"][name]:x}' for name in ALIASES)
 with tempfile.TemporaryDirectory() as temporary:
  try:text,state,symbols=game_options.compile_module(Path(temporary),code_address=cb,data_address=db,hooks=hooks,
    source=Path(__file__).parent/'native/extra_countries.c',cflags=flags,data_limit=0x1000)
  except Exception as error:
   if hasattr(error,'stderr'):print(error.stderr)
   raise
 code['data']+=bytes(cb-code['addr']-len(code['data']))+text
 data['data']+=bytes(db-data['addr']-len(data['data']))+state
 for name,(address,_) in hooks.items():
  section=next(s for s in sections if s['addr']<=address<s['addr']+len(s['data']))
  body=bytearray(section['data']);struct.pack_into('>I',body,address-section['addr'],patch.branch(address,symbols[name]));section['data']=bytes(body)
 info=next(s for s in sections if s['t']==0x80000004);body=bytearray(info['data'])
 for offset,end,base in [(4,cb+len(text),0x02000000),(12,db+len(state),0x10000000)]:
  struct.pack_into('>I',body,offset,max(struct.unpack_from('>I',body,offset)[0],((end+255)&~255)-base))
 info['data']=bytes(body);output.write_bytes(patch.repack(raw,sections))
 _,checked=rpxlib.load(output)
 for section in sections:
  if section['t']!=0x80000003:assert next(s['data'] for s in checked if s['i']==section['i'])==section['data']
 assert rpxlib.word_at(checked,0x024cb344)==0x81630034
 assert rpxlib.word_at(checked,0x024cc5bc)==0x7c0802a6
 meta['symbols'].update(symbols)
 meta.update(output_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),extra_countries_source_sha256=hashlib.sha256(raw).hexdigest(),country_count=254,runtime_verified=False)
 Path(str(output)+'.json').write_text(json.dumps(meta,indent=2))
 print('Expanded selector built; 254 choices, controller entries preserved.')

if __name__=='__main__':build(*sys.argv[1:3])
