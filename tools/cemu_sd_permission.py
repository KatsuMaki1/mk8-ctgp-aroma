"""Grant only SD mounting to a Cemu test title, preserving the original manifest."""
from pathlib import Path
import argparse
import re


def enable(path):
    path = Path(path).resolve(strict=True)
    original = path.read_bytes()
    pattern = rb'(<group\b[^>]*>\s*11\s*</group>\s*<mask\b[^>]*>)([0-9a-fA-F]{16})(</mask>)'
    matches = list(re.finditer(pattern, original))
    if len(matches) != 1:
        raise ValueError('Expected exactly one filesystem capability group (11)')
    match = matches[0]
    old = int(match[2], 16)
    new = old | (1 << 19)
    if old == new:
        return {'path': str(path), 'changed': False}
    backup = path.with_name(path.name + '.before_ctgp_sd')
    if backup.exists() and backup.read_bytes() != original:
        raise ValueError('An earlier, different backup already exists')
    if not backup.exists():
        backup.write_bytes(original)
    updated = original[:match.start(2)] + f'{new:016X}'.encode() + original[match.end(2):]
    # Replace the directory entry: the sandbox manifest may be hardlinked.
    temporary = path.with_name(path.name + '.ctgp_sd_tmp')
    with temporary.open('xb') as stream:
        stream.write(updated)
    temporary.replace(path)
    assert (old ^ new) == 1 << 19
    return {'path': str(path), 'changed': True, 'old': f'{old:016X}', 'new': f'{new:016X}', 'backup': str(backup)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('cos_xml', type=Path)
    print(enable(parser.parse_args().cos_xml))
