"""Append private Boltthunder4 object routing to existing EUR81 payloads."""
from pathlib import Path
import json,struct,tempfile,shutil,argparse
import costume_patch as patch,game_options as native,rpxlib,retarget
from mkpack import parse_hax,write_hax
SOURCE=Path(__file__).parent/'native/bolt_assets.c'
MARKER=b'MK8_BOLT_ASSET_SCOPE_V1'
FORMATS={'bolt0':(0x0272c02c,0x7c0802a6),'bolt1':(0x0272c240,0x9421fd88),'bolt2':(0x0272c8fc,0x7c0802a6)}
def cemu(source,options_manifest,output):
    raw,sections=rpxlib.load(source)
    code=next(s for s in sections if s['addr']==0x02b10000)
    data=next(s for s in sections if s['addr']==0x10300000)
    info=next(s for s in sections if s['t']==0x80000004)
    if MARKER in code['data']:raise ValueError('Asset scope already installed')
    opts=json.loads(Path(options_manifest).read_text())['symbols']
    hooks={f'bolt{i}':(opts[f'options_format{i}'],0x9421ffe0) for i in range(3)}
    for n,(a,w) in hooks.items():
        if rpxlib.word_at(sections,a)!=w:raise ValueError('Unknown existing Cemu format hook '+n)
    cb,db=0x02b20000,0x10308000
    if code['addr']+len(code['data'])>cb or data['addr']+len(data['data'])>db:raise ValueError('Module reservation overlaps existing payload')
    with tempfile.TemporaryDirectory() as tmp:
        text,mutable,symbols=native.compile_module(Path(tmp),code_address=cb,data_address=db,hooks=hooks,source=SOURCE)
    if cb+len(text)>0x02c00000:raise ValueError('Code exceeds local text limit')
    updated=bytearray(code['data'])
    for n,(a,w) in hooks.items():struct.pack_into('>I',updated,a-code['addr'],patch.branch(a,symbols['bolt_format'+n[-1]]))
    code['data']=bytes(updated)+bytes(cb-code['addr']-len(updated))+text
    data['data']+=bytes(db-data['addr']-len(data['data']))+mutable
    fi=bytearray(info['data']);struct.pack_into('>I',fi,4,max(struct.unpack_from('>I',fi,4)[0],((cb+len(text)+255)&~255)-0x02000000));struct.pack_into('>I',fi,12,max(struct.unpack_from('>I',fi,12)[0],((db+len(mutable)+255)&~255)-0x10000000));info['data']=bytes(fi)
    result=patch.repack(raw,sections);Path(output).write_bytes(result)
    _,check=rpxlib.load(output)
    for s in sections:
        if s['t']!=0x80000003 and s['data']!=next(t['data'] for t in check if t['i']==s['i']):raise ValueError('RPX readback mismatch')
    manifest={'source_sha256':patch.digest(raw),'output_sha256':patch.digest(result),'symbols':symbols,'chained_existing_format_hooks':hooks}
    Path(str(output)+'.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest
def console(pack,output):
    pack,output=Path(pack),Path(output)
    features=json.loads((pack/'Features.json').read_text())
    for n,h in features['files'].items():
        if patch.digest((pack/n).read_bytes())!=h:raise ValueError('Baseline pack changed '+n)
    code=(pack/'Code.bin').read_bytes();data=(pack/'Data.bin').read_bytes()
    if MARKER in code:raise ValueError('Already installed')
    patches=parse_hax((pack/'Patches.hax').read_bytes());verify=parse_hax((pack/'Verify.hax').read_bytes())
    if [a for a,b in patches]!=[a for a,b in verify]:raise ValueError('Verification coverage mismatch')
    hooks={n:(a+retarget.GT_SHIFT,w) for n,(a,w) in FORMATS.items()}
    for a,w in hooks.values():
        if any(a<x+len(b) and x<a+4 for x,b in patches):raise ValueError('Native format hook conflict')
    co=(len(code)+4095)&~4095;do=(len(data)+4095)&~4095
    with tempfile.TemporaryDirectory() as tmp:
        text,mutable,symbols=native.compile_module(Path(tmp),code_address=retarget.CB+co,data_address=retarget.DB+do,hooks=hooks,source=SOURCE)
    code+=bytes(co-len(code))+text;code+=bytes(-len(code)%4)+struct.pack('>I',0x4e800020)
    data+=bytes(do-len(data))+mutable
    for n,(a,w) in hooks.items():
        patches.append((a,struct.pack('>I',patch.branch(a,symbols['bolt_format'+n[-1]]))))
        verify.append((a,struct.pack('>I',w)))
    output.mkdir(parents=True,exist_ok=False)
    shutil.copy2(pack/'Addr.bin',output/'Addr.bin')
    (output/'Code.bin').write_bytes(code);(output/'Data.bin').write_bytes(data)
    (output/'Patches.hax').write_bytes(write_hax(patches));(output/'Verify.hax').write_bytes(write_hax(verify))
    features['features'].append('Scoped object assets for 48 additional Boltthunder4 courses')
    features['bolt_assets']={'symbols':symbols,'private_prefix':'custom/bolt_assets/','console_tested':False}
    features['files']={n:patch.digest((output/n).read_bytes()) for n in features['files']}
    (output/'Features.json').write_text(json.dumps(features,indent=2)+'\n')
    assert code.endswith(b'\x4e\x80\x00\x20')
    return {'symbols':symbols,'patch_count':len(patches),'console_tested':False}
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['cemu','console']);p.add_argument('--source',required=True);p.add_argument('--options');p.add_argument('--output',required=True);a=p.parse_args()
    print(json.dumps(cemu(a.source,a.options,a.output) if a.command=='cemu' else console(a.source,a.output),indent=2))
