"""Replace the installed globe/lobby country hook (0x025145FC) with a version that only touches the LOCAL player's entry.
Usage: python globe_fix.py SOURCE.rpx OUTPUT.rpx   (SOURCE.rpx.json must exist and carry the options module symbols)
"""
from pathlib import Path
import hashlib, json, struct, sys, tempfile
import game_options, rpxlib, costume_patch as patch

HOOK = 0x025145fc


def build(source, output):
    source, output = Path(source), Path(output)
    raw, sections = rpxlib.load(source)
    meta = json.loads(Path(str(source) + '.json').read_text())
    sym = meta['symbols']
    code = next(s for s in sections if s['addr'] == 0x02b10000)
    data = next(s for s in sections if s['addr'] == 0x10300000)
    if b'CTGP_GLOBE_FIX_V1' in code['data']:
        raise ValueError('Already installed')
    word = rpxlib.word_at(sections, HOOK)
    offset = word & 0x3fffffc
    offset -= 0x4000000 if offset & 0x2000000 else 0
    if word & 0xfc000003 != 0x48000000 or HOOK + offset != sym['globe_plate']:
        raise ValueError('The installed globe hook is not the expected options-module globe_plate')
    cb = (code['addr'] + len(code['data']) + 4095) & ~4095
    db = (data['addr'] + len(data['data']) + 4095) & ~4095
    cflags = ('-DGLOBE_ORIGINAL=0x%xu' % sym['original_globe_plate'], '-DGLOBE_SELECTED_COUNTRY=0x%xu' % sym['selected_country'])
    with tempfile.TemporaryDirectory() as temporary:
        try:
            text, state, symbols = game_options.compile_module(Path(temporary), code_address=cb, data_address=db, hooks={},
                                                               source=Path(__file__).parent / 'native/globe_fix.c', cflags=cflags)
        except Exception as error:
            if hasattr(error, 'stderr'):
                print(error.stderr)
            raise
    code['data'] += bytes(cb - code['addr'] - len(code['data'])) + text
    data['data'] += bytes(db - data['addr'] - len(data['data'])) + state
    section = next(s for s in sections if s['addr'] <= HOOK < s['addr'] + len(s['data']))
    body = bytearray(section['data'])
    struct.pack_into('>I', body, HOOK - section['addr'], patch.branch(HOOK, symbols['globe_fix_plate']))
    section['data'] = bytes(body)
    info = next(s for s in sections if s['t'] == 0x80000004)
    body = bytearray(info['data'])
    for off, end, base in [(4, cb + len(text), 0x02000000), (12, db + len(state), 0x10000000)]:
        struct.pack_into('>I', body, off, max(struct.unpack_from('>I', body, off)[0], ((end + 255) & ~255) - base))
    info['data'] = bytes(body)
    output.write_bytes(patch.repack(raw, sections))
    _, checked = rpxlib.load(output)
    for s in sections:
        if s['t'] != 0x80000003:
            assert next(x['data'] for x in checked if x['i'] == s['i']) == s['data']
    meta['symbols'].update(symbols)
    meta.update(output_sha256=hashlib.sha256(output.read_bytes()).hexdigest(), globe_fix_runtime_verified=False)
    Path(str(output) + '.json').write_text(json.dumps(meta, indent=2))
    print('globe fix built; old hook %x replaced' % sym['globe_plate'])


if __name__ == '__main__':
    build(*sys.argv[1:3])
