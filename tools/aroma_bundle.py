"""Bundle a private, user-supplied Cemu content snapshot with an Aroma pack."""
import argparse,hashlib,json,shutil,zipfile
from pathlib import Path

DIRS=('course','mapobj','ui','custom','charger','audio','common','driver','kart',
      'driver_anim','driver_tex','race_common','ui3d','trophy','ghost','data')

def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def bundle(content,plugin,output,archive=None,refresh_generated=False):
    content,plugin,output=map(lambda p:Path(p).resolve(),(content,plugin,output))
    if output==content or content in output.parents or output in content.parents:raise ValueError('Keep the bundle outside game content')
    sd=output/'sd';pack=sd/'cafeloader/000500001010ED00'
    features=json.loads((pack/'Features.json').read_text())
    for n,sha in features['files'].items():
        if digest(pack/n)!=sha:raise ValueError('Console pack changed: '+n)
    target=sd/'cafeloader/vol/000500001010ED00/content'
    previous={}
    if refresh_generated and (output/'Content-manifest.json').exists():
        previous=json.loads((output/'Content-manifest.json').read_text()).get('content',{})
    sources=[p for d in DIRS for p in (content/d).rglob('*') if p.is_file()
             and p.suffix.lower() not in ('.bak','.json') and '.bak.' not in p.name]
    sources += [content/'data.cup0']
    destinations=[(src,src.relative_to(content)) for src in sources
                  if src.relative_to(content).as_posix()!='custom/cup0']
    destinations.append((content/'data.cup0',Path('custom/cup0')))
    inventory={}
    for i,(src,rel) in enumerate(destinations):
        dst=target/rel;sha=digest(src)
        changed=dst.exists() and digest(dst)!=sha
        if changed and (not refresh_generated or previous.get(rel.as_posix(),{}).get('sha256')!=digest(dst)):
            raise ValueError('Conflicting generated content: '+str(dst))
        dst.parent.mkdir(parents=True,exist_ok=True)
        if not dst.exists() or changed:shutil.copy2(src,dst)
        if digest(dst)!=sha:raise ValueError('Content copy failed: '+str(rel))
        inventory[rel.as_posix()]={'sha256':sha,'size':src.stat().st_size}
        if i%200==0:print('Verified content',i+1,'/',len(sources),flush=True)
    plugin_dst=sd/'wiiu/environments/aroma/plugins/mk8-ct.wps'
    plugin_dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(plugin,plugin_dst)
    flags=sd/'wiiu/mk8-ct';flags.mkdir(parents=True,exist_ok=True)
    for n in ('notif','log_file'):(flags/n).write_bytes(b'')
    manifest={'region':'EUR','version':81,'console_tested':False,'plugin_sha256':digest(plugin_dst),'content':inventory}
    (output/'Content-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (output/'LIRE_MOI.txt').write_text(
        'MARIO KART 8 EUR v81 - CTGP + costumes + vehicules - Aroma\n\n'
        'Instantane de contenu : fichiers verifies ; les derniers ajouts restent a tester sur console.\n'
        'Le dossier sd contient le plugin, le pack EUR v81 et un instantane de ton contenu Cemu.\n'
        'Aroma doit disposer des modules ContentRedirection et Notifications.\n'
        'Sauvegarde les anciens fichiers de ta carte SD, puis fusionne le contenu de sd a sa racine.\n'
        'Ne copie aucun Turbo.rpx Cemu sur la console. Lance Mario Kart 8 EUR avec sa mise a jour v81.\n'
        'Le plugin refuse le code si les instructions du jeu ne correspondent pas au pack.\n'
        'Conserver ensemble le plugin, Data.bin et custom/cup0. Les deux listes data.cup0 et custom/cup0 sont synchronisees.\n'
        'Journal : sd:/ctgp-loader.txt.\n'
        'Redemarre completement la Wii U apres remplacement du plugin.\n'
        'Retour arriere : remets les anciens fichiers sauvegardes du plugin et de cafeloader.\n',encoding='utf-8')
    if archive:
        archive=Path(archive).resolve()
        if archive in (content,*content.parents) or output in archive.parents:raise ValueError('Archive must be outside its source folder')
        with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=1,allowZip64=True) as z:
            for file in output.rglob('*'):
                if file.is_file():z.write(file,file.relative_to(output).as_posix())
        print('Created',archive,archive.stat().st_size,'bytes',flush=True)
    print('Verified Aroma bundle:',len(inventory),'content files; console validation pending')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--content',required=True);p.add_argument('--plugin',required=True);p.add_argument('--output',required=True);p.add_argument('--archive');p.add_argument('--refresh-generated',action='store_true');a=p.parse_args()
    bundle(a.content,a.plugin,a.output,a.archive,a.refresh_generated)
