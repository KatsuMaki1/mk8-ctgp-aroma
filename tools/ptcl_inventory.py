"""Read-only inventory of Wii U EFTF v0x41 effects and emitter colors.

Format reference: https://nintendo-formats.com/libs/nw/ptcl/wiiu.html
No mutation/repacking: the native effects remain untouched during diagnosis.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct


def inventory(data):
    def span(offset, size):
        if offset < 0 or size < 0 or offset+size > len(data):
            raise ValueError('PTCL range outside file')
        return data[offset:offset+size]
    def word(offset):
        return struct.unpack('>I', span(offset, 4))[0]
    if span(0, 4) != b'EFTF' or word(4) != 0x41:
        raise ValueError('Only Wii U EFTF v0x41 is supported')
    strings, count = word(0x10), word(8)
    if not count or count > 4096:
        raise ValueError('Invalid effect count')
    span(0x48, count*0x1c)
    def name(relative):
        offset = strings+relative
        span(offset, 1)
        end = data.find(b'\0', offset, min(len(data), offset+512))
        if end < 0:
            raise ValueError('Unterminated effect/emitter name')
        return data[offset:end].decode('utf-8')
    effects = []
    for index in range(count):
        address = 0x48+index*0x1c
        n, table = word(address+0x10), word(address+0x14)
        if n > 1024:
            raise ValueError('Invalid emitter count')
        span(table, n*16)
        emitters = []
        for emitter in range(n):
            offset = word(table+emitter*16)
            span(offset, 0x8bc)
            colors = [struct.unpack('>32f', span(offset+base, 128)) for base in (0x650, 0x6d0)]
            if any(not math.isfinite(value) for color in colors for value in color):
                raise ValueError('Non-finite emitter color')
            emitters.append(dict(offset=offset, type=word(offset), name=name(word(offset+0x38)),
                                 color_function=[word(offset+0x330),word(offset+0x334)],
                                 colors=[list(color) for color in colors]))
        effects.append(dict(index=index, name=name(word(address+8)), emitters=emitters))
    return dict(version=0x41, sha256=hashlib.sha256(data).hexdigest(), effects=effects)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    result = inventory(args.source.read_bytes())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(f"{len(result['effects'])} effects inventoried; source unchanged")
