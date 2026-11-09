import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import byml_dump,animal_dependencies,struct

class AnimalDependencies(unittest.TestCase):
    def test_adds_manager_without_spawning_a_spectator(self):
        d={'MapObjIdList':[1139,1137,1013],'MapObjResList':['DL_CmnAnimalA','DL_CmnAnimalC'],
           'Obj':[{'ObjId':1137,'Translate':{'X':1.0,'Y':2.0,'Z':3.0}}]}
        raw=byml_dump.build(d);result,changed=animal_dependencies.fix(raw)
        self.assertTrue(changed);new=byml_dump.parse(result)
        self.assertEqual(new['Obj'],d['Obj']);self.assertEqual(new['MapObjIdList'],[1140,1139,1137,1013])
        self.assertEqual(new['MapObjResList'],d['MapObjResList'])
        self.assertEqual(result[4:20],raw[4:20])
        self.assertEqual(animal_dependencies.fix(result),(result,False))
    def test_other_courses_unchanged(self):
        raw=byml_dump.build({'MapObjIdList':[1044],'MapObjResList':['CmnToad'],'Obj':[]})
        self.assertEqual(animal_dependencies.fix(raw),(raw,False))
    def test_opaque_path_reference_is_not_reserialized(self):
        # A1 is a version1 path-table reference, unsupported by the serializer.
        raw=bytearray(byml_dump.build({'MapObjIdList':[1137],
            'MapObjResList':['DL_CmnAnimalA'],'ObjPt':7}))
        root=struct.unpack_from('>I',raw,16)[0]
        for i in range(int.from_bytes(raw[root+1:root+4],'big')):
            entry=root+4+8*i
            if raw[entry+3]==0xd1:raw[entry+3]=0xa1
        original=byml_dump.parse(raw);self.assertEqual(original['ObjPt'],('?a1',7))
        patched,changed=animal_dependencies.fix(bytes(raw))
        self.assertTrue(changed);self.assertEqual(byml_dump.parse(patched)['ObjPt'],('?a1',7))
        self.assertEqual(patched[12:20],raw[12:20])

if __name__=='__main__':unittest.main()
