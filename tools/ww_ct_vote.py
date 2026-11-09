"""Add the Worldwide-roulette CT module to an installed RPX (chains the existing roulette update hook at 0x025FFB84).
Usage: python ww_ct_vote.py SOURCE.rpx OUTPUT.rpx      (SOURCE.rpx.json must exist)
"""
from pathlib import Path
import hashlib, json, struct, sys, tempfile
import game_options, rpxlib, costume_patch as patch

UPDATE = 0x025ffb84
PICTURE = 0x0255c8b8
NAME = 0x0255a668
CARD = 0x0257e00c


def build(source, output, enabled=True):
    source, output = Path(source), Path(output)
    raw, sections = rpxlib.load(source)
    meta = json.loads(Path(str(source) + '.json').read_text())
    code = next(s for s in sections if s['addr'] == 0x02b10000)
    data = next(s for s in sections if s['addr'] == 0x10300000)
    if b'CTGP_WW_CT_VOTE_V1' in code['data']:
        raise ValueError('Already installed')
    word = rpxlib.word_at(sections, UPDATE)
    if word & 0xfc000003 != 0x48000000:
        raise ValueError('Roulette update is not a plain branch (expected the installed online module hook)')
    offset = word & 0x3fffffc
    offset -= 0x4000000 if offset & 0x2000000 else 0
    previous = UPDATE + offset
    if not code['addr'] <= previous < code['addr'] + len(code['data']):
        raise ValueError('Unknown previous roulette hook target %x' % previous)
    name_word = rpxlib.word_at(sections, NAME)
    if name_word & 0xfc000003 != 0x48000000:
        raise ValueError('Course name lookup is not a plain branch')
    name_offset = name_word & 0x3fffffc
    name_offset -= 0x4000000 if name_offset & 0x2000000 else 0
    name_previous = NAME + name_offset
    cb = (code['addr'] + len(code['data']) + 4095) & ~4095
    db = (data['addr'] + len(data['data']) + 4095) & ~4095
    with tempfile.TemporaryDirectory() as temporary:
        try:
            text, state, symbols = game_options.compile_module(Path(temporary), code_address=cb, data_address=db, hooks={'ww_picture': (PICTURE, 0x9421ff78), 'ww_card': (CARD, 0x7c0802a6)},
                                                               source=Path(__file__).parent / 'native/ww_ct_vote.c',
                                                               cflags=('-DWW_CT_PREVIOUS_UPDATE=0x%xu' % previous, '-DWW_CT_PREVIOUS_NAME=0x%xu' % name_previous, '-DWW_CT_ENABLED_DEFAULT=%d' % (1 if enabled else 0)))
        except Exception as error:
            if hasattr(error, 'stderr'):
                print(error.stderr)
            raise
    code['data'] += bytes(cb - code['addr'] - len(code['data'])) + text
    data['data'] += bytes(db - data['addr'] - len(data['data'])) + state
    section = next(s for s in sections if s['addr'] <= UPDATE < s['addr'] + len(s['data']))
    body = bytearray(section['data'])
    struct.pack_into('>I', body, UPDATE - section['addr'], patch.branch(UPDATE, symbols['ww_ct_update']))
    section['data'] = bytes(body)
    if rpxlib.word_at(sections, PICTURE) != 0x9421ff78:
        raise ValueError('Unexpected course picture lookup prologue')
    section = next(s for s in sections if s['addr'] <= PICTURE < s['addr'] + len(s['data']))
    body = bytearray(section['data'])
    struct.pack_into('>I', body, PICTURE - section['addr'], patch.branch(PICTURE, symbols['ww_ct_picture']))
    section['data'] = bytes(body)
    if rpxlib.word_at(sections, CARD) != 0x7c0802a6:
        raise ValueError('Unexpected vote card prologue')
    section = next(s for s in sections if s['addr'] <= CARD < s['addr'] + len(s['data']))
    body = bytearray(section['data'])
    struct.pack_into('>I', body, CARD - section['addr'], patch.branch(CARD, symbols['ww_ct_card']))
    section['data'] = bytes(body)
    section = next(s for s in sections if s['addr'] <= NAME < s['addr'] + len(s['data']))
    body = bytearray(section['data'])
    struct.pack_into('>I', body, NAME - section['addr'], patch.branch(NAME, symbols['ww_ct_name']))
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
    meta.update(output_sha256=hashlib.sha256(output.read_bytes()).hexdigest(), ww_ct_previous_update=hex(previous), ww_ct_runtime_verified=False)
    Path(str(output) + '.json').write_text(json.dumps(meta, indent=2))
    print('WW CT module built; chained previous roulette hook %x' % previous)


if __name__ == '__main__':
    build(sys.argv[1], sys.argv[2], enabled=(len(sys.argv) < 4 or sys.argv[3] != 'off'))
