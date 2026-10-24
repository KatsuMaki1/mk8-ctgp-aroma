#!/usr/bin/env python3
"""Install CTGP-Cafe into a Cemu Mario Kart 8 update folder (the one that holds code/Turbo.rpx).

  python install_cemu.py --update-dir "C:/Users/<you>/AppData/Roaming/Cemu/mlc01/usr/title/0005000e/1010ed00"
                         (--zip C:/Users/<you>/Downloads/ctgp_cafe_wiiu.zip | --cafeloader <folder with 000500001010EC00/ and vol/>)

Needs: pip install capstone. For a v81 game also pass --v64-rpx (see tools/nus_fetch.py). Re-runnable: always rebuilds from the untouched Turbo.rpx.bak.
"""
import argparse, os, shutil, subprocess, sys, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))

ap = argparse.ArgumentParser()
ap.add_argument('--update-dir', required=True)
ap.add_argument('--zip', default=os.path.expanduser('~/Downloads/ctgp_cafe_wiiu.zip'))
ap.add_argument('--v64-rpx', help='MK8 v64 Turbo.rpx (needed when the game is v81)')
ap.add_argument('--cafeloader', help='extracted cafeloader/ folder (e.g. the one on your SD card) instead of the zip')
a = ap.parse_args()

code = os.path.join(a.update_dir, 'code', 'Turbo.rpx'); bak = code + '.bak'
if not os.path.isfile(code) and not os.path.isfile(bak): sys.exit('no code/Turbo.rpx in ' + a.update_dir)
if not os.path.isfile(bak): shutil.copy2(code, bak); print('backup ->', bak)

TID = '000500001010EC00'
if a.cafeloader:                                   # (relative path under the pack, opener) pairs from a folder
    def files(prefix):
        base = os.path.join(a.cafeloader, prefix)
        for root, _, names in os.walk(base):
            for f in names:
                full = os.path.join(root, f); yield os.path.relpath(full, base).replace(os.sep, '/'), (lambda p=full: open(p, 'rb'))
else:
    z = zipfile.ZipFile(a.zip)
    def files(prefix):
        zp = 'CTGP Cafe WiiU/cafeloader/' + prefix.rstrip('/') + '/'
        for info in z.infolist():
            if info.filename.startswith(zp) and not info.is_dir(): yield info.filename[len(zp):], (lambda i=info: z.open(i))

work = os.path.join(HERE, 'out', 'pack'); os.makedirs(work, exist_ok=True)
pack = dict(files(TID + '/'))
for n in ('Code.bin', 'Data.bin', 'Patches.hax', 'Addr.bin'):
    if n not in pack: sys.exit('pack file missing: ' + n)
    with pack[n]() as s, open(os.path.join(work, n), 'wb') as d: shutil.copyfileobj(s, d)
cmd = [sys.executable, os.path.join(HERE, '..', 'tools', 'mkrpx.py'), '--rpx', bak, '--pack', work, '--out', code] + (['--v64-rpx', a.v64_rpx] if a.v64_rpx else [])
subprocess.check_call(cmd)

dest = os.path.join(a.update_dir, 'content'); n = 0
for rel, opener in files('vol/' + TID + '/content/'):
    out = os.path.join(dest, rel); os.makedirs(os.path.dirname(out), exist_ok=True)
    with opener() as s, open(out, 'wb') as d: shutil.copyfileobj(s, d)
    n += 1
print('content files in place:', n, '->', dest)
print('done. To undo: copy', bak, 'over', code, 'and delete the extra content folders (course/G*, ui/cmn/ctgp.szs, custom, charger, data.cup0).')
