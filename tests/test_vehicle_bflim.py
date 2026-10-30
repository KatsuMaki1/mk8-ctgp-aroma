import io,struct,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from PIL import Image
import bflim

class BC3Tests(unittest.TestCase):
    def test_native_surface_has_no_overlapping_blocks(self):
        offsets={bflim.addr_2d_thin1(x,y,128,64,1,0) for y in range(32) for x in range(64)}
        self.assertEqual(offsets,set(range(0,32768,16)))

    def test_bc3_texture_matches_independent_dds_decode(self):
        image=Image.new('RGBA',(200,128))
        image.putdata([(x%256,y*2%256,(x+y)%256,255 if x>y else 0) for y in range(128) for x in range(200)])
        footer=bytearray(40);footer[:4]=b'FLIM';footer[20:24]=b'imag'
        struct.pack_into('>HHHBBI',footer,28,200,128,8192,23,0x24,32768)
        result=bflim.encode_bc3(image,bytes(32768)+footer)
        dds=io.BytesIO();image.save(dds,format='DDS',pixel_format='DXT5');dds.seek(0)
        self.assertEqual(bflim.decode_bc3(result).tobytes(),Image.open(dds).convert('RGBA').tobytes())
        self.assertEqual(len(result),32808)

if __name__=='__main__':unittest.main()
