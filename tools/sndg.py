#!/usr/bin/env python3
"""Give a custom course its own music names so it no longer overrides the music of the original course it was made for.

  sndg.py rename-music --content <dir with course/ and audio/> --course Gu_MyTrack --old pBGM_WII_WARIOSMINE --new pBGM_CT_CHOCOISLAND

A course's SNDG_<dir>.bars is a SARC with the prefetch streams (<name>_N/_F.bfstp), sound effects and a `_param.bin` that names the music;
the full streams are audio/stream/<name>_N/_F.bfstm. The new base name must have the SAME length as the old one (the names are strings in a
fixed layout inside _param.bin). Streams found in <content>/audio/stream are renamed; nothing is touched if they are absent.
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
        if old in name: name = name.replace(old, new); hits += 1
        if name == '_param.bin':
            n = data.count(old.encode()); data = data.replace(old.encode(), new.encode()); hits += n
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
    print('%s: %d name(s) renamed in the archive; streams renamed: %s' % (course, hits, ', '.join(moved) or 'none found'))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cmd', choices=['rename-music']); ap.add_argument('--content', required=True)
    ap.add_argument('--course', required=True); ap.add_argument('--old', required=True); ap.add_argument('--new', required=True)
    a = ap.parse_args(); rename_music(a.content, a.course, a.old, a.new)
