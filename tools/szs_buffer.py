"""Raise the fixed decompression buffer of ui/cmn/common.szs (EUR v81).

The loader at 0254B8B4/0254B970 gets size = (0x46<<16) - 0x2800 = 4,577,280 bytes. A common.szs that grows
past it (each added national flag costs about 6 KB after SARC alignment) crashes the game at boot.
This only edits the two `lis r7,imm` words; the heap behind the buffer is NOT resized, so test any increase.
"""
import argparse, struct
from pathlib import Path
import rpxlib, costume_patch as patch

SITES = (0x254b8a0, 0x254b95c)
LIS_R7 = 0x3ce00000
ORIGINAL_HI = 0x46

def limit(hi): return (hi << 16) - 0x2800

def build(source, output, hi):
    if not ORIGINAL_HI <= hi <= 0x60: raise ValueError('Unreasonable buffer size')
    raw, sections = rpxlib.load(source)
    relocs = {a for s in sections if s['name'] == '.rela.text' for a, _, _ in struct.iter_unpack('>III', s['data'])}
    for a in SITES:
        if a in relocs: raise ValueError('Site %x has a relocation' % a)
        if rpxlib.word_at(sections, a) not in (LIS_R7 | ORIGINAL_HI, LIS_R7 | hi):
            raise ValueError('Unexpected word at %x' % a)
        s = next(s for s in sections if s['addr'] <= a < s['addr'] + len(s['data']))
        b = bytearray(s['data']); struct.pack_into('>I', b, a - s['addr'], LIS_R7 | hi); s['data'] = bytes(b)
    out = patch.repack(raw, sections); Path(output).write_bytes(out)
    _, check = rpxlib.load(output)
    for a in SITES: assert rpxlib.word_at(check, a) == LIS_R7 | hi
    return limit(hi)

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('source'); p.add_argument('output'); p.add_argument('--hi', type=lambda x: int(x, 0), default=0x48)
    a = p.parse_args(); print('new common.szs decoded-size limit:', build(a.source, a.output, a.hi))
