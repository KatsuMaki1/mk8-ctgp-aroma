#!/usr/bin/env python3
"""Inspect and stage the Wii U Mario Sunshine mod without replacing vanilla Mario.

Staging never replaces vanilla Mario. The explicit activate/restore commands
provide a reversible model-only test; an in-game selector needs a runtime patch.
None of these commands changes DLC rights.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import struct
import tempfile
import zipfile

import szs


PREFIX = 'Mario (Sunshine)/over Mario/content/'
MODEL = 'driver/Mario.szs'
VOICE = 'audio/driver_menu/SNDG_M_Mario.bars'
HUD_SOURCE = 'ui/cmn/a_race/timg/ym_HornEmblemMario_00^h.bflim'
HUD_TARGET = 'ui/cmn/a_race/timg/ym_HornEmblemMario_01^h.bflim'
MAX_RESOURCE_SIZE = 32 * 1024 * 1024


def bfres_names(data, field):
    """Read names from a Wii U BFRES relative-pointer resource dictionary."""
    relative, = struct.unpack_from('>i', data, field)
    if not relative:
        return []
    start = field + relative
    if not 0 <= start <= len(data) - 8:
        raise ValueError('BFRES dictionary outside the file')
    size, count = struct.unpack_from('>II', data, start)
    if size < 8 + (count + 1) * 16 or start + size > len(data):
        raise ValueError('Invalid BFRES dictionary size')
    names = []
    for index in range(count):
        at = start + 8 + (index + 1) * 16 + 8
        offset = at + struct.unpack_from('>i', data, at)[0]
        if not 0 <= offset < len(data):
            raise ValueError('BFRES name outside the file')
        end = data.find(bytes(1), offset)
        if end < 0:
            raise ValueError('Unterminated BFRES name')
        names.append(data[offset:end].decode('utf-8'))
    return names


def inspect_model(packed):
    if packed[:4] != b'Yaz0' or len(packed) < 16:
        raise ValueError('Expected a Yaz0-compressed Wii U model')
    size, = struct.unpack_from('>I', packed, 4)
    if not 0x6c <= size <= MAX_RESOURCE_SIZE:
        raise ValueError('Unexpected decoded model size')
    data = szs.yaz0_decode(packed)
    if data[:8] != b'FRES' + bytes.fromhex('03040004') or data[8:10] != bytes.fromhex('feff'):
        raise ValueError('Expected a Wii U BFRES v3.4.0.4 model')
    if struct.unpack_from('>I', data, 12)[0] != len(data):
        raise ValueError('BFRES file size does not match its header')
    return {
        'sha256': hashlib.sha256(packed).hexdigest(),
        'packed_bytes': len(packed),
        'decoded_bytes': len(data),
        'models': bfres_names(data, 0x20),
        'textures': bfres_names(data, 0x24),
        'skeletal_animations': bfres_names(data, 0x28),
    }


def read_sunshine(archive, base_content):
    with zipfile.ZipFile(archive) as source:
        payloads = {}
        for name in (MODEL, VOICE):
            entries = [entry for entry in source.infolist() if entry.filename == PREFIX + name]
            if len(entries) != 1 or entries[0].file_size > MAX_RESOURCE_SIZE:
                raise ValueError('Missing, duplicate or oversized archive member: ' + PREFIX + name)
            payloads[name] = source.read(entries[0])
    mod = inspect_model(payloads[MODEL])
    vanilla = inspect_model((Path(base_content) / MODEL).read_bytes())
    if mod['models'] != vanilla['models']:
        raise ValueError('Model resource names differ from vanilla Mario')
    missing = sorted(set(vanilla['skeletal_animations']) - set(mod['skeletal_animations']))
    if missing:
        raise ValueError('Missing Mario animations: ' + ', '.join(missing))
    if payloads[VOICE][:4] != b'SARC':
        raise ValueError('Unexpected selection voice archive format')
    report = {
        'format': 'mk8-costume-v1',
        'character': 'Mario', 'character_id': 0,
        'costume': 'Sunshine', 'costume_id': 1,
        'status': 'resources-staged-runtime-selector-required',
        'archive_sha256': hashlib.sha256(Path(archive).read_bytes()).hexdigest(),
        'model': mod,
        'vanilla_model_sha256': vanilla['sha256'],
        'missing_skeletal_animations': missing,
        'resources': {
            name: {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}
            for name, data in payloads.items()
        },
        'notes': [
            'Original Mario files are not replaced.',
            'Matching resource and animation names are static checks, not an in-game compatibility test.',
            'Selection voice is staged separately; global Mario audio is not replaced.',
        ],
    }
    return report, payloads


def stage_sunshine(archive, base_content, content):
    report, payloads = read_sunshine(archive, base_content)
    destination = Path(content) / 'custom' / 'costumes' / 'Mario' / 'Sunshine'
    output = {destination / name: data for name, data in payloads.items()}
    output[destination / 'manifest.json'] = (json.dumps(report, indent=2) + '\n').encode('utf-8')
    # Refuse conflicting resources before writing anything. Repeating the same
    # import is safe, but never overwrite a different costume silently.
    for path, data in output.items():
        if path.exists() and path.read_bytes() != data:
            raise ValueError('A different staged resource already exists: ' + str(path))
    for path, data in output.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            with path.open('xb') as target:
                target.write(data)
    prepare_sunshine_hud(base_content, content)
    return destination, report


def atomic_write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.costume-', delete=False) as target:
            temporary = Path(target.name)
            target.write(data)
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def install_staged_sunshine_hud(content):
    """Provide the native horn emblem requested for Mario's custom variant 1."""
    content = Path(content).resolve()
    staged = content / 'custom/costumes/Mario/Sunshine'
    metadata = json.loads((staged / 'hud_alias.json').read_text(encoding='utf-8'))
    if metadata.get('format') != 'mk8-sunshine-hud-v1' or metadata.get('target') != HUD_TARGET:
        raise ValueError('Unexpected Sunshine HUD dependency manifest')
    payload = (staged / HUD_TARGET).read_bytes()
    if hashlib.sha256(payload).hexdigest() != metadata['sha256']:
        raise ValueError('Staged Sunshine HUD dependency changed')
    if payload[-40:-36] != b'FLIM' or payload[-20:-16] != b'imag':
        raise ValueError('Expected a Wii U BFLIM horn emblem')
    target = content / HUD_TARGET
    if target.exists() and target.read_bytes() != payload:
        raise ValueError('A different Mario variant-1 horn emblem already exists; kept: ' + str(target))
    if not target.exists():
        atomic_write(target, payload)
    return target


def prepare_sunshine_hud(base_content, content):
    content = Path(content).resolve()
    payload = (Path(base_content) / HUD_SOURCE).read_bytes()
    if payload[-40:-36] != b'FLIM' or payload[-20:-16] != b'imag':
        raise ValueError('Expected the base Mario horn emblem to be a Wii U BFLIM')
    staged = content / 'custom/costumes/Mario/Sunshine'
    metadata = {'format': 'mk8-sunshine-hud-v1', 'source': HUD_SOURCE, 'target': HUD_TARGET,
                'sha256': hashlib.sha256(payload).hexdigest(),
                'note': 'Mario variant 1 uses the standard Mario horn emblem; its 3D model remains Sunshine.'}
    entries = {staged / HUD_TARGET: payload,
               staged / 'hud_alias.json': (json.dumps(metadata, indent=2) + '\n').encode()}
    # Preflight every destination, including the active alias, before writing.
    for path, data in {**entries, content / HUD_TARGET: payload}.items():
        if path.exists() and path.read_bytes() != data:
            raise ValueError('Existing HUD resource differs and was preserved: ' + str(path))
    for path, data in entries.items():
        if not path.exists():
            atomic_write(path, data)
    return install_staged_sunshine_hud(content)


def test_paths(content):
    content = Path(content).resolve()
    backup = content.with_name(content.name + '_backups') / 'costumes' / 'MarioSunshineTest'
    return content / MODEL, backup, backup / 'state.json'


def activate_sunshine_test(content):
    """Enable a reversible MODEL-ONLY replacement to validate the supplied asset."""
    content = Path(content).resolve()
    destination = content / 'custom/costumes/Mario/Sunshine'
    manifest = json.loads((destination / 'manifest.json').read_text(encoding='utf-8'))
    packed = (destination / MODEL).read_bytes()
    info = inspect_model(packed)
    if info['sha256'] != manifest['resources'][MODEL]['sha256']:
        raise ValueError('Staged model no longer matches its manifest')
    target, backup, state_path = test_paths(content)
    if state_path.exists():
        state = json.loads(state_path.read_text(encoding='utf-8'))
        if state['content'] != str(content) or state['test_sha256'] != info['sha256']:
            raise ValueError('Another model test has a saved rollback state')
        current = hashlib.sha256(target.read_bytes()).hexdigest() if target.exists() else None
        if current == state['test_sha256']:
            return target
        if current != state['previous_sha256']:
            raise ValueError('Mario override changed outside the test; refusing to replace it')
    else:
        previous = target.read_bytes() if target.exists() else None
        state = {
            'format': 'mk8-costume-model-test-v1',
            'content': str(content),
            'previous_sha256': hashlib.sha256(previous).hexdigest() if previous is not None else None,
            'test_sha256': info['sha256'],
            'note': 'Temporary model replacement only. No in-game selector installed.',
        }
        backup.mkdir(parents=True, exist_ok=True)
        if previous is not None:
            prior_path = backup / 'Mario.szs.previous'
            if prior_path.exists() and prior_path.read_bytes() != previous:
                raise ValueError('A different previous Mario override is already backed up')
            if not prior_path.exists():
                with prior_path.open('xb') as saved:
                    saved.write(previous)
        atomic_write(state_path, (json.dumps(state, indent=2) + '\n').encode('utf-8'))
    atomic_write(target, packed)
    if hashlib.sha256(target.read_bytes()).hexdigest() != state['test_sha256']:
        raise ValueError('Installed test model verification failed')
    return target


def restore_sunshine_test(content):
    """Restore the previous update override, or remove only our temporary override."""
    content = Path(content).resolve()
    target, backup, state_path = test_paths(content)
    state = json.loads(state_path.read_text(encoding='utf-8'))
    if state['content'] != str(content):
        raise ValueError('Rollback state belongs to another content folder')
    current = hashlib.sha256(target.read_bytes()).hexdigest() if target.exists() else None
    if current == state['previous_sha256']:
        return target
    if current != state['test_sha256']:
        raise ValueError('Mario override changed outside the test; refusing to restore over it')
    if state['previous_sha256'] is None:
        target.unlink()
    else:
        previous = (backup / 'Mario.szs.previous').read_bytes()
        if hashlib.sha256(previous).hexdigest() != state['previous_sha256']:
            raise ValueError('Previous Mario backup failed verification')
        atomic_write(target, previous)
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('inspect-sunshine', 'stage-sunshine', 'prepare-sunshine-hud',
                                          'activate-sunshine-test', 'restore-sunshine-test'))
    parser.add_argument('--archive')
    parser.add_argument('--base-game', help='Base game content folder')
    parser.add_argument('--content', help='Update/mod content folder; required for staging')
    args = parser.parse_args()
    if args.command == 'prepare-sunshine-hud':
        if not args.content or not args.base_game:
            parser.error('prepare-sunshine-hud requires --base-game and --content')
        print('Mario variant-1 horn emblem:', prepare_sunshine_hud(args.base_game, args.content))
        return
    if args.command in ('activate-sunshine-test', 'restore-sunshine-test'):
        if not args.content:
            parser.error(args.command + ' requires --content')
        operation = activate_sunshine_test if args.command == 'activate-sunshine-test' else restore_sunshine_test
        print(operation(args.content))
        print('Model-only test ' + ('activated. No in-game selector installed.'
                                   if args.command == 'activate-sunshine-test' else 'restored.'))
        return
    if not args.archive or not args.base_game:
        parser.error(args.command + ' requires --archive and --base-game')
    if args.command == 'stage-sunshine':
        if not args.content:
            parser.error('stage-sunshine requires --content')
        destination, report = stage_sunshine(args.archive, args.base_game, args.content)
        print('Staged resources:', destination)
        print('Runtime selector is not enabled by this command.')
    else:
        report, _ = read_sunshine(args.archive, args.base_game)
    print('Models:', ', '.join(report['model']['models']))
    print('Skeletal animations:', len(report['model']['skeletal_animations']))
    print('Missing vanilla animations:', len(report['missing_skeletal_animations']))


if __name__ == '__main__':
    main()
