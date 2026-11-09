"""Append a guarded adapter for the native 37-character sound-group loader."""
from pathlib import Path
import json,struct,tempfile
import rpxlib,costume_patch as patch,game_options
HOOK=0x0202c438

def build(source,output):
    raw,ss=rpxlib.load(source)
    if rpxlib.word_at(ss,HOOK)!=0x7c0802a6:raise ValueError('Unknown audio group entry')
    code=next(s for s in ss if s['addr']==0x02b10000)
    data=next(s for s in ss if s['addr']==0x10300000)
    if b'MK8_ROB_NATIVE_GROUP_ALIAS_V1' in code['data']:raise ValueError('Already patched')
    relocs={a for s in ss if s['name']=='.rela.text' for a,b,c in struct.iter_unpack('>III',s['data'])}
    patch.check_relocation_overlap([HOOK],relocs)
    cb=(code['addr']+len(code['data'])+4095)&~4095
    db=(data['addr']+len(data['data'])+4095)&~4095
    with tempfile.TemporaryDirectory() as tmp:
        text,mutable,symbols=game_options.compile_module(Path(tmp),code_address=cb,data_address=db,hooks={'audio_groups':(HOOK,0x7c0802a6)},source=Path(__file__).parent/'native/rob_audio_groups.c')
    code['data']+=bytes(cb-code['addr']-len(code['data']))+text
    data['data']+=bytes(db-data['addr']-len(data['data']))+mutable
    section=next(s for s in ss if s['addr']<=HOOK<s['addr']+len(s['data']))
    b=bytearray(section['data']);struct.pack_into('>I',b,HOOK-section['addr'],patch.branch(HOOK,symbols['rob_audio_groups']));section['data']=bytes(b)
    info=next(s for s in ss if s['t']==0x80000004);b=bytearray(info['data'])
    for off,end,base in [(4,cb+len(text),0x02000000),(12,db+len(mutable),0x10000000)]:struct.pack_into('>I',b,off,max(struct.unpack_from('>I',b,off)[0],((end+255)&~255)-base))
    info['data']=bytes(b);out=Path(output);out.parent.mkdir(parents=True,exist_ok=True);result=patch.repack(raw,ss);out.write_bytes(result)
    _,check=rpxlib.load(out)
    for s in ss:
        if s['t']!=0x80000003:assert s['data']==next(x['data'] for x in check if x['i']==s['i'])
    meta={'source_sha256':patch.digest(raw),'output_sha256':patch.digest(result),'symbols':symbols,'runtime_tested':False,'hook':hex(HOOK)}
    Path(str(out)+'.json').write_text(json.dumps(meta,indent=2)+'\n');return meta
