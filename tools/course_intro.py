"""Append the custom course-name/series message override for the race banner."""
from pathlib import Path
import json,struct,tempfile
import rpxlib,costume_patch as patch,game_options
HOOKS=(0x026273e4,0x02627404)

def build(source,formatter_meta,output):
    raw,ss=rpxlib.load(source)
    code=next(s for s in ss if s['addr']==0x02b10000)
    data=next(s for s in ss if s['addr']==0x10300000)
    if b'MK8_CUSTOM_COURSE_INTRO_V1' in code['data']:raise ValueError('Already patched')
    for a in HOOKS:
        if rpxlib.word_at(ss,a)!=(patch.branch(a,0x025367e8)|1):raise ValueError('Unknown course banner call')
    cb=(code['addr']+len(code['data'])+4095)&~4095;db=(data['addr']+len(data['data'])+4095)&~4095
    path=json.loads(Path(formatter_meta).read_text())['symbols']['dlc_current_course']
    with tempfile.TemporaryDirectory() as temp:
        text,mutable,symbols=game_options.compile_module(Path(temp),code_address=cb,data_address=db,hooks={},source=Path(__file__).parent/'native/course_intro.c',cflags=(f'-DCOURSE_PATH=0x{path:x}u',))
    code['data']+=bytes(cb-code['addr']-len(code['data']))+text
    data['data']+=bytes(db-data['addr']-len(data['data']))+mutable
    for a in HOOKS:
        s=next(s for s in ss if s['addr']<=a<s['addr']+len(s['data']))
        b=bytearray(s['data']);struct.pack_into('>I',b,a-s['addr'],patch.branch(a,symbols['course_intro'])|1);s['data']=bytes(b)
    info=next(s for s in ss if s['t']==0x80000004);b=bytearray(info['data'])
    for off,end,base in [(4,cb+len(text),0x02000000),(12,db+len(mutable),0x10000000)]:struct.pack_into('>I',b,off,max(struct.unpack_from('>I',b,off)[0],((end+255)&~255)-base))
    info['data']=bytes(b);result=patch.repack(raw,ss);Path(output).write_bytes(result)
    _,check=rpxlib.load(output)
    for s in ss:
        if s['t']!=0x80000003:assert s['data']==next(x['data'] for x in check if x['i']==s['i'])
    meta={'source_sha256':patch.digest(raw),'output_sha256':patch.digest(result),'symbols':symbols,'hooks':[hex(a) for a in HOOKS],'course_path':hex(path),'runtime_tested':False}
    Path(str(output)+'.json').write_text(json.dumps(meta,indent=2)+'\n');return meta
