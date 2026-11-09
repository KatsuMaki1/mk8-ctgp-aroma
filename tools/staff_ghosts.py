"""Stage recorded Wii U ghosts by CT/revision/cc/rules, without changing inputs.

The scoped native TT loader reads these sg files; the manifest records provenance.
Replay validation in-game is still required before distributing a staff recording.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import zlib

RULES = ('mk8-u81-native-v1', 'ctgp-pink-charge150-boost150-v1')


def payload(data):
    if data[:4] == b'CTG0':
        if len(data) < 0x48:
            raise ValueError('Truncated CTG0 header')
        if struct.unpack_from('>I', data, 8)[0] != len(data):
            raise ValueError('CTG0 file size mismatch')
        if struct.unpack_from('>I', data, 0x38)[0] != zlib.crc32(data[0x48:]):
            raise ValueError('CTG0 checksum mismatch')
        data = data[0x48:]
    if not 0x400 <= len(data) <= 2 << 20:
        raise ValueError('Unsupported ghost size')
    return data


def stage(catalog, track, cc, rules, ghost, name, content):
    if cc not in (150, 200) or rules not in RULES:
        raise ValueError('Unsupported TT category')
    if not 1 <= len(name) <= 32:
        raise ValueError('Staff display name must be 1..32 characters')
    entries = json.loads(Path(catalog).read_text(encoding='utf-8'))['tracks']
    matches = [row for row in entries if row['id'] == track]
    if len(matches) != 1:
        raise ValueError('Track not uniquely present in catalog')
    row = matches[0]
    if not re.fullmatch(r'[a-z0-9._-]+', track) or not re.fullmatch(r'[0-9a-f]{64}', row['revision']):
        raise ValueError('Unsafe catalog identity')
    source = Path(ghost)
    if not re.fullmatch(r'(gs|dg|sg)(?:[0-9a-fA-F]{98}|[0-9a-fA-F]{100}|[0-9a-fA-F]{112})\.dat', source.name):
        raise ValueError('Keep the original Wii U ghost filename (gs/dg/sg...dat)')
    original = source.read_bytes()
    body = payload(original)
    native_course = struct.unpack_from('>I', body, 0x17c)[0]
    filename_course = int(source.name[4:6], 16)
    if struct.unpack_from('>I', body)[0] != 0x400 or not 0x10 <= native_course < 0x50:
        raise ValueError('Invalid native Wii U ghost information section')
    if filename_course != native_course:
        raise ValueError('Ghost filename course does not match the recording')
    if source.name[:2] != 'dg' and int(source.name[2:4], 16) != native_course - 0x10:
        raise ValueError('Ghost filename slot does not match its native course')
    digest = hashlib.sha256(body).hexdigest()
    # Downloaded dg files use a cache slot (0..15), NOT the staff course slot.
    # Change filename metadata only; never edit recorded inputs or payload IDs.
    staff_name = 'sg' + f'{native_course - 0x10:02x}' + source.name[4:]
    relative = Path('custom/tt_staff') / track / row['revision'][:8] / str(cc) / ('p1' if rules == RULES[1] else 'n1') / staff_name
    if len(relative.as_posix().encode('utf-8')) + 2 > 256:
        raise ValueError('Staff ghost path exceeds the native 256-byte buffer')
    content = Path(content)
    destination = content / relative
    manifest = content / 'custom/tt_staff/manifest.json'
    records = json.loads(manifest.read_text(encoding='utf-8')) if manifest.exists() else {'version': 1, 'ghosts': []}
    key = (track, row['revision'], cc, rules, digest)
    for existing in records['ghosts']:
        if tuple(existing[k] for k in ('track', 'revision', 'cc', 'rules', 'sha256')) == key:
            return existing
    if destination.exists() and destination.read_bytes() != body:
        raise FileExistsError('A different recording uses this filename in the same category')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('xb') if not destination.exists() else destination.open('rb') as stream:
        if stream.writable():
            stream.write(body)
    record = dict(track=track, revision=row['revision'], cc=cc, rules=rules, name=name,
                  path=relative.as_posix(), sha256=digest,
                  source_sha256=hashlib.sha256(original).hexdigest(),
                  native_course=native_course,
                  category_asserted_by_importer=True, replay_validated=False)
    records['ghosts'].append(record)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    temporary = manifest.with_suffix('.json.tmp')
    with temporary.open('x', encoding='utf-8') as stream:
        json.dump(records, stream, ensure_ascii=False, indent=2)
    temporary.replace(manifest)
    return record


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--catalog', type=Path, required=True)
    parser.add_argument('--track', required=True)
    parser.add_argument('--cc', type=int, choices=(150, 200), required=True)
    parser.add_argument('--rules', choices=RULES, default=RULES[0])
    parser.add_argument('--ghost', type=Path, required=True)
    parser.add_argument('--name', required=True)
    parser.add_argument('--content', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(stage(args.catalog, args.track, args.cc, args.rules, args.ghost, args.name, args.content), indent=2))
