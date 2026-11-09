"""Full Aroma SD pack = R7 COMPLET pack with the code pack replaced by the Protarium-server build (game server id 1010EB01).

Streams the R7 zip into a new zip, swaps the five code-pack files + Features.json, refreshes their sha256/size in sd/CTGP_manifest.json and
adds sd/LISEZ-MOI_PROTARIUM.txt. Refuses to overwrite an existing archive.
"""
import hashlib, json, sys, zipfile
from pathlib import Path

WORK = Path('C:/Users/evant/Documents/Codex/2026-10-25/files-mentioned-by-the-user-handoff')
BASE = WORK / 'outputs/WiiU/CTGP_WiiU_COMPLET_SD_R7_Optimisations_R3_2026-11-04.zip'
OUT = WORK / 'outputs/WiiU/CTGP_Aroma_COMPLET_SD_R7_ServeurProtarium_2026-11-06.zip'
PAYLOAD = WORK / 'work/aroma_p46/release/sd/cafeloader/000500001010ED00'
README = Path(__file__).resolve().parents[1] / 'docs/AROMA_TESTER_README.txt'
PREFIX = 'sd/cafeloader/000500001010ED00/'
FILES = ['Addr.bin', 'Code.bin', 'Data.bin', 'Patches.hax', 'Verify.hax', 'Features.json']
FORBIDDEN = ('account.dat', 'persisid', '.db', '.sqlite', 'secret', 'kerberos', '.env')


def main():
    assert not OUT.exists(), 'Never overwrite a delivered archive'
    new = {PREFIX + f: (PAYLOAD / f).read_bytes() for f in FILES}
    with zipfile.ZipFile(BASE) as src, zipfile.ZipFile(OUT, 'w', zipfile.ZIP_DEFLATED, compresslevel=1, allowZip64=True) as dst:
        names = src.namelist()
        for i, name in enumerate(names):
            if name.endswith('/'):
                continue
            low = name.lower()
            assert not any(f in low for f in FORBIDDEN), 'private-looking file: ' + name
            if name in new:
                continue
            if name == 'sd/CTGP_manifest.json':
                m = json.loads(src.read(name))
                for k, data in new.items():
                    m['files'][k] = {'size': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
                m['release'] = 'R7 + Protarium server (game server id 1010EB01)'
                dst.writestr(name, json.dumps(m, indent=2))
                continue
            with src.open(name) as f, dst.open(name, 'w', force_zip64=True) as o:
                while True:
                    b = f.read(4 << 20)
                    if not b:
                        break
                    o.write(b)
            if i % 300 == 0:
                print(i, '/', len(names), flush=True)
        for k, data in new.items():
            dst.writestr(k, data)
        dst.write(README, 'sd/LISEZ-MOI_PROTARIUM.txt')
    print('done', OUT, OUT.stat().st_size // 2**20, 'MB')


if __name__ == '__main__':
    main()
