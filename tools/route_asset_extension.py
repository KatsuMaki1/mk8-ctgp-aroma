"""Chain, rather than replace, every installed model/course/UI formatter."""
from pathlib import Path
import hashlib,json,struct,sys,tempfile
import game_options,rpxlib,costume_patch as patch
def build(source,output):
 source,output=Path(source),Path(output);raw,sections=rpxlib.load(source);meta=json.loads(Path(str(source)+'.json').read_text())
 code=next(s for s in sections if s['addr']==0x02b10000);data=next(s for s in sections if s['addr']==0x10300000)
 if b'CTGP_LONDON_BRIDGE_RESOURCE_V1' in code['data'] or b'CTGP_LONDON_BRIDGE_RESOURCE_V2' in code['data']:raise ValueError('Use the P66 base; do not chain the obsolete input hook')
 addresses=[0x0272c02c,0x0272c240,0x0272c8fc];previous=[]
 for a in addresses:
  w=rpxlib.word_at(sections,a)
  if w&0xfc000003!=0x48000000:raise ValueError('Expected installed formatter branch')
  offset=w&0x3fffffc;offset-=0x4000000 if offset&0x2000000 else 0;target=a+offset
  if not code['addr']<=target<code['addr']+len(code['data']):raise ValueError('Unknown previous formatter')
  previous.append(target)
 cb=(code['addr']+len(code['data'])+4095)&~4095;db=(data['addr']+len(data['data'])+4095)&~4095
 with tempfile.TemporaryDirectory() as temporary:
  try:text,state,symbols=game_options.compile_module(Path(temporary),code_address=cb,data_address=db,hooks={},source=Path(__file__).parent/'native/route_asset_extension.c',cflags=tuple(f'-DROUTE_ORIGINAL{i}=0x{v:x}u' for i,v in enumerate(previous)))
  except Exception as error:
   if hasattr(error,'stderr'):print(error.stderr)
   raise
 code['data']+=bytes(cb-code['addr']-len(code['data']))+text;data['data']+=bytes(db-data['addr']-len(data['data']))+state
 for i,a in enumerate(addresses):
  s=next(s for s in sections if s['addr']<=a<s['addr']+len(s['data']));body=bytearray(s['data']);struct.pack_into('>I',body,a-s['addr'],patch.branch(a,symbols[f'route_asset_format{i}']));s['data']=bytes(body)
 info=next(s for s in sections if s['t']==0x80000004);body=bytearray(info['data'])
 for off,end,base in [(4,cb+len(text),0x02000000),(12,db+len(state),0x10000000)]:struct.pack_into('>I',body,off,max(struct.unpack_from('>I',body,off)[0],((end+255)&~255)-base))
 info['data']=bytes(body);output.write_bytes(patch.repack(raw,sections));_,checked=rpxlib.load(output)
 for s in sections:
  if s['t']!=0x80000003:assert next(x['data'] for x in checked if x['i']==s['i'])==s['data']
 meta['symbols'].update(symbols);meta.update(output_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),route_asset_previous_formatters=previous,route_asset_runtime_verified=False)
 Path(str(output)+'.json').write_text(json.dumps(meta,indent=2));print('Resource extension built; previous formatters chained.')
if __name__=='__main__':build(*sys.argv[1:3])
