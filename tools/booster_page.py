"""Patch CTGP's Booster-page gate while retaining the existing Aroma loader."""
import argparse,json,shutil,struct,tempfile
from pathlib import Path
import costume_patch as patch
import game_options as native
import rpxlib,retarget,cup0

MARKER=b'MK8_BOOSTER_GATE_EUR81_V1'
OFFSET=0x3f1c
SOURCE=Path(__file__).parent/'native/booster_gate.c'
EXPECTED=0x7c0802a6

def module(code,data,entry,console):
    state=0x10402564 if console else 0x10302564
    with tempfile.TemporaryDirectory() as tmp:
        return native.compile_module(Path(tmp),code_address=code,data_address=data,
            hooks={'gate':(entry,EXPECTED)},source=SOURCE,cflags=['-DCUP_STATE=0x%xu'%state])

def cemu(source,output):
    raw,sections=rpxlib.load(source)
    code=next(s for s in sections if s['addr']==0x02b10000)
    data=next(s for s in sections if s['addr']==0x10300000)
    info=next(s for s in sections if s['t']==0x80000004)
    if MARKER in code['data']:raise ValueError('Booster gate already installed')
    entry=code['addr']+OFFSET
    if rpxlib.word_at(sections,entry)!=EXPECTED:raise ValueError('Unknown CTGP gate')
    code_address,data_address=0x02b1d000,0x10306000
    if code['addr']+len(code['data'])>code_address or data['addr']+len(data['data'])>data_address:raise ValueError('Payload overlap')
    text,mutable,symbols=module(code_address,data_address,entry,False)
    if code_address+len(text)>0x02000000+struct.unpack_from('>I',info['data'],4)[0]:raise ValueError('Text allocation too small')
    updated=bytearray(code['data']);struct.pack_into('>I',updated,OFFSET,patch.branch(entry,symbols['booster_gate']))
    code['data']=bytes(updated)+bytes(code_address-code['addr']-len(updated))+text
    data['data']+=bytes(data_address-data['addr']-len(data['data']))+mutable
    fileinfo=bytearray(info['data']);struct.pack_into('>I',fileinfo,12,max(struct.unpack_from('>I',fileinfo,12)[0],((data_address+len(mutable)+255)&~255)-0x10000000));info['data']=bytes(fileinfo)
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True);result=patch.repack(raw,sections);output.write_bytes(result)
    _,check=rpxlib.load(output)
    for s in sections:
        if s['t']!=0x80000003 and s['data']!=next(t['data'] for t in check if t['i']==s['i']):raise ValueError('RPX readback mismatch')
    manifest={'source_sha256':patch.digest(raw),'output_sha256':patch.digest(result),'symbols':symbols}
    Path(str(output)+'.json').write_text(json.dumps(manifest,indent=2)+'\n');return manifest

def console(pack,content,output):
    pack,content,output=map(Path,(pack,content,output))
    if output.exists():raise ValueError('Use a new output folder')
    features=json.loads((pack/'Features.json').read_text())
    for n,h in features['files'].items():
        if patch.digest((pack/n).read_bytes())!=h:raise ValueError('Baseline pack changed: '+n)
    code=(pack/'Code.bin').read_bytes();data=(pack/'Data.bin').read_bytes()
    if MARKER in code or struct.unpack_from('>I',code,OFFSET)[0]!=EXPECTED:raise ValueError('Unknown/already patched CTGP gate')
    if data[0x17dc:0x17e8]!=b'custom/cup0\0':raise ValueError('Requires validated v0.20 private CUP0 path')
    code_offset=(len(code)+4095)&~4095;data_offset=(len(data)+4095)&~4095
    text,mutable,symbols=module(retarget.CB+code_offset,retarget.DB+data_offset,retarget.CB+OFFSET,True)
    code=bytearray(code);struct.pack_into('>I',code,OFFSET,patch.branch(retarget.CB+OFFSET,symbols['booster_gate']))
    code=bytes(code)+bytes(code_offset-len(code))+text
    code+=bytes(-len(code)%4)+struct.pack('>I',0x4e800020)
    data+=bytes(data_offset-len(data))+mutable
    sd=output/'sd';target=sd/'cafeloader/000500001010ED00';target.mkdir(parents=True)
    for n in ('Addr.bin','Patches.hax','Verify.hax'):shutil.copy2(pack/n,target/n)
    (target/'Code.bin').write_bytes(code);(target/'Data.bin').write_bytes(data)
    features['features'].append('Playable imported Booster cups on original page')
    features['console_tested']=False
    features['booster_gate']={'entry':retarget.CB+OFFSET,'target':symbols['booster_gate'],'requires_four_custom_courses':True}
    features['files']={n:patch.digest((target/n).read_bytes()) for n in features['files']}
    (target/'Features.json').write_text(json.dumps(features,indent=2)+'\n')
    cups=cup0.parse((content/'data.cup0').read_bytes());golden=next(c for c in cups if c.name=='Golden Dash Cup')
    if golden.type!=4 or golden.icon!=0 or any(t.dir=='Ginvalid' for t in golden.tracks):raise ValueError('Expected complete R2 Golden cup')
    golden.type=1;golden.icon=0
    payload=cup0.build(cups);dst=sd/'cafeloader/vol/000500001010ED00/content';(dst/'custom').mkdir(parents=True);(dst/'data').mkdir()
    (dst/'data.cup0').write_bytes(payload);(dst/'custom/cup0').write_bytes(payload)
    shutil.copy2(content/'data/objflow.byaml',dst/'data/objflow.byaml')
    (output/'LIRE_MOI.txt').write_text('GOLDEN DASH - selection sur la page Booster R3\n\nPour le pack Golden Dash deja installe (R1+R2). Jeu ferme, copie le CONTENU de sd a la racine SD et remplace les fichiers. Garde ton plugin Aroma v0.20.\n\nGolden Dash retrouve sa premiere case sur la page Booster, avec Paris Promenade, Toad Circuit, Choco Mountain, Coconut Mall. La page type4 du contournement est retiree de la liste de coupes. Le correctif autorise les boutons de coupe/circuit uniquement pour les coupes Booster ayant quatre vrais dossiers de circuits. Les autres coupes restent a remplir.\n\nCode.bin et Data.bin contiennent uniquement ce nouveau correctif, en plus du pack precedent : aucun bouton Speedometer ON/OFF, aucun drift rose, aucun nouveau plugin. La table objets R2 est incluse.\n\nValidation en cours : voir Verification.json.\n',encoding='utf-8')
    manifest={'kind':'Golden Dash original Booster page R3','console_tested':False,'cemu_tested':False,'files':{p.relative_to(sd).as_posix():patch.digest(p.read_bytes()) for p in sd.rglob('*') if p.is_file()},'symbols':symbols}
    (output/'Verification.json').write_text(json.dumps(manifest,indent=2)+'\n');print(output)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['cemu','console']);p.add_argument('--source');p.add_argument('--pack');p.add_argument('--content');p.add_argument('--output',required=True);a=p.parse_args()
    if a.command=='cemu':cemu(a.source,a.output)
    else:console(a.pack,a.content,a.output)
