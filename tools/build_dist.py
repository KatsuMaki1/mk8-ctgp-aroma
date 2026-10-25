#!/usr/bin/env python3
"""Build the SD card folder for the Aroma plugin from a working Cemu install.

  build_dist.py --content <Cemu update content dir> --base-game <MK8 base content dir> --release-zip ctgp_cafe_wiiu.zip \
                --v64-rpx Turbo_v64.rpx --v81-rpx Turbo_v81.rpx --plugin plugin/mk8-ct.wps --title-id 000500001010ED00 --out dist

Only CTGP's and your own files are copied (the update's own files are not): everything in the CTGP release, the course folders used by data.cup0,
custom/ pictures, your own music streams (pBGM_CT_*), and sky/object files that differ from the base game. The code pack comes from mkpack.py.
"""
import argparse, hashlib, os, shutil, subprocess, sys, zipfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cup0, speedo


def md5(p):
    h = hashlib.md5()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 20), b''): h.update(c)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for n in ('content', 'base-game', 'release-zip', 'v64-rpx', 'v81-rpx', 'plugin', 'title-id', 'out'): ap.add_argument('--' + n, required=True)
    ap.add_argument('--no-speedo-string', action='store_true', help='keep "km/h" in the speed text')
    a = ap.parse_args(); tid = a.title_id.upper()
    sd = os.path.join(a.out, 'sd'); vol = os.path.join(sd, 'cafeloader', 'vol', tid, 'content'); code = os.path.join(sd, 'cafeloader', tid)
    if os.path.exists(a.out): shutil.rmtree(a.out)
    os.makedirs(vol); os.makedirs(code); os.makedirs(os.path.join(sd, 'wiiu', 'environments', 'aroma', 'plugins'))
    z = zipfile.ZipFile(a.release_zip); names = [n for n in z.namelist() if '/cafeloader/vol/' in n and '/content/' in n and not n.endswith('/')]
    pre = names[0][:names[0].index('/content/') + len('/content/')]; rel = {n[len(pre):] for n in names}
    rel_pack = [n for n in z.namelist() if n.endswith(('Code.bin', 'Data.bin', 'Addr.bin', 'Patches.hax'))]
    pack_dir = os.path.dirname(rel_pack[0]); tmp = os.path.join(a.out, '_release_pack'); os.makedirs(tmp)
    for f in ('Code.bin', 'Data.bin', 'Addr.bin', 'Patches.hax'): open(os.path.join(tmp, f), 'wb').write(z.read(pack_dir + '/' + f))
    chosen = set(r for r in rel if os.path.exists(os.path.join(a.content, r)))                         # CTGP's own files (installed copy)
    chosen.add('data.cup0')
    cups = cup0.parse(open(os.path.join(a.content, 'data.cup0'), 'rb').read())
    for c in cups:
        for t in c.tracks:
            if t.dir != 'Ginvalid': chosen |= {os.path.relpath(os.path.join(dp, f), a.content).replace(os.sep, '/') for dp, _, fs in os.walk(os.path.join(a.content, 'course', t.dir)) for f in fs}
    for dp, _, fs in os.walk(os.path.join(a.content, 'custom')): chosen |= {os.path.relpath(os.path.join(dp, f), a.content).replace(os.sep, '/') for f in fs}
    for f in os.listdir(os.path.join(a.content, 'audio', 'stream')):
        if f.startswith('pBGM_CT_'): chosen.add('audio/stream/' + f)
    for dp, _, fs in os.walk(os.path.join(a.content, 'mapobj')):                                         # skies / objects that differ from the base game
        for f in fs:
            p = os.path.join(dp, f); r = os.path.relpath(p, a.content).replace(os.sep, '/'); b = os.path.join(a.base_game, r)
            if r in rel or not os.path.exists(b) or md5(p) != md5(b): chosen.add(r)
    chosen = {r for r in chosen if os.path.exists(os.path.join(a.content, r)) and r.split('/')[0] in ('course', 'mapobj', 'ui', 'custom', 'charger', 'audio', 'data.cup0')}
    tot = 0
    for r in sorted(chosen):
        dst = os.path.join(vol, r); os.makedirs(os.path.dirname(dst), exist_ok=True); shutil.copy2(os.path.join(a.content, r), dst); tot += os.path.getsize(dst)
    print('content: %d files, %d MB' % (len(chosen), tot // 1000000))
    if not a.no_speedo_string: speedo.patch_data(tmp, tmp + '_speedo'); pack_src = tmp + '_speedo'
    else: pack_src = tmp
    subprocess.check_call([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mkpack.py'), '--v64-rpx', a.v64_rpx, '--v81-rpx', a.v81_rpx, '--release', pack_src, '--out', code])
    shutil.rmtree(tmp); shutil.rmtree(tmp + '_speedo', ignore_errors=True)
    shutil.copy2(a.plugin, os.path.join(sd, 'wiiu', 'environments', 'aroma', 'plugins', 'mk8-ct.wps'))
    print('done ->', os.path.abspath(sd))


if __name__ == '__main__':
    main()
