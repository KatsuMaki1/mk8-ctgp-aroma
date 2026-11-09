"""Normalize input strings before entering older chained asset routers."""
from pathlib import Path
import json,struct,tempfile
import rpxlib,costume_patch as patch,game_options

def build(source,manifest,output):
    raw,sections=rpxlib.load(source);assets=json.loads(Path(manifest).read_text())['scoped_assets']
    code=next(s for s in sections if s['addr']==0x02b10000);data=next(s for s in sections if s['addr']==0x10300000)
    info=next(s for s in sections if s['t']==0x80000004)
    if b'MK8_FORMATTER_PLAIN_STRINGS_V1' in code['data']:raise ValueError('Already scoped')
    cb=(code['addr']+len(code['data'])+4095)&~4095;db=(data['addr']+len(data['data'])+4095)&~4095
    original=[];addresses=(0x0272c02c,0x0272c240,0x0272c8fc)
    for a in addresses:
        w=rpxlib.word_at(sections,a)
        if w is None or w&0xfc000003!=0x48000000:raise ValueError('Expected existing relative formatter hook')
        dest=a+(w&0x3fffffc)-(0x4000000 if w&0x2000000 else 0)
        if not code['addr']<=dest<code['addr']+len(code['data']):raise ValueError('Unknown formatter destination')
        original.append(dest)
    header='static const struct {unsigned int hash;const char *path;} bcp_assets[]={\n'
    for name in assets:
        h=2166136261
        for c in name.encode():h=((h^c)*16777619)&0xffffffff
        header+='{0x%08xu,%s},\n'%(h,json.dumps(name))
    header+='};\n'
    with tempfile.TemporaryDirectory() as tmp:
        folder=Path(tmp);(folder/'booster_asset_list.h').write_text(header)
        text,mutable,symbols=game_options.compile_module(folder,code_address=cb,data_address=db,hooks={},source=Path(__file__).parent/'native/formatter_strings.c',cflags=('-I'+str(folder),*[f'-DBCP_ORIGINAL{i}=0x{v:x}u' for i,v in enumerate(original)]))
    code['data']+=bytes(cb-code['addr']-len(code['data']))+text
    data['data']+=bytes(db-data['addr']-len(data['data']))+mutable
    for i,a in enumerate(addresses):
        section=next(s for s in sections if s['addr']<=a<s['addr']+len(s['data']))
        b=bytearray(section['data']);struct.pack_into('>I',b,a-section['addr'],patch.branch(a,symbols[f'bcp_format{i}']));section['data']=bytes(b)
    b=bytearray(info['data'])
    for offset,end,start in ((4,cb+len(text),0x02000000),(12,db+len(mutable),0x10000000)):
        struct.pack_into('>I',b,offset,max(struct.unpack_from('>I',b,offset)[0],((end+255)&~255)-start))
    info['data']=bytes(b);result=patch.repack(raw,sections);Path(output).write_bytes(result)
    _,checked=rpxlib.load(output)
    for s in sections:
        if s['t']!=0x80000003 and next(x for x in checked if x['i']==s['i'])['data']!=s['data']:raise ValueError('RPX readback mismatch')
    report={'source_sha256':patch.digest(raw),'output_sha256':patch.digest(result),'symbols':symbols,'previous_formatters':original,'assets':len(assets),'code_address':cb,'data_address':db,'runtime_tested':False}
    Path(str(output)+'.json').write_text(json.dumps(report,indent=2)+'\n');Path(str(output)+'.h').write_text(header)
    return report
