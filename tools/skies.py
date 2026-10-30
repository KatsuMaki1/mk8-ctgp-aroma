#!/usr/bin/env python3
"""Install sky assets under their original engine names.

Renaming BFRES skies produced corrupt rendering in-game. Keep the asset intact
and refuse conflicting shared overrides. Real isolation needs runtime routing.
"""
import argparse, os, shutil, sys, zlib


def private_name(course, old):
    if len(old) < 4: raise SystemExit('sky name %r is too short to be renamed' % old)
    return ('VR' + '%08X' % zlib.crc32(course.encode()))[:len(old)].ljust(len(old), 'X')


def install_original(content, course, old, bfres):
    from pathlib import Path
    import backup
    if not old.startswith('VR') or not old.isalnum(): raise ValueError('Invalid sky object name')
    data = Path(bfres).read_bytes()
    if data[:4] != b'FRES': raise ValueError('Sky is not a Wii U BFRES')
    target = Path(content) / 'mapobj' / old / (old + '.bfres')
    if target.exists() and target.read_bytes() != data:
        raise SystemExit('conflicting shared sky %s: existing asset kept; per-course runtime routing is required' % old)
    course_dir = Path(content) / 'course' / course
    if not course_dir.is_dir(): raise ValueError('Course folder not found: ' + str(course_dir))
    renamed = private_name(course, old).encode() + bytes(1)
    original = old.encode() + bytes(1)
    changes = []
    for f in os.listdir(os.path.join(content, 'course', course)):
        if f.startswith('course_muunt') and f.endswith('.byaml'):
            path = course_dir / f; before = path.read_bytes()
            if renamed in before: changes.append((path, before.replace(renamed, original)))
    target.parent.mkdir(parents=True, exist_ok=True)
    backup.save(content, target)
    if not target.exists(): target.write_bytes(data)
    for path, after in changes:
        backup.save(content, path); path.write_bytes(after)
    print('%s: original sky %s installed unchanged; %d object list(s) restored. This sky name is shared by the game.' % (course, old, len(changes)))
    return old


def isolate(content, course, old, bfres):
    raise SystemExit('Sky renaming is disabled: it corrupts rendering. Use install-original; genuine isolation requires runtime routing.')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cmd', choices=['isolate', 'install-original']); ap.add_argument('--content', required=True); ap.add_argument('--course', required=True)
    ap.add_argument('--old', required=True); ap.add_argument('--bfres', required=True)
    a = ap.parse_args(); (install_original if a.cmd == 'install-original' else isolate)(a.content, a.course, a.old, a.bfres)
