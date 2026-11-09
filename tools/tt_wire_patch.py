"""Append typed NEX mapping to a known-booting EUR81 Options prototype.

Does not rebuild/replace its Options, controller, UI or particle code.
"""
import hashlib
import json
import struct
import tempfile
from pathlib import Path
import costume_patch as patch
import game_options
import rpxlib

HOOKS = {"tt_course_event": (0x025bc400, 0x9421ffa8),
         "tt_wire_upload": (0x023f4f48, 0x80c40000),
         "tt_wire_score": (0x02405e7c, 0x7c0802a6),
         "tt_country_profile": (0x024dd0f0, 0x7c0802a6),
         "tt_country_row": (0x02595930, 0x98c3000c),
         "tt_wire_query": (0x02406260, 0x7c0802a6),
         "tt_wire_target": (0x0241ece0, 0x81830000)}


def build(source, output, ghosts=False):
    source, output = Path(source), Path(output)
    raw, sections = rpxlib.load(source)
    meta = json.loads(Path(str(source)+".json").read_text())
    pink = meta["symbols"]["pink_enabled"]
    hooks = dict(HOOKS)
    flags = []
    call_patches = {}
    if ghosts:
        hooks.update({'tt_save_record':(0x24f41c8,0x9421feb8),'tt_upload_sequence':(0x25c8ca0,0x9421ff70),
            'tt_online_exit':(0x25cf00c,0x7c0802a6),'tt_online_enter':(0x25cbe30,0x9421ff80),
            'tt_title_update':(0x2596e3c,0x9421ffb8),'tt_online_calc':(0x25cde3c,0x7c0802a6),
            'tt_online_event':(0x25cde78,0x9421ffd8),'tt_list_build':(0x25c6584,0x3d80ffff),
            'tt_footer':(0x2585b00,0x9421ff88),'tt_ghost_event':(0x25c81e8,0x9421ffe0),
            'tt_ghost_enter':(0x25c79e8,0x9421ff70),'tt_personal_get':(0x24f2714,0x7c0802a6),
            'tt_mgr_start':(0x24f22ac,0x7c0802a6),'tt_name_generate':(0x24f400c,0x9421ff78),
            'tt_directory':(0x24cdc98,0x9421ffd8),'tt_personal_reload':(0x24f0a04,0x7c0802a6),
            'tt_remove':(0x24f2944,0x7c0802a6)})
        flags += ['-DENABLE_TT_GHOST_SCOPE', f'-Wl,--defsym,tt_options_import=0x{meta["symbols"]["settings_import"]:x}']
        call_patches[0x025c9d1c] = ('tt_staff_format', patch.branch(0x025c9d1c, 0x02740e1c)|1)
    for name, (address, expected) in hooks.items():
        if rpxlib.word_at(sections, address) != expected:
            raise ValueError("Unknown/already patched boundary " + name)
    relocations = {a for s in sections if s['name'] == '.rela.text' for a, _, _ in struct.iter_unpack('>III', s['data'])}
    patch.check_relocation_overlap([a for a, _ in hooks.values()]+list(call_patches), relocations)
    code = next(s for s in sections if s['addr'] == 0x02b10000)
    data = next(s for s in sections if s['addr'] == 0x10300000)
    cb = (code['addr']+len(code['data'])+4095)&~4095
    db = (data['addr']+len(data['data'])+4095)&~4095
    generated = Path(__file__).resolve().parents[1]/'work/tt_categories'
    with tempfile.TemporaryDirectory() as directory:
        try:
            text, state, symbols = game_options.compile_module(Path(directory), code_address=cb, data_address=db,
                hooks=hooks, source=Path(__file__).parent/'native/tt_wire_module.c',
                cflags=(f'-I{generated}', f'-I{Path(__file__).parent / "native"}', f'-Wl,--defsym,pink_enabled=0x{pink:x}',
                        f'-Wl,--defsym,tt_options_country=0x{meta["symbols"]["selected_country"]:x}', *flags), data_limit=0x20000)
        except Exception as error:
            if hasattr(error, 'stderr'): print(error.stderr)
            raise
    code['data'] += bytes(cb-code['addr']-len(code['data'])) + text
    data['data'] += bytes(db-data['addr']-len(data['data'])) + state
    for name, (address, _) in hooks.items():
        section = next(s for s in sections if s['addr'] <= address < s['addr']+len(s['data']))
        body = bytearray(section['data'])
        struct.pack_into('>I', body, address-section['addr'], patch.branch(address, symbols[name]))
        section['data'] = bytes(body)
    for address, (name, expected) in call_patches.items():
        if rpxlib.word_at(sections,address)!=expected:raise ValueError('Unknown staff filename format call')
        section=next(s for s in sections if s['addr']<=address<s['addr']+len(s['data']))
        body=bytearray(section['data']);struct.pack_into('>I',body,address-section['addr'],patch.branch(address,symbols[name])|1);section['data']=bytes(body)
    # This pool uses CTGP's existing special game_server_id, not vanilla EB00.
    for address, vanilla, ctgp in [(0x023d5628, 0x38e7eb00, 0x38e7eb01), (0x023e8c58, 0x38a5eb00, 0x38a5eb01)]:
        if rpxlib.word_at(sections, address) not in (vanilla, ctgp):
            raise ValueError('Unknown server-ID instruction')
        section = next(s for s in sections if s['addr'] <= address < s['addr']+len(s['data']))
        body = bytearray(section['data'])
        struct.pack_into('>I', body, address-section['addr'], ctgp)
        section['data'] = bytes(body)
    # These legacy "country" hooks actually intercept steering-use accessors.
    # Restore their ORIGINAL instructions; the profile copy above is the proper
    # country boundary. Do not mutate controller state or falsify replay flags.
    for address, name, native in [(0x024cb344, 'country_get', 0x81630034), (0x024cc5bc, 'country_local_get', 0x7c0802a6)]:
        if rpxlib.word_at(sections, address) != patch.branch(address, meta['symbols'][name]):
            raise ValueError('Unknown legacy controller accessor hook')
        section = next(s for s in sections if s['addr'] <= address < s['addr']+len(s['data']))
        body = bytearray(section['data'])
        struct.pack_into('>I', body, address-section['addr'], native)
        section['data'] = bytes(body)
    info = next(s for s in sections if s['t'] == 0x80000004)
    body = bytearray(info['data'])
    for offset, end, base in [(4, cb+len(text), 0x02000000), (12, db+len(state), 0x10000000)]:
        struct.pack_into('>I', body, offset, max(struct.unpack_from('>I', body, offset)[0], ((end+255)&~255)-base))
    info['data'] = bytes(body)
    output.write_bytes(patch.repack(raw, sections))
    _, checked = rpxlib.load(output)
    for section in sections:
        if section['t'] != 0x80000003:
            assert next(s['data'] for s in checked if s['i'] == section['i']) == section['data']
    meta['symbols'].update(symbols)
    meta.update(output_sha256=hashlib.sha256(output.read_bytes()).hexdigest(), runtime_verified=False,
                typed_wire_source_sha256=hashlib.sha256(raw).hexdigest(),
                wire_header_sha256=hashlib.sha256((generated/'wire_catalog.h').read_bytes()).hexdigest(), game_server_id='1010EB01', restored_controller_accessors=True, scoped_ghosts=bool(ghosts))
    Path(str(output)+'.json').write_text(json.dumps(meta, indent=2))


if __name__ == '__main__':
    import sys
    build(*sys.argv[1:3], ghosts='--ghosts' in sys.argv[3:])
