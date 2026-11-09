"""Guard the verified EUR81 native Picture draw entry; preserve all other hooks."""
from pathlib import Path
import hashlib
import json
import struct
import tempfile
import rpxlib
import costume_patch as patch
import game_options


def build(source, output):
    raw, sections = rpxlib.load(source)
    address, expected = 0x02696094, 0x9421ff30
    if rpxlib.word_at(sections, address) != expected:
        raise ValueError('Unknown/already-patched Picture draw entry')
    code = next(s for s in sections if s['addr'] == 0x2b10000)
    data = next(s for s in sections if s['addr'] == 0x10300000)
    if b'MK8_UI_NULL_TEXTURE_GUARD_V1' in code['data']:
        raise ValueError('Guard already installed')
    cb = (code['addr'] + len(code['data']) + 4095) & ~4095
    db = (data['addr'] + len(data['data']) + 4095) & ~4095
    with tempfile.TemporaryDirectory() as temporary:
        text, mutable, symbols = game_options.compile_module(Path(temporary), code_address=cb, data_address=db,
            hooks={'ui_picture_draw': (address, expected)}, source=Path(__file__).parent/'native/ui_texture_guard.c')
    code['data'] += bytes(cb-code['addr']-len(code['data'])) + text
    data['data'] += bytes(db-data['addr']-len(data['data'])) + mutable
    target = next(s for s in sections if s['addr'] <= address < s['addr']+len(s['data']))
    body = bytearray(target['data'])
    struct.pack_into('>I', body, address-target['addr'], patch.branch(address,symbols['ui_picture_draw']))
    target['data'] = bytes(body)
    info = next(s for s in sections if s['t'] == 0x80000004)
    body = bytearray(info['data'])
    for offset, end, base in [(4,cb+len(text),0x2000000),(12,db+len(mutable),0x10000000)]:
        struct.pack_into('>I',body,offset,max(struct.unpack_from('>I',body,offset)[0],((end+255)&~255)-base))
    info['data'] = bytes(body)
    result = patch.repack(raw,sections)
    Path(output).write_bytes(result)
    _, checked = rpxlib.load(output)
    for section in sections:
        if section['t'] != 0x80000003:
            assert next(s['data'] for s in checked if s['i']==section['i']) == section['data']
    previous = Path(str(source)+'.json')
    meta = json.loads(previous.read_text()) if previous.exists() else {}
    meta.setdefault('symbols',{}).update(symbols)
    meta.update(output_sha256=hashlib.sha256(result).hexdigest(), runtime_verified=False,
                ui_texture_guard_source_sha256=hashlib.sha256(raw).hexdigest())
    Path(str(output)+'.json').write_text(json.dumps(meta,indent=2))


if __name__ == '__main__':
    import sys
    build(sys.argv[1],sys.argv[2])
