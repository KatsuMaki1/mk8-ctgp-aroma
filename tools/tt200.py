"""Build a sandbox-only 150/200cc TT selector. Save separation is not ported yet."""
from pathlib import Path
import struct,json,tempfile
import rpxlib,costume_patch as patch,game_options
HOOKS={'tt_class_calc':(0x025ea5b0,0x7c0802a6),'tt_race_copy':(0x024f9f0c,0x7c0802a6),'tt_mode':(0x025e8114,0x7c0802a6),'tt_class_in':(0x025e9eac,0x7c0802a6),'tt_class_event':(0x025ea994,0x7c0802a6)}
def build(source,output):
    raw,sections=rpxlib.load(source);code=next(s for s in sections if s['addr']==0x02b10000);data=next(s for s in sections if s['addr']==0x10300000);info=next(s for s in sections if s['t']==0x80000004)
    if b'MK8_TT200_SANDBOX_P1' in code['data']:raise ValueError('Already patched')
    if rpxlib.word_at(sections,0x02616a78)!=0x93fa0164:raise ValueError('Unexpected TT engine store')
    for name,(a,w) in HOOKS.items():
        if rpxlib.word_at(sections,a)!=w:raise ValueError('Unexpected hook prologue '+name)
    relocations={a for s in sections if s['name']=='.rela.text' for a,b,c in struct.iter_unpack('>III',s['data'])};patch.check_relocation_overlap([a for a,w in HOOKS.values()]+[0x02616a78],relocations)
    cb=(code['addr']+len(code['data'])+4095)&~4095;db=(data['addr']+len(data['data'])+4095)&~4095
    with tempfile.TemporaryDirectory() as tmp:
        text,mutable,symbols=game_options.compile_module(Path(tmp),code_address=cb,data_address=db,hooks=HOOKS,source=Path(__file__).parent/'native/tt200.c',cflags=('-Wl,--defsym,tt200_rule_return=0x02616a7c',))
    code['data']+=bytes(cb-code['addr']-len(code['data']))+text;data['data']+=bytes(db-data['addr']-len(data['data']))+mutable
    for name,(a,w) in HOOKS.items():
        s=next(x for x in sections if x['addr']<=a<x['addr']+len(x['data']));b=bytearray(s['data']);struct.pack_into('>I',b,a-s['addr'],patch.branch(a,symbols[name.replace('tt_','tt200_')]));s['data']=bytes(b)
    section=next(x for x in sections if x['addr']<=0x02616a78<x['addr']+len(x['data']));b=bytearray(section['data']);struct.pack_into('>I',b,0x02616a78-section['addr'],patch.branch(0x02616a78,symbols['tt200_tt_rule_store']));section['data']=bytes(b)
    b=bytearray(info['data'])
    for at,end,base in ((4,cb+len(text),0x02000000),(12,db+len(mutable),0x10000000)):struct.pack_into('>I',b,at,max(struct.unpack_from('>I',b,at)[0],((end+255)&~255)-base))
    info['data']=bytes(b);out=Path(output);out.parent.mkdir(parents=True,exist_ok=True);result=patch.repack(raw,sections);out.write_bytes(result)
    _,check=rpxlib.load(out)
    for s in sections:
        if s['t']!=0x80000003 and next(x['data'] for x in check if x['i']==s['i'])!=s['data']:raise ValueError('RPX roundtrip failed')
    report={'source_sha256':patch.digest(raw),'output_sha256':patch.digest(result),'symbols':symbols,'hooks':HOOKS,'sandbox_only':True,'native_150_save_isolation_implemented':False,'runtime_tested':False}
    Path(str(out)+'.json').write_text(json.dumps(report,indent=2)+'\n');return report
