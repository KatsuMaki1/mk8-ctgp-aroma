import sys,unittest,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from maple_wigglers import sample_loop,xyz

class WigglerPaths(unittest.TestCase):
    def test_equal_distance_closed_loop_and_world_space_controls(self):
        points=[{'Translate':dict(zip(('X','Y','Z'),v)),'ControlPoints':[{},{}]}
                for v in [(0,2500,0),(100,2500,0),(100,2500,100),(0,2500,100)]]
        out,length=sample_loop(points,40)
        self.assertEqual(length,400)
        for p in out:self.assertEqual(p['ControlPoints'],[p['Translate'],p['Translate']])
        shifted=out[-5:]+out[:-5]
        self.assertEqual(sorted(map(lambda p:xyz(p['Translate']),out)),sorted(map(lambda p:xyz(p['Translate']),shifted)))
        for i in range(40):
            self.assertEqual(out[i],shifted[(i+5)%40])
            self.assertEqual(math.dist(xyz(out[i]['Translate']),xyz(out[(i+1)%40]['Translate'])),10)

if __name__=='__main__':unittest.main()
