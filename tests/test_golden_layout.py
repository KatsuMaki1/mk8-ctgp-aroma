import struct
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import byml_dump
import golden_dash

class GoldenLayoutTests(unittest.TestCase):
    def test_native_layout_and_scalar_roundtrip(self):
        value=[{'ObjId':7025,'Label':'VRMenu','ResName':['VRMenu'],
                'Item':[0,1],'nested':{'enabled':True,'signed':-1,'unsigned':0xffffffff,'float':1.25,'empty':None}}]
        raw=byml_dump.build(value)
        self.assertEqual(byml_dump.parse(raw),value)
        kt,st,_,root=struct.unpack_from('>4I',raw,4)
        self.assertLess(kt,st);self.assertLess(st,root)
        self.assertEqual(golden_dash.table(raw,kt),sorted(golden_dash.table(raw,kt)))
        self.assertEqual(golden_dash.table(raw,st),sorted(golden_dash.table(raw,st)))
        def walk(t,pos):
            if t==0xc0:
                count=struct.unpack_from('>I',raw,pos)[0]&0xffffff
                for i in range(count):
                    typ=raw[pos+4+i];child=struct.unpack_from('>I',raw,pos+4+((count+3)&~3)+4*i)[0]
                    if typ in (0xc0,0xc1):self.assertGreater(child,pos);walk(typ,child)
            elif t==0xc1:
                count=struct.unpack_from('>I',raw,pos)[0]&0xffffff
                for i in range(count):
                    word,child=struct.unpack_from('>II',raw,pos+4+8*i);typ=word&255
                    if typ in (0xc0,0xc1):self.assertGreater(child,pos);walk(typ,child)
        walk(0xc0,root)

    def test_merge_preserves_menu_and_other_objects(self):
        def obj(id,label,count=4):
            return {'ObjId':id,'Label':label,'ResName':[label],
                    'Item':[0]*count,'ItemObj':[0]*count,'Kart':[0]*count,'KartObj':[0]*count}
        original=[obj(1018,'Coin'),obj(7025,'VRMenu')]
        source=[obj(1018,'ChangedCoin'),obj(7061,'VRCnsw12',5)]
        merged,added=golden_dash.merge_objects(byml_dump.build(original),byml_dump.build(source),[1018,7061])
        result={o['ObjId']:o for o in byml_dump.parse(merged)}
        self.assertEqual(added,[7061])
        for o in original:self.assertEqual(result[o['ObjId']],o)
        self.assertEqual(len(result[7061]['Kart']),4)

if __name__=='__main__':unittest.main()
