#!/usr/bin/env python3
"""Build/install/restore an experimental Mario costume selector for Cemu EUR v81.

Build uses the current CTGP RPX as input and writes a separate candidate. It does
not touch the installed game. Install and restore require Cemu to be closed.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import zlib

import costumes
import rpxlib


CODE = 0x02B18000
DATA = 0x10304000
MARKER = b'MK8_COSTUME_SELECTOR_EUR81_V1'
HOOKS = {
    'main_event': (0x025DBD58, 0x9421FF98),
    'list_event': (0x025D4B04, 0x9421FF20),
    'setup': (0x025A1064, 0x9421FF48),
    'grid': (0x025A0D68, 0x9421FFD0),
    'cell': (0x0259F104, 0x9421FFA0),
    'apply': (0x025669A8, 0x9421FFD0),
}
PREFIX_CALLS = {0x0242E0B0: 0x4BFFDC21, 0x0242E1E0: 0x4BFFDAF1}
PREFIX_SITES = tuple(PREFIX_CALLS)
EXTRA_CFLAGS = []
EXTRA_ASSEMBLY = []
STATIC_PATCHES = {}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def branch(source, target):
    offset = target - source
    if offset % 4 or not -0x2000000 <= offset < 0x2000000:
        raise ValueError('Branch target out of range')
    return 0x48000000 | (offset & 0x03FFFFFC)


def check_relocation_overlap(addresses, relocation_sites):
    # R_PPC_ADDR16_LO/HA relocations target the immediate at instruction+2.
    # Checking only equality with the aligned instruction misses those writes.
    for address in addresses:
        if any(address <= offset < address + 4 for offset in relocation_sites):
            raise ValueError('Relocation overlaps instruction: %08x' % address)


def compiler_tools():
    root = Path(os.environ.get('DEVKITPPC', r'C:\msys64\opt\devkitpro\devkitPPC')) / 'bin'
    suffix = '.exe' if os.name == 'nt' else ''
    gcc, nm = (root / ('powerpc-eabi-' + name + suffix) for name in ('gcc', 'nm'))
    if not gcc.is_file() or not nm.is_file():
        raise ValueError('devkitPPC gcc/nm not found; set DEVKITPPC')
    return gcc, nm


def compile_native(directory, address_map=None):
    import vehicle_catalog
    (directory/'vehicle_catalog.h').write_text(vehicle_catalog.native_header())
    gcc, nm = compiler_tools()
    source = Path(__file__).parent / 'native' / 'costume_selector.c'
    if address_map is not None:
        import re
        # Recompile our own sources at the console layout. Do not relocate
        # arbitrary instruction bytes or rewrite generated binary constants.
        for name in ('costume_selector.c','vehicle_slots.c'):
            text=(source.parent/name).read_text()
            text=re.sub(r'0x[0-9a-fA-F]+',lambda m:hex(address_map(int(m.group(),16))),text)
            (directory/name).write_text(text)
        source=directory/'costume_selector.c'
    assembly = ['.section .text.tramp,"ax",@progbits', '.balign 4']
    for name, (address, original) in HOOKS.items():
        assembly += [f'.global original_{name}', f'original_{name}:',
                     f'.long 0x{original:08x}', f'b return_{name}']
    for index, address in enumerate(PREFIX_SITES):
        assembly += [f'.global costume_prefix_{index}', f'costume_prefix_{index}:',
                     'lwz 0,0(29)', 'cmpwi 0,0', f'beq prefix_mario_{index}',
                     'cmpwi 0,9', f'bne prefix_done_{index}',
                     'lwz 0,4(29)', 'cmpwi 0,1', f'beq prefix_funky_{index}',
                     'cmpwi 0,2', f'bne prefix_done_{index}',
                     'lis 4,costume_prefix_snorlax@ha', 'addi 4,4,costume_prefix_snorlax@l',
                     f'b prefix_done_{index}', f'prefix_funky_{index}:',
                     'lis 4,costume_prefix_funky@ha', 'addi 4,4,costume_prefix_funky@l',
                     f'b prefix_done_{index}', f'prefix_mario_{index}:',
                     'lwz 0,4(29)', 'cmpwi 0,1', f'bne prefix_done_{index}',
                     'lis 4,costume_prefix@ha', 'addi 4,4,costume_prefix@l',
                     f'prefix_done_{index}:', f'b return_prefix_{index}']
    assembly += EXTRA_ASSEMBLY
    asm = directory / 'trampolines.S'
    asm.write_text('\n'.join(assembly) + '\n', encoding='utf-8')
    linker = directory / 'selector.ld'
    return_symbols = ''.join(f'return_{name} = 0x{address + 4:x};\n'
                             for name, (address, _) in HOOKS.items())
    # The patched call sets LR to the real caller's next instruction. Tail-call
    # the original prefix routine so that its return preserves that LR.
    prefix_return=address_map(0x0242bcd0) if address_map else 0x0242bcd0
    return_symbols += ''.join(f'return_prefix_{i} = 0x{prefix_return:x};\n'
                              for i, address in enumerate(PREFIX_SITES))
    linker.write_text(
        return_symbols + f'SECTIONS {{ .text 0x{CODE:x} : {{ *(.text*) *(.rodata*) }} '
        f'.data 0x{DATA:x} : {{ *(.data*) *(.sdata*) BYTE(0) }} '
        '.bss ALIGN(4) : { *(.bss*) *(.sbss*) *(COMMON) } '
        '/DISCARD/ : { *(.comment) *(.eh_frame*) } }\n', encoding='utf-8')
    elf = directory / 'selector.elf'
    command = [str(gcc), '-Os', '-ffreestanding', '-fno-builtin', '-fno-pic',
               '-fno-stack-protector', '-fno-asynchronous-unwind-tables', '-fno-unwind-tables',
               '-mcpu=750', '-m32', '-mbig-endian', '-msdata=none', '-ffixed-r2', '-ffixed-r13',
               *EXTRA_CFLAGS, '-I'+str(directory), '-Wall', '-Wextra', '-Werror', '-nostdlib', '-Wl,--build-id=none',
               '-Wl,-T,' + str(linker), str(source), str(asm), '-lgcc', '-o', str(elf)]
    subprocess.run(command, check=True, capture_output=True, text=True)
    listing = subprocess.check_output([str(nm), '-n', str(elf)], text=True)
    symbols = {}
    for line in listing.splitlines():
        fields = line.split()
        if len(fields) == 3:
            symbols[fields[2]] = int(fields[0], 16)
        elif len(fields) == 2 and fields[0] == 'U':
            raise ValueError('Unresolved native symbol: ' + fields[1])
    _, sections = rpxlib.load(elf)
    text = next(s['data'] for s in sections if s['name'] == '.text')
    data_sections = [s for s in sections if s['name'] in ('.data', '.bss') and s['size']]
    if any(s['addr'] < DATA or s['addr'] + s['size'] > DATA + 0x1000 for s in data_sections):
        raise ValueError('Compiler placed native mutable state outside its writable reservation')
    end = max([DATA] + [s['addr'] + s['size'] for s in data_sections])
    data = bytearray(end - DATA)
    for section in data_sections:
        if section['t'] != 8:
            start = section['addr'] - DATA
            data[start:start + len(section['data'])] = section['data']
    return text, bytes(data), symbols


def repack(header, sections):
    """Rewrite section file offsets and checksums without adding ELF sections."""
    crc = next(s for s in sections if s['t'] == 0x80000003)
    crc['data'] = b''.join(struct.pack('>I', 0 if s is crc or s['t'] == 8
                                      else zlib.crc32(s['data']) & 0xffffffff) for s in sections)
    for s in sections:
        if s['t'] == 8:
            continue
        s['raw'] = (struct.pack('>I', len(s['data'])) + zlib.compress(s['data'], 9)
                    if s['fl'] & 0x08000000 else bytes(s['data']))
        s['size'] = len(s['raw'])
    result_header = bytearray(header[:0x40])
    struct.pack_into('>I', result_header, 0x20, 0x40)
    pos = (0x40 + len(sections) * 40 + 15) & ~15
    for s in sorted((s for s in sections if s['t'] != 8), key=lambda s: s['off']):
        s['new_off'] = pos
        pos = (pos + s['size'] + 15) & ~15
    output = bytearray(pos)
    output[:0x40] = result_header
    for i, s in enumerate(sections):
        struct.pack_into('>10I', output, 0x40 + i * 40, s['n'], s['t'], s['fl'], s['addr'],
                         s.get('new_off', 0), s['size'], s['link'], s['info'], s['align'], s['ent'])
        if s['t'] != 8:
            start = s['new_off']
            output[start:start + len(s['raw'])] = s['raw']
    return bytes(output)


def build(source, output):
    source, output = Path(source).resolve(), Path(output).resolve()
    if source == output:
        raise ValueError('Build must write a separate candidate RPX')
    raw, sections = rpxlib.load(source)
    if any(MARKER in s['data'] for s in sections):
        raise ValueError('Input already contains the selector; rebuild from the saved CTGP baseline')
    game = next(s for s in sections if s['name'] == '.text' and s['addr'] == 0x02000020)
    code = next(s for s in sections if s['name'] == '.text' and s['addr'] == 0x02B10000)
    data = next(s for s in sections if s['name'] == '.data' and s['addr'] == 0x10300000)
    file_info = next(s for s in sections if s['t'] == 0x80000004)
    relocation_sites = set()
    for section in sections:
        if section['name'] == '.rela.text':
            relocation_sites.update(o for o, _, _ in struct.iter_unpack('>III', section['data']))
    expected = {address: original for address, original in HOOKS.values()}
    expected.update(PREFIX_CALLS)
    expected.update({a:pair[0] for a,pair in STATIC_PATCHES.items()})
    check_relocation_overlap(expected, relocation_sites)
    for address, word in expected.items():
        if rpxlib.word_at(sections, address) != word or address in relocation_sites:
            raise ValueError('Unexpected or relocated patch site: %08x' % address)
    with tempfile.TemporaryDirectory(prefix='mk8-selector-build-') as tmp:
        native_text, native_data, symbols = compile_native(Path(tmp))
    if code['addr'] + len(code['data']) > CODE or data['addr'] + len(data['data']) > DATA:
        raise ValueError('Native payload would overlap existing CTGP content')
    text_limit = 0x02000000 + struct.unpack_from('>I', file_info['data'], 4)[0]
    if CODE + len(native_text) > text_limit:
        raise ValueError('Payload exceeds the original text memory reservation')
    changes = []
    game_bytes = bytearray(game['data'])
    for name, (address, original) in HOOKS.items():
        target = symbols['costume_' + name]
        word = branch(address, target)
        struct.pack_into('>I', game_bytes, address - game['addr'], word)
        changes.append({'address': address, 'before': original, 'after': word, 'target': target})
    for i, address in enumerate(PREFIX_SITES):
        target = symbols['costume_prefix_' + str(i)]
        word = branch(address, target) | 1
        struct.pack_into('>I', game_bytes, address - game['addr'], word)
        changes.append({'address': address, 'before': PREFIX_CALLS[address], 'after': word,
                        'target': target, 'link': True})
    for address,(before,after) in STATIC_PATCHES.items():
        struct.pack_into('>I',game_bytes,address-game['addr'],after)
        changes.append({'address':address,'before':before,'after':after,'static':True})
    game['data'] = bytes(game_bytes)
    code['data'] = code['data'] + bytes(CODE - code['addr'] - len(code['data'])) + native_text
    data['data'] = data['data'] + bytes(DATA - data['addr'] - len(data['data'])) + native_data
    info = bytearray(file_info['data'])
    struct.pack_into('>I', info, 12, max(struct.unpack_from('>I', info, 12)[0],
                                      ((DATA + len(native_data) + 255) & ~255) - 0x10000000))
    file_info['data'] = bytes(info)
    result = repack(raw, sections)
    output.parent.mkdir(parents=True, exist_ok=True)
    costumes.atomic_write(output, result)
    manifest = {'format': 'mk8-costume-selector-cemu-eur81-v1', 'status': 'experimental-unverified-in-game',
                'input_sha256': digest(raw), 'output_sha256': digest(result),
                'code_address': CODE, 'code_bytes': len(native_text),
                'data_address': DATA, 'data_bytes': len(native_data), 'changes': changes,
                'symbols': symbols}
    audit(source, output, manifest)
    costumes.atomic_write(str(output) + '.json', (json.dumps(manifest, indent=2) + '\n').encode())
    return manifest


def audit(source, output, manifest):
    original_raw, original = rpxlib.load(source)
    result_raw, result = rpxlib.load(output)
    if digest(original_raw) != manifest['input_sha256'] or digest(result_raw) != manifest['output_sha256']:
        raise ValueError('Candidate/source hash mismatch')
    if len(original) != len(result) or original_raw[:0x20] != result_raw[:0x20]:
        raise ValueError('Unexpected ELF structure change')
    crc = next(s for s in result if s['t'] == 0x80000003)
    for i, (old, new) in enumerate(zip(original, result)):
        if any(old[key] != new[key] for key in ('n', 't', 'fl', 'addr', 'link', 'info', 'align', 'ent')):
            raise ValueError('Section identity changed')
        expected_crc = 0 if new is crc or new['t'] == 8 else zlib.crc32(new['data']) & 0xffffffff
        if struct.unpack_from('>I', crc['data'], i * 4)[0] != expected_crc:
            raise ValueError('CRC mismatch')
        if new['t'] == 0x80000003:
            continue
        if old['addr'] == 0x02000020 and old['name'] == '.text':
            expected = bytearray(old['data'])
            for change in manifest['changes']:
                struct.pack_into('>I', expected, change['address'] - old['addr'], change['after'])
            if new['data'] != expected:
                raise ValueError('Unexpected game code change')
        elif old['addr'] in (0x02B10000, 0x10300000) and old['name'] in ('.text', '.data'):
            if new['data'][:len(old['data'])] != old['data']:
                raise ValueError('Existing CTGP payload changed')
        elif old['t'] == 0x80000004:
            if old['data'][:12] != new['data'][:12] or old['data'][16:] != new['data'][16:]:
                raise ValueError('Unexpected file-info change')
        elif old['data'] != new['data']:
            raise ValueError('Unrelated section changed: ' + old['name'])
    spans = sorted((s['off'], s['off'] + s['size']) for s in result if s['t'] != 8 and s['size'])
    if spans[-1][1] > len(result_raw) or any(a[1] > b[0] for a, b in zip(spans, spans[1:])):
        raise ValueError('Invalid section file layout')
    for change in manifest['changes']:
        expected_branch = change['after'] if change.get('static') else branch(change['address'], change['target']) | int(change.get('link', False))
        if rpxlib.word_at(result, change['address']) != expected_branch:
            raise ValueError('Hook branch verification failed')
    relocations = {offset for section in result if section['name'] == '.rela.text'
                   for offset, _, _ in struct.iter_unpack('>III', section['data'])}
    check_relocation_overlap([change['address'] for change in manifest['changes']], relocations)
    print('PASS: guarded hooks, unchanged CTGP payload and relocations, ELF sections and CRCs')


def ensure_cemu_closed():
    if os.name == 'nt':
        for name in ('Xapfish.exe', 'Cemu.exe'):
            output = subprocess.check_output(['tasklist', '/fi', 'IMAGENAME eq ' + name,
                                              '/fo', 'csv', '/nh'], text=True)
            if ('"' + name.lower() + '"') in output.lower():
                raise ValueError('Close Cemu before installing/restoring this prototype')


def install(candidate, content):
    ensure_cemu_closed()
    content = Path(content).resolve()
    target = content.parent / 'code' / 'Turbo.rpx'
    candidate = Path(candidate).resolve()
    manifest = json.loads(Path(str(candidate) + '.json').read_text())
    payload = candidate.read_bytes()
    if digest(payload) != manifest['output_sha256']:
        raise ValueError('Candidate no longer matches its build manifest')
    backup = content.parent / 'code_backups' / 'MarioCostumeSelector'
    state_path = backup / 'state.json'
    current = target.read_bytes()
    if digest(current) == manifest['output_sha256'] and state_path.exists():
        costumes.install_staged_sunshine_hud(content)
        return target
    original_path = backup / 'Turbo.rpx.before-selector'
    baseline = current
    if digest(current) != manifest['input_sha256']:
        state = json.loads(state_path.read_text())
        if state['target'] != str(target) or digest(current) != state['selector_sha256']:
            raise ValueError('Installed RPX differs from tracked selector')
        baseline = original_path.read_bytes()
        if digest(baseline) != state['baseline_sha256'] or digest(baseline) != manifest['input_sha256']:
            raise ValueError('Saved baseline checksum mismatch')
        audit(original_path, candidate, manifest)
    else:
        audit(target, candidate, manifest)
    for label, variant in (('FunkyKong', 1), ('Snorlax', 2)):
        root = content / 'custom/costumes/DK' / label
        dependency = json.loads((root / 'manifest.json').read_text())
        if digest((root / 'driver/DK.szs').read_bytes()) != dependency['model']['sha256']:
            raise ValueError('Changed DK costume: ' + label)
        if digest((root / dependency['icon']).read_bytes()) != dependency['icon_sha256']:
            raise ValueError('Changed DK icon: ' + label)
        horn = content / ('ui/cmn/a_race/timg/ym_HornEmblemDK_0%d^h.bflim' % variant)
        if not horn.is_file(): raise ValueError('Missing DK variant horn emblem')
    model_manifest = json.loads((content / 'custom/costumes/Mario/Sunshine/manifest.json').read_text())
    model = content / 'custom/costumes/Mario/Sunshine/driver/Mario.szs'
    if digest(model.read_bytes()) != model_manifest['resources']['driver/Mario.szs']['sha256']:
        raise ValueError('Missing or changed Sunshine model')
    _, _, test_state_path = costumes.test_paths(content)
    if (content / 'driver/Mario.szs').exists():
        if not test_state_path.exists():
            raise ValueError('Unknown Mario override; restore it before installing the selector')
        test_state = json.loads(test_state_path.read_text())
        actual = digest((content / 'driver/Mario.szs').read_bytes())
        if actual not in (test_state['test_sha256'], test_state['previous_sha256']):
            raise ValueError('Mario override was edited outside the model test')
    backup.mkdir(parents=True, exist_ok=True)
    original_path = backup / 'Turbo.rpx.before-selector'
    if original_path.exists() and original_path.read_bytes() != baseline:
        raise ValueError('A different baseline RPX is already backed up')
    if not original_path.exists():
        with original_path.open('xb') as saved:
            saved.write(baseline)
    costumes.atomic_write(backup / ('Turbo.rpx.previous-' + digest(current)[:12]), current)
    state = {'baseline_sha256': digest(baseline), 'selector_sha256': digest(payload), 'target': str(target)}
    costumes.atomic_write(state_path, (json.dumps(state, indent=2) + '\n').encode())
    if test_state_path.exists():
        costumes.restore_sunshine_test(content)
    costumes.install_staged_sunshine_hud(content)
    costumes.atomic_write(target, payload)
    return target


def restore(content):
    ensure_cemu_closed()
    content = Path(content).resolve()
    target = content.parent / 'code' / 'Turbo.rpx'
    backup = content.parent / 'code_backups' / 'MarioCostumeSelector'
    state = json.loads((backup / 'state.json').read_text())
    if str(target) != state['target']:
        raise ValueError('Restore state belongs to another installation')
    original = (backup / 'Turbo.rpx.before-selector').read_bytes()
    if digest(original) != state['baseline_sha256']:
        raise ValueError('Baseline backup checksum failed')
    current = digest(target.read_bytes())
    if current == state['baseline_sha256']:
        return target
    if current != state['selector_sha256']:
        raise ValueError('Installed RPX changed outside the prototype; refusing to overwrite it')
    costumes.atomic_write(target, original)
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('build', 'audit', 'install', 'restore'))
    parser.add_argument('--rpx')
    parser.add_argument('--out')
    parser.add_argument('--candidate')
    parser.add_argument('--content')
    args = parser.parse_args()
    try:
        if args.command in ('build', 'audit'):
            if not args.rpx or not args.out:
                parser.error('build/audit require --rpx and --out')
            if args.command == 'build':
                manifest = build(args.rpx, args.out)
                print('Candidate:', args.out, '| native code:', manifest['code_bytes'], 'bytes')
            else:
                manifest = json.loads(Path(args.out + '.json').read_text())
                audit(args.rpx, args.out, manifest)
        elif args.command == 'install':
            if not args.content or not args.candidate:
                parser.error('install requires --content and --candidate')
            print('Installed experimental selector:', install(args.candidate, args.content))
        else:
            if not args.content:
                parser.error('restore requires --content')
            print('Restored:', restore(args.content))
    except (ValueError, subprocess.CalledProcessError) as error:
        if isinstance(error, subprocess.CalledProcessError):
            print(error.stderr or error.stdout or str(error))
        parser.exit(1, str(error) + '\n')


if __name__ == '__main__':
    main()
