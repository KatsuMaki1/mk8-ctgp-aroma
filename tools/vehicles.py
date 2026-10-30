"""Inspect and stage supplied vehicle models; never replace native kart parts.

Staging does not add roulette slots. Runtime registration is a separate step.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import zipfile
import costumes

SPEEDER_COLORS = ('Blue', 'Flaming', 'Green', 'Holiday', 'Pink')

def collect(base, speeder, silver, color='Blue'):
    if color not in SPEEDER_COLORS: raise ValueError('Unknown Speeder color')
    base = Path(base)
    if not Path(speeder).is_file() or not Path(silver).is_file(): raise ValueError('Missing mod archive')
    resources = {}
    with zipfile.ZipFile(speeder) as archive:
        for rel in ('kart/body/BodyK_Wld.szs', 'kart/tire/TireK_Slk.szs'):
            resources['Speeder8/'+color+'/'+rel] = archive.read('Speeder 8/'+color+' Speeder/content/'+rel)
    extractor = Path(r'C:\Program Files\7-Zip\7z.exe')
    if not extractor.is_file(): raise ValueError('7-Zip is required to read the supplied RAR')
    # Extract only the three known resources, never archive-provided scripts.
    with tempfile.TemporaryDirectory(prefix='mk8-silver-monster-') as tmp:
        for kind in ('B','K','T'):
            member='silver monster/content/kart/tire/Tire'+kind+'_Zbi.szs'
            subprocess.run([str(extractor),'x',str(Path(silver).resolve()),member,'-o'+tmp,'-y'],check=True,capture_output=True)
            resources['SilverMonster/kart/tire/Tire'+kind+'_Zbi.szs']=(Path(tmp)/member).read_bytes()
    report = {'format':'mk8-vehicle-assets-v1', 'runtime_status':'staged-only-no-roulette-patch',
              'archives':{str(Path(p).resolve()):hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in (speeder,silver)},
              'choices':{'body':{'name':'Speeder 8','color':color,'base_id':7},
                         'tire':{'name':'Silver Monster','base_id':12}},
              'resources':{}, 'icons_provided':False,
              'note':'Speeder matching slick tire is staged separately; it does not replace Silver Monster or native tires.'}
    for name,payload in resources.items():
        rel='kart/'+name.split('/kart/',1)[1]
        metadata=costumes.inspect_model(payload)
        original=costumes.inspect_model((base/rel).read_bytes())
        if metadata['models'] != original['models']: raise ValueError('Unexpected model names: '+name)
        missing=set(original['skeletal_animations'])-set(metadata['skeletal_animations'])
        report['resources'][name]={'sha256':hashlib.sha256(payload).hexdigest(),'bytes':len(payload),
                                   'models':metadata['models'],'missing_original_animations':sorted(missing)}
    return resources,report

def stage(base,content,speeder,silver,color='Blue'):
    resources,report=collect(base,speeder,silver,color)
    root=Path(content)/'custom/vehicles'
    manifest=(json.dumps(report,indent=2)+'\n').encode()
    writes={root/n:d for n,d in resources.items()}
    writes[root/'manifest.json']=manifest
    for p,d in writes.items():
        if p.exists() and p.read_bytes()!=d: raise ValueError('Existing staged asset differs; preserved: '+str(p))
    for p,d in writes.items(): costumes.atomic_write(p,d)
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=('inspect','stage'))
    p.add_argument('--base',required=True);p.add_argument('--content')
    p.add_argument('--speeder',required=True);p.add_argument('--silver',required=True)
    p.add_argument('--color',choices=SPEEDER_COLORS,default='Blue')
    a=p.parse_args()
    if a.command=='stage':
        if not a.content: p.error('stage requires --content')
        result=stage(a.base,a.content,a.speeder,a.silver,a.color)
    else: _,result=collect(a.base,a.speeder,a.silver,a.color)
    print(json.dumps(result,indent=2))
