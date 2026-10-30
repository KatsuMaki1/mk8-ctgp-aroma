from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import costumes


class HornDependencyTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='mk8-hud-test-')
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name) / 'base'
        self.content = Path(self.temporary.name) / 'content'
        # Container fixture for copy/hash/conflict tests; no image decoder used.
        payload = bytearray(128)
        payload[-40:-36] = b'FLIM'
        payload[-20:-16] = b'imag'
        self.payload = bytes(payload)
        source = self.base / costumes.HUD_SOURCE
        source.parent.mkdir(parents=True)
        source.write_bytes(self.payload)

    def test_dependency_is_copied_and_repeat_install_is_safe(self):
        target = costumes.prepare_sunshine_hud(self.base, self.content)
        self.assertEqual(target.name, 'ym_HornEmblemMario_01^h.bflim')
        self.assertEqual(target.read_bytes(), self.payload)
        self.assertEqual((self.base / costumes.HUD_SOURCE).read_bytes(), self.payload)
        costumes.prepare_sunshine_hud(self.base, self.content)
        costumes.install_staged_sunshine_hud(self.content)
        self.assertEqual(target.read_bytes(), self.payload)

    def test_conflicting_active_emblem_is_preserved_before_staging(self):
        target = self.content / costumes.HUD_TARGET
        target.parent.mkdir(parents=True)
        target.write_bytes(b'user emblem')
        with self.assertRaises(ValueError):
            costumes.prepare_sunshine_hud(self.base, self.content)
        self.assertEqual(target.read_bytes(), b'user emblem')
        self.assertFalse((self.content / 'custom').exists())

    def test_changed_staged_emblem_is_rejected(self):
        target = costumes.prepare_sunshine_hud(self.base, self.content)
        staged = self.content / 'custom/costumes/Mario/Sunshine' / costumes.HUD_TARGET
        staged.write_bytes(b'changed')
        with self.assertRaises(ValueError):
            costumes.install_staged_sunshine_hud(self.content)
        self.assertEqual(target.read_bytes(), self.payload)


if __name__ == '__main__':
    unittest.main()
