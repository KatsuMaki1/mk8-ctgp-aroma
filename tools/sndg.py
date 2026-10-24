#!/usr/bin/env python3
"""Give a custom course its own music FILES so it no longer overrides the music of the original course it was made for.

  sndg.py rename-music --content <dir with course/ and audio/> --course Gu_MyTrack --old pBGM_WII_WARIOSMINE --new pBGM_CT_CHOCOISLAND

A course's SNDG_<dir>.bars is a SARC with the prefetch streams (<name>_N/_F.bfstp), sound effects and a `_param.bin` that lists, per music label,
the prefetch file and the full stream file (audio/stream/<name>_N/_F.bfstm). The game reads the stream path from that list, so only the .bfstm
names are changed: the label itself (an existing name in turbo_sound.bfsar) and the .bfstp names stay as they are, and the course keeps playing
its own music without touching the original course's. The new name must have the SAME length as the old one (fixed string layout).
"""
import argparse, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import szs


def rename_music(content, course, old, new):
    if len(old) != len(new): raise SystemExit('--old and --new must have the same length (%d vs %d)' % (len(old), len(new)))
    if not re.fullmatch(r'[A-Za-z0-9_]+', new): raise SystemExit('--new: letters, digits and underscore only')
    path = os.path.join(content, 'course', course, 'SNDG_%s.bars' % course)
    raw = open(path, 'rb').read(); info, _, ver = szs.sarc_info(raw)
    files, hits = [], 0
    for name, data, _, _ in info:
        if name == '_param.bin':
            data, n = re.subn(rb'%s(\w*\.bfstm)' % re.escape(old.encode()), lambda m: new.encode() + m.group(1), data); hits += n
        files.append((name, data))
    if not hits: raise SystemExit('%s not found in %s' % (old, path))
    open(path + '.bak', 'wb').write(raw) if not os.path.exists(path + '.bak') else None
    open(path, 'wb').write(szs.sarc_write(files, szs.sarc_aligns(raw, 0x20), ver))
    moved = []
    stream = os.path.join(content, 'audio', 'stream')
    for suf in ('_N', '_F'):
        for ext in ('.bfstm',):
            src, dst = os.path.join(stream, old + suf + ext), os.path.join(stream, new + suf + ext)
            if os.path.exists(src): os.replace(src, dst); moved.append(os.path.basename(dst))
    print('%s: %d stream path(s) renamed in the archive; stream files renamed: %s' % (course, hits, ', '.join(moved) or 'none found'))


def relabel(content, course, old, new):
    """swap the music label (e.g. pBGM_WII_WARIOSMINE_N -> pBGM_WU_DESERT_N) in the course's archive; `new` must be an existing label of the game's
    turbo_sound.bfsar (DLC music labels are NOT in the base game's, so a course built for a DLC track stays silent until relabelled)"""
    if len(new) > len(old): raise SystemExit('--new must not be longer than --old (%d vs %d)' % (len(new), len(old)))
    path = os.path.join(content, 'course', course, 'SNDG_%s.bars' % course)
    raw = open(path, 'rb').read(); info, _, ver = szs.sarc_info(raw); files, hits = [], 0
    nul = bytes(1)
    for name, data, _, _ in info:
        if name.startswith(old): name = new + name[len(old):]; hits += 1
        if name == '_param.bin':
            pad = nul * (len(old) - len(new))                       # keeps the string pool layout: the strings end at their first NUL
            data, n = re.subn(rb'%s(\w*(?:\.bfst[mp])?)\x00' % re.escape(old.encode()), lambda m: new.encode() + m.group(1) + nul + pad, data); hits += n
        files.append((name, data))
    if not hits: raise SystemExit('%s not found in %s' % (old, path))
    if not os.path.exists(path + '.bak'): open(path + '.bak', 'wb').write(raw)
    open(path, 'wb').write(szs.sarc_write(files, szs.sarc_aligns(raw, 0x20), ver)); print('%s: label %s -> %s (%d places)' % (course, old, new, hits))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cmd', choices=['rename-music', 'relabel']); ap.add_argument('--content', required=True)
    ap.add_argument('--course', required=True); ap.add_argument('--old', required=True); ap.add_argument('--new', required=True)
    a = ap.parse_args(); (rename_music if a.cmd == 'rename-music' else relabel)(a.content, a.course, a.old, a.new)
