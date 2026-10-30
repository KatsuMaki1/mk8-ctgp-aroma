"""Build a guarded EUR81 online-vote test overlay from the existing R4 pack."""
import argparse,json,struct,tempfile,shutil
from pathlib import Path
import costume_patch as patch
import game_options as native
import retarget
import rpxlib
from mkpack import parse_hax,write_hax

MARKER=b'MK8_ONLINE_SYNC_EUR81_V1'
NATIVE={'vote':(0x02412220,0x9421ffd8),'preview':(0x025a9870,0x7c0802a6),
        'update':(0x025ffb84,0x9421ffd0),'error':(0x02a3f33c,0x4e800020)}
INTERNAL={'winner':(0x5f48,0x9421ffc0),'receive':(0x6a00,0x9421ffd8)}

def cemu(source,output):
    raw,sections=rpxlib.load(source)
    code=next(s for s in sections if s['addr']==0x02b10000)
    data=next(s for s in sections if s['addr']==0x10300000)
    info=next(s for s in sections if s['t']==0x80000004)
    if MARKER in code['data']:raise ValueError('Already patched')
    code_base,data_base=0x02b1e000,0x10307000
    if code['addr']+len(code['data'])>code_base or data['addr']+len(data['data'])>data_base:raise ValueError('Module overlaps existing state')
    for n,(a,w) in NATIVE.items():
        if rpxlib.word_at(sections,a)!=w:raise ValueError('Wrong native hook '+n)
    for n,(o,w) in INTERNAL.items():
        if struct.unpack_from('>I',code['data'],o)[0]!=w:raise ValueError('Wrong blob hook '+n)
    relocs={a for s in sections if s['name']=='.rela.text' for a,_,_ in struct.iter_unpack('>III',s['data'])}
    patch.check_relocation_overlap([a for a,w in NATIVE.values()],relocs)
    hooks={**NATIVE,'receive':(code['addr']+INTERNAL['receive'][0],INTERNAL['receive'][1])}
    with tempfile.TemporaryDirectory() as tmp:
        text,mutable,symbols=native.compile_module(Path(tmp),code_address=code_base,data_address=data_base,
            hooks=hooks,source=Path(__file__).parent/'native/online_sync.c')
    if code_base+len(text)>0x02000000+struct.unpack_from('>I',info['data'],4)[0]:raise ValueError('Text reservation too small')
    for n,(a,w) in NATIVE.items():
        section=next(s for s in sections if s['t']==1 and s['addr']<=a<s['addr']+len(s['data']))
        payload=bytearray(section['data']);struct.pack_into('>I',payload,a-section['addr'],patch.branch(a,symbols['online_'+n]));section['data']=bytes(payload)
    updated=bytearray(code['data'])
    for n,(o,w) in INTERNAL.items():struct.pack_into('>I',updated,o,patch.branch(code['addr']+o,symbols['online_'+n]))
    code['data']=bytes(updated)+bytes(code_base-code['addr']-len(updated))+text
    data['data']+=bytes(data_base-data['addr']-len(data['data']))+mutable
    fi=bytearray(info['data']);struct.pack_into('>I',fi,12,max(struct.unpack_from('>I',fi,12)[0],((data_base+len(mutable)+255)&~255)-0x10000000));info['data']=bytes(fi)
    result=patch.repack(raw,sections);Path(output).write_bytes(result)
    _,check=rpxlib.load(output)
    for s in sections:
        if s['t']!=0x80000003 and s['data']!=next(t['data'] for t in check if t['i']==s['i']):raise ValueError('RPX readback mismatch')
    Path(str(output)+'.json').write_text(json.dumps({'source_sha256':patch.digest(raw),'output_sha256':patch.digest(result),'symbols':symbols},indent=2)+'\n')
    return symbols

def build(pack,stock_text,output):
    pack,stock_text,output=map(Path,(pack,stock_text,output))
    if output.exists():raise ValueError('Use a new output folder')
    features=json.loads((pack/'Features.json').read_text())
    for n,h in features['files'].items():
        if patch.digest((pack/n).read_bytes())!=h:raise ValueError('Baseline hash differs: '+n)
    code=(pack/'Code.bin').read_bytes();data=(pack/'Data.bin').read_bytes()
    if MARKER in code:raise ValueError('Online module already installed')
    if struct.unpack('>II',(pack/'Addr.bin').read_bytes())!=(retarget.CB,retarget.DB):raise ValueError('Unknown layout')
    if data[0x17dc:0x17e8]!=b'custom/cup0\0':raise ValueError('Requires private CUP0 alias')
    stock=stock_text.read_bytes()
    for n,(a,w) in NATIVE.items():
        if struct.unpack_from('>I',stock,a-0x02000020)[0]!=w:raise ValueError('Wrong native hook '+n)
    for n,(o,w) in INTERNAL.items():
        if struct.unpack_from('>I',code,o)[0]!=w:raise ValueError('Wrong blob hook '+n)
    patches=parse_hax((pack/'Patches.hax').read_bytes());verify=parse_hax((pack/'Verify.hax').read_bytes())
    if [a for a,d in patches]!=[a for a,d in verify]:raise ValueError('Verification coverage differs')
    code_offset=(len(code)+4095)&~4095;data_offset=(len(data)+4095)&~4095
    hooks={n:(a+retarget.GT_SHIFT,w) for n,(a,w) in NATIVE.items()}
    hooks['receive']=(retarget.CB+INTERNAL['receive'][0],INTERNAL['receive'][1])
    cflags=['-DGAME_TEXT_SHIFT=0x%xu'%retarget.GT_SHIFT,
            '-DGAME_DATA_SHIFT=0x%xu'%retarget.GD_SHIFT,
            '-DCTGP_CODE_BASE=0x%xu'%retarget.CB,'-DCTGP_DATA_BASE=0x10400000u']
    with tempfile.TemporaryDirectory() as tmp:
        text,mutable,symbols=native.compile_module(Path(tmp),
            code_address=retarget.CB+code_offset,data_address=retarget.DB+data_offset,
            hooks=hooks,source=Path(__file__).parent/'native/online_sync.c',cflags=cflags)
    updated=bytearray(code)
    for n,(o,w) in INTERNAL.items():
        struct.pack_into('>I',updated,o,patch.branch(retarget.CB+o,symbols['online_'+n]))
    for n,(a,w) in NATIVE.items():
        at=a+retarget.GT_SHIFT
        if any(at<x+len(d) and x<at+4 for x,d in patches):raise ValueError('Existing hook conflict '+n)
        patches.append((at,struct.pack('>I',patch.branch(at,symbols['online_'+n]))))
        verify.append((at,struct.pack('>I',w)))
    code=bytes(updated)+bytes(code_offset-len(code))+text
    code+=bytes(-len(code)%4)+struct.pack('>I',0x4e800020)
    data+=bytes(data_offset-len(data))+mutable
    target=output/'sd/cafeloader/000500001010ED00';target.mkdir(parents=True)
    shutil.copy2(pack/'Addr.bin',target/'Addr.bin')
    (target/'Code.bin').write_bytes(code);(target/'Data.bin').write_bytes(data)
    (target/'Patches.hax').write_bytes(write_hax(patches));(target/'Verify.hax').write_bytes(write_hax(verify))
    features['features'].append('Online vote page publication, exact CUP0 slot and custom previews (test)')
    features['console_tested']=False
    features['online_sync']={'symbols':symbols,'two_console_test_pending':True}
    features['files']={n:patch.digest((target/n).read_bytes()) for n in features['files']}
    (target/'Features.json').write_text(json.dumps(features,indent=2)+'\n')
    rollback=output/'rollback/sd/cafeloader/000500001010ED00';rollback.mkdir(parents=True)
    for p in pack.iterdir():
        if p.is_file():shutil.copy2(p,rollback/p.name)
    for n,h in features['files'].items():
        if patch.digest((target/n).read_bytes())!=h:raise ValueError('Output hash mismatch')
    if not code.endswith(b'\x4e\x80\x00\x20'):raise ValueError('Missing logger stub')
    if len(parse_hax((target/'Patches.hax').read_bytes()))!=len(verify):raise ValueError('Output coverage mismatch')
    manifest={'kind':'Online private-room synchronization candidate','console_tested':False,
              'native_hooks':len(NATIVE),'symbols':symbols,'files':{p.relative_to(output/'sd').as_posix():patch.digest(p.read_bytes()) for p in target.iterdir()}}
    (output/'Verification.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (output/'LIRE_MOI.txt').write_text(
        'CTGP AROMA - ONLINE TEST - EUR v81\n\n'
        'Ferme MK8 sur les DEUX Wii U. Sauvegarde ta SD puis copie le contenu de sd a la racine des deux SD, en remplacant les six fichiers du pack code. Meme pack de circuits requis des deux cotes. Garde le plugin Aroma v0.20 et Online CTGP sur ON.\n\n'
        'Ce candidat publie la page CTGP lors du vote natif, corrige le choix du slot 0..3 et utilise les images CTGP dans la roulette de vote. Il conserve les ressources et le correctif Golden Dash R4 deja installes. Aucun bouton Speedometer ON/OFF ni drift rose ajoute.\n\n'
        'TEST REQUIS : partie privee entre deux Wii U. Tester un circuit personnalise en position 0 puis un autre en position 1, 2 ou 3; comparer les images du vote et le circuit charge des deux cotes. Echanger ensuite l hote. Aucun test reseau reel effectue ici : ce paquet est un candidat, pas un correctif console confirme.\n\n'
        'Retour arriere : copie le contenu de rollback/sd a la racine des deux SD.\n',encoding='utf-8')
    return manifest

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--pack',required=True);p.add_argument('--stock-text',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();print(json.dumps(build(a.pack,a.stock_text,a.output),indent=2))
