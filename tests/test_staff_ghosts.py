import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
import zlib
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import staff_ghosts


class Ghosts(unittest.TestCase):
    def test_header_validation_and_unchanged_inputs(self):
        body = bytes(range(256)) * 4
        header = bytearray(0x48)
        header[:4] = b'CTG0'
        struct.pack_into('>I', header, 8, len(header) + len(body))
        struct.pack_into('>I', header, 0x38, zlib.crc32(body))
        self.assertEqual(staff_ghosts.payload(header + body), body)
        broken = bytearray(header + body)
        broken[-1] ^= 1
        with self.assertRaisesRegex(ValueError, 'checksum'):
            staff_ghosts.payload(broken)

    def test_categories_and_duplicate_import(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            catalog = root / 'catalog.json'
            catalog.write_text(json.dumps({'tracks': [{'id': 'ct.test', 'revision': 'a' * 64}]}))
            ghost = root / ('sg0010' + '0' * 108 + '.dat')
            original = bytearray(bytes(range(256)) * 4)
            struct.pack_into('>I', original, 0, 0x400)
            struct.pack_into('>I', original, 0x17c, 0x10)
            original = bytes(original)
            ghost.write_bytes(original)
            a = staff_ghosts.stage(catalog, 'ct.test', 150, staff_ghosts.RULES[0], ghost, 'Friend', root / 'content')
            b = staff_ghosts.stage(catalog, 'ct.test', 200, staff_ghosts.RULES[0], ghost, 'Friend', root / 'content')
            self.assertNotEqual(a['path'], b['path'])
            self.assertEqual((root / 'content' / a['path']).read_bytes(), original)
            self.assertFalse(a['replay_validated'])
            staff_ghosts.stage(catalog, 'ct.test', 150, staff_ghosts.RULES[0], ghost, 'Friend', root / 'content')
            records = json.loads((root / 'content/custom/tt_staff/manifest.json').read_text())
            self.assertEqual(len(records['ghosts']), 2)

    def test_download_cache_slot_is_not_reused_as_staff_slot(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            catalog = root / 'catalog.json'
            catalog.write_text(json.dumps({'tracks': [{'id':'ct.test','revision':'a'*64}]}))
            ghost = root / ('dg0035' + '0'*108 + '.dat')
            body = bytearray(0x400)
            struct.pack_into('>I', body, 0, 0x400)
            struct.pack_into('>I', body, 0x17c, 0x35)
            ghost.write_bytes(body)
            record = staff_ghosts.stage(catalog,'ct.test',200,staff_ghosts.RULES[0],ghost,'Staff',root/'content')
            self.assertTrue(Path(record['path']).name.startswith('sg2535'))
            self.assertEqual((root/'content'/record['path']).read_bytes(), body)
            struct.pack_into('>I', body, 0x17c, 0x34)
            ghost.write_bytes(body)
            with self.assertRaisesRegex(ValueError,'does not match'):
                staff_ghosts.stage(catalog,'ct.test',200,staff_ghosts.RULES[0],ghost,'Staff',root/'content')


if __name__ == '__main__':
    unittest.main()
