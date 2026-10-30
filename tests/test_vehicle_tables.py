import struct,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import vehicle_tables as v

def fixture(axes):
    n=len(axes)+1;base=16+4*n;out=bytearray(base);out[:4]=b'PRTS';struct.pack_into('>HH',out,8,n,base)
    offsets=[]
    for tag,(ax,ay) in axes.items():
        offsets.append(len(out)-base);x=v.COUNTS[ax] if ax else 37;y=v.COUNTS[ay] if ay else 1
        out.extend(tag+struct.pack('>HHI',x,y,0))
        for row in range(y):
            for col in range(x): out.extend(struct.pack('>II',row,col))
    offsets.append(len(out)-base);out.extend(b'DRVR'+struct.pack('>HHI',1,1,0x12345678)+b'preserve')
    struct.pack_into('>I',out,4,len(out));struct.pack_into('>%dI'%n,out,16,*offsets);return bytes(out)

class TableTests(unittest.TestCase):
    def test_multiple_distinct_donors_preserve_all_cross_products(self):
        donors={'body':[7,30,7],'tire':[12,11]};original=fixture(v.PART_AXES)
        result=v.expand(original,v.PART_AXES,donors);v.verify(original,result,v.PART_AXES,donors)
        data=dict(v.sections(result)[1])[b'BDTR']
        self.assertEqual(struct.unpack_from('>HH',data,4),(23,42))
        self.assertEqual(struct.unpack_from('>II',data,12+(40*23+22)*8),(30,11))
        self.assertEqual(struct.unpack_from('>II',data,12+(41*23+21)*8),(7,12))
    def test_body_tire_cross_product_keeps_coordinates(self):
        original=fixture(v.PART_AXES);before=bytes(original);expanded=v.expand(original,v.PART_AXES)
        self.assertEqual(original,before)
        data=dict(v.sections(expanded)[1])[b'BDTR'];self.assertEqual(struct.unpack_from('>HH',data,4),(22,40))
        def at(y,x):return struct.unpack_from('>II',data,12+(y*22+x)*8)
        self.assertEqual(at(38,20),(38,20));self.assertEqual(at(39,20),(7,20));self.assertEqual(at(38,21),(38,12));self.assertEqual(at(39,21),(7,12))
        self.assertEqual(dict(v.sections(expanded)[1])[b'DRVR'],dict(v.sections(original)[1])[b'DRVR'])
    def test_repeated_extension_is_rejected(self):
        with self.assertRaises(ValueError):v.expand(v.expand(fixture(v.PART_AXES),v.PART_AXES),v.PART_AXES)
    def test_performance_curves_are_not_extended(self):
        original=fixture(v.PERF_AXES);result=v.expand(original,v.PERF_AXES)
        self.assertEqual(struct.unpack_from('>H',dict(v.sections(result)[1])[b'PTBD'],4)[0],40)
        self.assertEqual(struct.unpack_from('>H',dict(v.sections(result)[1])[b'PTTR'],4)[0],22)

if __name__=='__main__':unittest.main()
