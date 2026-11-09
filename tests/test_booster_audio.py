import sys,struct,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import szs,booster_audio

class Sounds:
    def lookup(self,name):return {'known':0x01000077}.get(name)

class BoosterAudioTests(unittest.TestCase):
    def test_unknown_ids_removed_without_changing_samples(self):
        pool=b'known\0unknown\0';records=[]
        for offset,old in ((0,19),(6,7000)):
            b=bytearray(84);struct.pack_into('>I',b,0,offset);struct.pack_into('>I',b,36,old);records.append(bytes(b))
        head=bytearray(b'BARS\xfe\xff\x00\x20'+bytes(24));struct.pack_into('>6I',head,8,32+168+len(pool),84,32,168,200,len(pool))
        bank=szs.sarc_write([('_param.bin',bytes(head)+b''.join(records)+pool),('known.bfwav',b'unchanged')],{},0x100)
        new,dropped=booster_audio.known_bar(bank,Sounds());entries={n:b for n,b,h in szs.sarc_read(new)}
        param=entries['_param.bin'];self.assertEqual(dropped,['unknown']);self.assertEqual(entries['known.bfwav'],b'unchanged')
        self.assertEqual(struct.unpack_from('>III',param,20),(84,116,len(pool)))
        self.assertEqual(struct.unpack_from('>I',param,68)[0],0x77)
        self.assertEqual(param[116:],pool);self.assertEqual(len(param),struct.unpack_from('>I',param,8)[0])

if __name__=='__main__':unittest.main()
