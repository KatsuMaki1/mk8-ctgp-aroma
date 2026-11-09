"""Build a native-layout red TT background pane, hidden unless enabled by code."""
import argparse
from pathlib import Path
import struct
import subprocess
import tempfile
import bflyt
import szs
import character_menu

LAYOUT = szs.sarc_hash('blyt/mn_Background_00.bflyt')


def layout(data):
    parts = [(tag, bytearray(data[offset:offset + size])) for tag, offset, size in bflyt.sections(data)]
    if any(tag == 'pic1' and bflyt.cstr(block[12:36]) == 'P_CTGPRedBG_00' for tag, block in parts):
        raise ValueError('Red background pane already exists')
    material_index = next(i for i, (tag, _) in enumerate(parts) if tag == 'mat1')
    material = parts[material_index][1]
    count = struct.unpack_from('>H', material, 8)[0]
    offsets = struct.unpack_from('>' + str(count) + 'I', material, 12)
    materials = [bytearray(material[start:offsets[i + 1] if i + 1 < count else len(material)]) for i, start in enumerate(offsets)]
    donor = next(block for block in materials if bflyt.cstr(block[:28]) == 'P_BlueBG_00')
    red = bytearray(donor)
    red[:28] = b'P_CTGPRedBG_00'.ljust(28, b'\0')
    # Native BFLYT black/white RGBA colors; texture, animation and TEV config stay native.
    red[28:36] = bytes((100, 0, 20, donor[31], 215, 40, 75, donor[35]))
    materials.append(red)
    head = bytearray(material[:12])
    struct.pack_into('>H', head, 8, len(materials))
    position = 12 + 4 * len(materials)
    pointers = []
    for block in materials:
        pointers.append(position)
        position += len(block)
    merged = head + struct.pack('>' + str(len(pointers)) + 'I', *pointers) + b''.join(materials)
    struct.pack_into('>I', merged, 4, len(merged))
    parts[material_index] = ('mat1', merged)
    index = next(i for i, (tag, block) in enumerate(parts) if tag == 'pic1' and bflyt.cstr(block[12:36]) == 'P_BlueBG_00')
    pane = bytearray(parts[index][1])
    pane[12:36] = b'P_CTGPRedBG_00'.ljust(24, b'\0')
    pane[8] &= ~1  # Default hidden: installing the asset alone changes no menu.
    struct.pack_into('>H', pane, 100, count)
    parts.insert(index + 1, ('pic1', pane))
    header = bytearray(data[:struct.unpack_from('>H', data, 6)[0]])
    struct.pack_into('>H', header, 16, len(parts))
    result = header + b''.join(block for _, block in parts)
    struct.pack_into('>I', result, 12, len(result))
    assert len(bflyt.sections(result)) == len(parts)
    return bytes(result)


def build(source, output):
    raw = szs.yaz0_decode(Path(source).read_bytes())
    entries = szs.sarc_info(raw)[0]
    if not any(hashed == LAYOUT for _, _, hashed, _ in entries):
        raise ValueError('Native background layout not found')
    # Preserve unnamed SARC hashes and alignment through the existing helper.
    donor = next(data for _, data, hashed, _ in entries if hashed == LAYOUT)
    merged = character_menu.replace_archive(raw, {LAYOUT: layout(donor)}, {})
    with tempfile.TemporaryDirectory() as temp:
        sarc = Path(temp) / 'menu.sarc'
        packed = Path(temp) / 'menu.szs'
        sarc.write_bytes(merged)
        subprocess.run([r'C:/Program Files/Wiimm/SZS/wszst.exe', 'compress', str(sarc), '--yaz0', '--dest', str(packed)], check=True, capture_output=True)
        result = packed.read_bytes()
        assert szs.yaz0_decode(result) == merged
        Path(output).write_bytes(result)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    build(args.source, args.output)
