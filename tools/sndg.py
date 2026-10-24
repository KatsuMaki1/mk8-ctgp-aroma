#!/usr/bin/env python3
"""Give a custom course its own music FILES so it no longer overrides the music of the original course it was made for.

  sndg.py rename-music --content <dir with course/ and audio/> --course Gu_MyTrack --old pBGM_WII_WARIOSMINE --new pBGM_CT_CHOCOISLAND

A course's SNDG_<dir>.bars is a SARC with the prefetch streams (<name>_N/_F.bfstp), sound effects and a `_param.bin` that lists, per music label,
the prefetch file and the full stream file (audio/stream/<name>_N/_F.bfstm). The game reads the stream path from that list, so only the .bfstm
names are changed: the label itself (an existing name in turbo_sound.bfsar) and the .bfstp names stay as they are, and the course keeps playing
its own music without touching the original course's. The new name must have the SAME length as the old one (fixed string layout).
"""
import argparse, os, re, struct, sys
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


def set_labels(content, course, mapping):
    """replace music labels by names of ANY length: {'pBGM_WU_DESERT_N': 'pBGM_WU_RAINBOW_ROAD_N', ...}. The labels and their .bfstp names are strings in the
    pool of _param.bin; the new strings are appended to the pool and every table word that pointed at an old one is re-pointed (the old text is left behind)."""
    path = os.path.join(content, 'course', course, 'SNDG_%s.bars' % course)
    raw = open(path, 'rb').read(); info, _, ver = szs.sarc_info(raw); files = []; nul = bytes(1); done = 0
    for name, data, _, _ in info:
        for old, new in mapping.items():
            if name == old + '.bfstp': name = new + '.bfstp'
        if name == '_param.bin':
            data = bytearray(data); size, = struct.unpack('>I', data[8:12]); assert size == len(data), 'unexpected param.bin header'
            tab, tab_end, pool = struct.unpack('>III', data[0x10:0x1C])[0], struct.unpack('>I', data[0x14:0x18])[0], struct.unpack('>I', data[0x18:0x1C])[0]
            def sat(o): return bytes(data[pool + o:data.index(nul, pool + o)])
            strings = {}                                   # pool offset -> text, for every string that starts at a string boundary
            o = 0
            while pool + o < len(data):
                t = sat(o); strings[o] = t; o += len(t) + 1
            new_blob = bytearray(); new_off = {}
            for old, new in mapping.items():
                for suf in (b'', b'.bfstp'):
                    new_off[old.encode() + suf] = len(data) - pool + len(new_blob); new_blob += new.encode() + suf + nul
            repoint = {off: new_off[t] for off, t in strings.items() if t in new_off}
            for p in range(tab, pool, 4):                  # every aligned word of the table area
                w, = struct.unpack('>I', data[p:p + 4])
                if w in repoint: struct.pack_into('>I', data, p, repoint[w]); done += 1
            data += new_blob; data += bytes(-len(data) % 4); struct.pack_into('>I', data, 8, len(data)); data = bytes(data)
        files.append((name, data))
    if not done: raise SystemExit('none of %s found in %s' % (', '.join(mapping), path))
    if not os.path.exists(path + '.bak'): open(path + '.bak', 'wb').write(raw)
    open(path, 'wb').write(szs.sarc_write(files, szs.sarc_aligns(raw, 0x20), ver)); print('%s: %d label reference(s) re-pointed' % (course, done)); return done


def course_labels(content, course):
    """music labels (pBGM_*) named in the course's _param.bin"""
    raw = open(os.path.join(content, 'course', course, 'SNDG_%s.bars' % course), 'rb').read()
    for name, data, _, _ in szs.sarc_info(raw)[0]:
        if name == '_param.bin': return sorted({m.decode() for m in re.findall(rb'pBGM_\w+', data)})
    return []


def auto_music(content, course, base_bfsar=None, log=print):
    """make an imported course use its own stream files and a label the base game knows:
    1. stream names -> unique pBGM_CT_<course>... (same length, so the vanilla course keeps its music), 2. labels missing from the base
    game's turbo_sound.bfsar (DLC music) -> pBGM_WU_DESERT_N/_F. Returns the list of things done."""
    import zlib
    done = []
    labels = [l for l in course_labels(content, course) if l.endswith(('_N', '_F'))]
    stems = sorted({l[:-2] for l in labels})
    known = open(base_bfsar, 'rb').read(0x60000) if base_bfsar and os.path.exists(base_bfsar) else None
    for stem in stems:
        if len(stem) >= 13 and not stem.startswith('pBGM_CT_'):
            tag = re.sub(r'[^A-Z0-9]', '', course.upper())
            new = ('pBGM_CT_' + tag)[:len(stem) - 4] + '%04X' % (zlib.crc32(course.encode()) & 0xFFFF)
            new = new.ljust(len(stem), 'X')[:len(stem)]
            rename_music(content, course, stem, new); done.append('streams %s -> %s' % (stem, new))
        if known is not None:
            for suf in ('_N', '_F'):
                if stem + suf in labels and (stem + suf).encode() + bytes(1) not in known:
                    if len(stem) < len('pBGM_WU_DESERT'): done.append('label %s%s has no entry in the base game: kept (too short to relabel)' % (stem, suf)); continue
                    relabel(content, course, stem + suf, 'pBGM_WU_DESERT' + suf); done.append('label %s%s -> pBGM_WU_DESERT%s' % (stem, suf, suf))
    for d in done: log(d)
    if not stems: log('no music labels found in %s (nothing to do)' % course)
    return done


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cmd', choices=['rename-music', 'relabel']); ap.add_argument('--content', required=True)
    ap.add_argument('--course', required=True); ap.add_argument('--old', required=True); ap.add_argument('--new', required=True)
    a = ap.parse_args(); (rename_music if a.cmd == 'rename-music' else relabel)(a.content, a.course, a.old, a.new)
