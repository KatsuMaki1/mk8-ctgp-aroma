from pathlib import Path
import json,sys,tempfile,unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import character_install as i

class Transactions(unittest.TestCase):
    def test_install_restore_existing_and_new_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            content=Path(tmp)/'update/content';content.mkdir(parents=True)
            existing=content/'common/mush/Parts.bin';existing.parent.mkdir(parents=True);existing.write_bytes(b'before')
            new=content/'custom/characters/ROB/driver/Morton.szs'
            with patch.object(i.patch,'ensure_cemu_closed'),patch.object(i,'plan',return_value=({existing:b'after',new:b'private'},{})):
                state=i.install(content,None,None,None)
            self.assertEqual(state['status'],'installed-awaiting-cemu-test')
            self.assertEqual(existing.read_bytes(),b'after');self.assertEqual(new.read_bytes(),b'private')
            with patch.object(i.patch,'ensure_cemu_closed'):i.restore(content)
            self.assertEqual(existing.read_bytes(),b'before');self.assertFalse(new.exists())

    def test_failed_second_write_restores_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            content=Path(tmp)/'update/content';content.mkdir(parents=True)
            first=content/'first';second=content/'second';first.write_bytes(b'old');second.write_bytes(b'other')
            real=i.costumes.atomic_write
            def failing(path,data):
                if path==second and data==b'fail':raise OSError('simulated write failure')
                return real(path,data)
            with patch.object(i.patch,'ensure_cemu_closed'),patch.object(i,'plan',return_value=({first:b'new',second:b'fail'},{})),patch.object(i.costumes,'atomic_write',side_effect=failing):
                with self.assertRaises(OSError):i.install(content,None,None,None)
            self.assertEqual(first.read_bytes(),b'old');self.assertEqual(second.read_bytes(),b'other')
            state=json.loads((content.parent/'code_backups/IndependentROB/state.json').read_text())
            self.assertEqual(state['status'],'rolled-back-install-failure')

    def test_revision_tracks_new_dependencies_and_keeps_original_restore(self):
        with tempfile.TemporaryDirectory() as tmp:
            content=Path(tmp)/'update/content';content.mkdir(parents=True)
            first=content/'first';first.write_bytes(b'original')
            audio=content/'Audio.bin';audio.write_bytes(b'old-audio');icon=content/'new-icon'
            with patch.object(i.patch,'ensure_cemu_closed'),patch.object(i,'plan',return_value=({first:b'v1'},{})):
                i.install(content,None,None,None)
            with patch.object(i.patch,'ensure_cemu_closed'):
                i.revise(content,{first:b'v2',audio:b'expanded',icon:b'icon'},'r2',
                         new_files={audio:i.assets.digest(b'old-audio'),icon:None})
                i.restore(content)
            self.assertEqual(first.read_bytes(),b'original');self.assertEqual(audio.read_bytes(),b'old-audio')
            self.assertFalse(icon.exists())

if __name__=='__main__':unittest.main()
