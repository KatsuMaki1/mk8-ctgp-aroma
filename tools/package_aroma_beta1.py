"""BETA 1 Aroma SD pack = R7 COMPLET + P75 code pack + plugin v0.29 + content changed since R7 + Protarium Inkay r17.

Streams the R7 zip, swaps the code pack and mk8-ct.wps, replaces/adds the sandbox content files listed in work/aroma_p75/newer_than_r7.json,
adds Inkay (module + plugin) from the official r17 archive, refreshes sd/CTGP_manifest.json and adds sd/LISEZ-MOI_BETA1.txt.
Refuses to overwrite an existing archive and any private-looking file.
"""
import hashlib, json, zipfile
from pathlib import Path

WORK = Path('C:/Users/evant/Documents/Codex/2026-10-25/files-mentioned-by-the-user-handoff')
REPO = Path(__file__).resolve().parents[1]
BASE = WORK / 'outputs/WiiU/CTGP_WiiU_COMPLET_SD_R7_Optimisations_R3_2026-11-04.zip'
OUT = WORK / 'outputs/WiiU/CTGP_Aroma_BETA1c_SD_Protarium_2026-11-09.zip'
PAYLOAD = WORK / 'work/aroma_p75/release/sd/cafeloader/000500001010ED00'
CONTENT = WORK / 'work/bcp_r4_test/mlc/usr/title/0005000e/1010ed00/content'
CHANGED = json.loads((WORK / 'work/aroma_p75/newer_than_r7.json').read_text())
PLUGIN = REPO / 'plugin/mk8-ct.wps'
INKAY = Path('E:/claude-code/inkay-protarium-online/dist/wiiu.zip')
INKAY_SHA = 'b755b1185c2c845c868919bc935d02906a9b19dcea310b18f2060de64c43a104'
README = REPO / 'docs/BETA1_LISEZ-MOI.txt'
CODE = 'sd/cafeloader/000500001010ED00/'
VOL = 'sd/cafeloader/vol/000500001010ED00/content/'
FORBIDDEN = ('account.dat', 'persisid', '.db', '.sqlite', 'secret', 'kerberos', '.env', 'userdata.dat', 'miidata')


def sha(b):
    return hashlib.sha256(b).hexdigest()


def main():
    assert not OUT.exists(), 'Never overwrite a delivered archive'
    assert sha(INKAY.read_bytes()) == INKAY_SHA, 'Inkay archive is not the official r17 release'
    replace = {CODE + f: (PAYLOAD / f).read_bytes() for f in ('Addr.bin', 'Code.bin', 'Data.bin', 'Patches.hax', 'Verify.hax', 'Features.json')}
    replace['sd/wiiu/environments/aroma/plugins/mk8-ct.wps'] = PLUGIN.read_bytes()
    for rel in CHANGED:
        replace[VOL + rel] = (CONTENT / rel).read_bytes()
    with zipfile.ZipFile(INKAY) as z:
        for name in z.namelist():
            if not name.endswith('/'):
                replace['sd/' + name] = z.read(name)
    for name in replace:
        assert not any(f in name.lower() for f in FORBIDDEN), 'private-looking file ' + name
    written = set()
    with zipfile.ZipFile(BASE) as src, zipfile.ZipFile(OUT, 'w', zipfile.ZIP_DEFLATED, compresslevel=1, allowZip64=True) as dst:
        names = [n for n in src.namelist() if not n.endswith('/')]
        for i, name in enumerate(names):
            assert not any(f in name.lower() for f in FORBIDDEN), 'private-looking file ' + name
            if name in replace:
                continue
            if name == 'sd/CTGP_manifest.json':
                manifest = json.loads(src.read(name))
                continue
            with src.open(name) as f, dst.open(name, 'w', force_zip64=True) as o:
                while True:
                    b = f.read(4 << 20)
                    if not b:
                        break
                    o.write(b)
            written.add(name)
            if i % 400 == 0:
                print(i, '/', len(names), flush=True)
        for name, data in replace.items():
            dst.writestr(name, data)
            written.add(name)
            manifest['files'][name] = {'size': len(data), 'sha256': sha(data)}
        manifest.update(release='BETA1c Protarium (P75 minus nn::act import hooks, relocation fix, plugin v0.29, Inkay r17)', console_tested=False)
        dst.writestr('sd/CTGP_manifest.json', json.dumps(manifest, indent=2))
        dst.write(README, 'sd/LISEZ-MOI_BETA1.txt')
    print('done', OUT, OUT.stat().st_size // 2**20, 'MB', len(written), 'files')


if __name__ == '__main__':
    main()
