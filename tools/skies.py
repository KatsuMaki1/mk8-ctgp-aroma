#!/usr/bin/env python3
"""Give a course its own sky box: mapobj objects are shared by every course (a sky is looked up by its object name, e.g. VRfair), so two
tracks that ship different skies with the same name overwrite each other. isolate() copies the sky under a name unique to the course and points
the course's object list at it (same-length rename of the file name, of the names inside the file and of the byaml string).

  skies.py isolate --content <dir> --course Gu_MyTrack --old VRfair --bfres <the track's own VRfair.bfres>
"""
import argparse, os, shutil, sys, zlib


def private_name(course, old):
    if len(old) < 4: raise SystemExit('sky name %r is too short to be renamed' % old)
    return ('VR' + '%08X' % zlib.crc32(course.encode()))[:len(old)].ljust(len(old), 'X')


def isolate(content, course, old, bfres):
    new = private_name(course, old)
    dst = os.path.join(content, 'mapobj', new); os.makedirs(dst, exist_ok=True)
    data = open(bfres, 'rb').read(); hits = data.count(old.encode())
    # the game finds the sky MODEL (and its cube map, which the walls reflect) by the object name, so every name inside the file is renamed too.
    # Same length, and the sky's names all share the prefix, so the file's search dictionaries stay valid.
    open(os.path.join(dst, new + '.bfres'), 'wb').write(data.replace(old.encode(), new.encode())); print('renamed %d name(s) inside the sky file' % hits)
    n = 0
    for f in os.listdir(os.path.join(content, 'course', course)):
        if f.startswith('course_muunt') and f.endswith('.byaml'):
            p = os.path.join(content, 'course', course, f); b = open(p, 'rb').read(); key = old.encode() + bytes(1)
            if key in b:
                open(p + '.bak', 'wb').write(b) if not os.path.exists(p + '.bak') else None
                open(p, 'wb').write(b.replace(key, new.encode() + bytes(1))); n += b.count(key)
    if not n: raise SystemExit('%s not found in the course object list of %s' % (old, course))
    print('%s: sky %s -> %s (own copy in mapobj/%s, %d reference(s) updated)' % (course, old, new, new, n)); return new


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cmd', choices=['isolate']); ap.add_argument('--content', required=True); ap.add_argument('--course', required=True)
    ap.add_argument('--old', required=True); ap.add_argument('--bfres', required=True)
    a = ap.parse_args(); isolate(a.content, a.course, a.old, a.bfres)
