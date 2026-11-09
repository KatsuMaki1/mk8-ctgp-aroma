import sys
from pathlib import Path
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from cemu_tt_bridge import ghost_time, downloaded_name

class NativeFilenameTests(unittest.TestCase):
    def test_download_keeps_track_and_inputs_metadata(self):
        name='gs142407000000030620d37702f3d502a21e02b16c93b3e793b3e700570069006c006c00690061006d000000000000310000.dat'
        result=downloaded_name(name,15)
        self.assertEqual(result[:4],'dg0f')
        self.assertEqual(result[4:100],name[4:100])
        self.assertEqual(ghost_time(name),2*60000+13*1000+0x377)
        self.assertTrue(result.endswith('0000.dat'))
    def test_reject_path_and_invalid_slot(self):
        for name,slot in [('../gs'+100*'0'+'.dat',0),('gs'+100*'0'+'.dat',16)]:
            with self.assertRaises(ValueError):downloaded_name(name,slot)

if __name__=='__main__':unittest.main()
