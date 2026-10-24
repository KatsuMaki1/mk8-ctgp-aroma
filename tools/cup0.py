#!/usr/bin/env python3
"""Read / edit / extend CTGP-Café's data.cup0 and import custom course folders (e.g. from GameBanana).

  cup0.py list      --content <dir holding data.cup0>
  cup0.py add-track --content <dir> --course <folder|zip> --name "Track name" (--cup N --slot S | --new-cup "My Cup")
                    [--dir Gu_MyTrack] [--tag DS|3DS|Wii|N64|GBA|SNES|Tour] [--picture my.bflim]
  cup0.py selftest  --content <dir>

data.cup0 layout (big endian): 'CUP0', u32 ncups, u32 pool_offset, then ncups records of 80 bytes
  { u32 type, u32 icon, u32 name, u32 cup_id, 4 x { u32 dir, u32 picture, u32 track_name, u32 tag } }
every string is a NUL-terminated offset into the pool that follows the records. type 1 = the game's 12 DLC cups (dir "Ginvalid" = keep
the original DLC course), type 2 = CTGP cups; `icon` is the picture index 0..5 of the six extra cup buttons (L_CupIcon_12..17 in ui/cmn/ctgp.szs).
Limits that come from the CTGP code, not from this tool: 6 CTGP cups, 4 tracks per cup, battle courses are hard-coded in the code.
"""
import argparse, os, re, shutil, struct, sys, zipfile

REQUIRED = ['course_model.szs', 'course.kcl', 'course_muunt.byaml', 'course.bgenv', 'course_maptexture.bflim']
OPTIONAL = ['course_muunt_200.byaml', 'course.bglpbd', 'course.ptcl', 'course_mapcamera.bin']
FIRST_CUSTOM_ID = 24


class Track:
    def __init__(self, dir='Ginvalid', picture='', name='', tag=''): self.dir, self.picture, self.name, self.tag = dir, picture, name, tag
    def __eq__(self, o): return vars(self) == vars(o)


class Cup:
    def __init__(self, type, icon, name, cup_id, tracks): self.type, self.icon, self.name, self.cup_id, self.tracks = type, icon, name, cup_id, tracks
    def __eq__(self, o): return vars(self) == vars(o)


def parse(d):
    magic, n, pool = struct.unpack('>4sII', d[:12])
    if magic != b'CUP0' or pool != 12 + 80 * n: raise ValueError('not a CUP0 file')
    def s(o): return d[pool + o:d.index(b'\0', pool + o)].decode('utf-8')
    cups = []
    for i in range(n):
        r = struct.unpack('>20I', d[12 + i * 80:12 + (i + 1) * 80])
        cups.append(Cup(r[0], r[1], s(r[2]), r[3], [Track(s(r[4 + t * 4]), s(r[5 + t * 4]), s(r[6 + t * 4]), s(r[7 + t * 4])) for t in range(4)]))
    return cups


def build(cups):
    pool = bytearray(); recs = bytearray()
    def add(s):
        o = len(pool); pool.extend(s.encode('utf-8') + b'\0'); return o
    for c in cups:
        assert len(c.tracks) == 4, 'a cup has exactly 4 tracks'
        words = [c.type, c.icon, add(c.name), c.cup_id]
        for t in c.tracks: words += [add(t.dir), add(t.picture), add(t.name), add(t.tag)]
        recs += struct.pack('>20I', *words)
    return struct.pack('>4sII', b'CUP0', len(cups), 12 + len(recs)) + bytes(recs) + bytes(pool)


def listing(cups):
    for i, c in enumerate(cups):
        kind = 'DLC ' if c.type == 1 else 'CTGP'
        print('cup %2d [%s id=%d icon=%d] %s' % (i, kind, c.cup_id, c.icon, c.name))
        for k, t in enumerate(c.tracks):
            print('    slot %d  %-22s %-28s %s  %s' % (k, t.dir, t.name or '(game name)', ('[' + t.tag + ']') if t.tag else '', t.picture))


def find_courses(src, tmp):
    """-> {course folder name: path} for every folder with course_model.szs inside a directory or a zip"""
    if os.path.isfile(src):
        with zipfile.ZipFile(src) as z: z.extractall(tmp)
        src = tmp
    found = {}
    for root, _, files in os.walk(src):
        if 'course_model.szs' in files: found[os.path.basename(root)] = root
    return found


def import_course(course_dir, content, new_dir, picture, force):
    dst = os.path.join(content, 'course', new_dir)
    if os.path.exists(dst) and not force: raise SystemExit('%s already exists (use --force to overwrite)' % dst)
    os.makedirs(dst, exist_ok=True)
    old = os.path.basename(course_dir); names = os.listdir(course_dir)
    missing = [f for f in REQUIRED if f not in names]
    if missing: print('warning: missing %s (the game may refuse or crash on this track)' % ', '.join(missing))
    for f in names:
        out = f
        for pre in ('', 'SNDG_'):                                   # sound banks are named after the folder
            if f == pre + old + '.bars': out = pre + new_dir + '.bars'
        shutil.copy2(os.path.join(course_dir, f), os.path.join(dst, out))
    os.makedirs(os.path.join(content, 'custom'), exist_ok=True)
    pic = 'custom/cPict_%s.bflim' % new_dir
    if picture: shutil.copy2(picture, os.path.join(content, pic))
    else:                                                           # placeholder: reuse a picture that already exists
        have = sorted(f for f in os.listdir(os.path.join(content, 'custom')) if f.startswith('cPict_'))
        if not have: raise SystemExit('no --picture given and no existing cPict_*.bflim to use as a placeholder')
        shutil.copy2(os.path.join(content, 'custom', have[0]), os.path.join(content, pic)); print('note: placeholder preview picture (%s); give --picture for the real one' % have[0])
    return pic


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cmd', choices=['list', 'add-track', 'selftest']); ap.add_argument('--content', required=True)
    ap.add_argument('--course'); ap.add_argument('--name'); ap.add_argument('--dir'); ap.add_argument('--tag', default='')
    ap.add_argument('--picture'); ap.add_argument('--cup', type=int); ap.add_argument('--slot', type=int); ap.add_argument('--new-cup')
    ap.add_argument('--course-name', help='which course folder to take when the archive holds several'); ap.add_argument('--force', action='store_true')
    a = ap.parse_args()
    path = os.path.join(a.content, 'data.cup0'); raw = open(path, 'rb').read(); cups = parse(raw)
    if a.cmd == 'list': return listing(cups)
    if a.cmd == 'selftest':
        assert build(cups) == raw, 'rebuilt file differs from the original'; assert parse(build(cups)) == cups
        print('ok: parse -> build reproduces data.cup0 byte for byte (%d cups)' % len(cups)); return

    # add-track
    if not a.course or not a.name: sys.exit('--course and --name are required')
    if (a.cup is None) == (a.new_cup is None): sys.exit('choose either --cup N --slot S (replace a slot) or --new-cup "Name Cup"')
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        found = find_courses(a.course, tmp)
        if not found: sys.exit('no course folder (with course_model.szs) found in %s' % a.course)
        if len(found) > 1 and a.course_name not in found: sys.exit('several courses found: %s ; pick one with --course-name' % ', '.join(found))
        src_name = a.course_name if a.course_name in found else next(iter(found))
        new_dir = a.dir or (src_name if src_name.startswith('G') else 'Gu_' + re.sub(r'[^A-Za-z0-9_]', '', src_name))
        if not re.fullmatch(r'G[A-Za-z0-9_]+', new_dir): sys.exit('--dir must start with G and use letters/digits/underscore')
        if any(t.dir == new_dir for c in cups for t in c.tracks) and not a.force: sys.exit('%s is already used in data.cup0' % new_dir)
        pic = import_course(found[src_name], a.content, new_dir, a.picture, a.force)
    track = Track(new_dir, pic, a.name, a.tag)
    if a.new_cup:
        custom = [c for c in cups if c.type == 2]
        free = [i for i in range(6) if i not in {c.icon for c in custom}]
        if not free: sys.exit('all 6 CTGP cup slots are used: replace a slot with --cup/--slot instead')
        # A cup always has 4 tracks: start with the new track in all four slots, replace slots 1..3 with later add-track calls.
        cups.append(Cup(2, free[0], a.new_cup, max(c.cup_id for c in cups) + 1, [Track(**vars(track)) for _ in range(4)]))
        a.cup, a.slot = len(cups) - 1, 0
        print('new cup %d "%s" (picture slot %d): the track fills all 4 slots for now; replace slots 1-3 with --cup %d --slot 1..3' % (a.cup, a.new_cup, free[0], a.cup))
        print('warning: more cups than the original 17 is untested; the game code may have fixed-size tables')
    if not (0 <= a.cup < len(cups) and a.slot in range(4)): sys.exit('--cup/--slot out of range (see `list`)')
    shutil.copy2(path, path + '.bak')
    cups[a.cup].tracks[a.slot] = track
    open(path, 'wb').write(build(cups))
    print('cup %d slot %d is now "%s" (%s); previous data.cup0 saved as data.cup0.bak' % (a.cup, a.slot, a.name, new_dir))


if __name__ == '__main__':
    main()
