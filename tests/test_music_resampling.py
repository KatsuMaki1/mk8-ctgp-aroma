import unittest,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from console_music import resample
class AudioResamplingTests(unittest.TestCase):
    def test_tone_frequency_and_amplitude_survive_both_directions(self):
        for src,dst in ((22047,32000),(32000,22047)):
            tone=np.sin(2*np.pi*1000*np.arange(src)/src)
            result=resample(np.column_stack((tone,tone)),src,dst)
            expected=np.sin(2*np.pi*1000*np.arange(dst)/dst)
            self.assertEqual(result.shape,(dst,2))
            self.assertLess(np.max(np.abs(result[:,0]-expected)),1e-8)
    def test_downsampling_removes_tones_above_new_nyquist(self):
        tone=np.sin(2*np.pi*14000*np.arange(32000)/32000)
        result=resample(np.column_stack((tone,tone)),32000,22047)
        self.assertLess(np.sqrt(np.mean(result*result)),1e-8)
    def test_original_nyquist_amplitude_is_not_doubled(self):
        tone=(-1.)**np.arange(32000)
        result=resample(np.column_stack((tone,tone)),32000,64000)
        expected=np.cos(np.pi*np.arange(64000)/2)
        self.assertLess(np.max(np.abs(result[:,0]-expected)),1e-8)
if __name__=='__main__':unittest.main()
