import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import booster_object_alias as alias,byml_dump

class BirdAliasTests(unittest.TestCase):
    def test_legacy_definition_and_unrelated_objects_are_preserved(self):
        old=[{'ObjId':1170,'MgrId':1170,'ResName':['Bird'],'Label':'DL_WdBird'}]
        source=[dict(old[0],ResName=['DL_WdBird']),{'ObjId':9020}]
        course={'Obj':[{'ObjId':1170,'UnitIdNum':42,'Params':[2.0]},{'ObjId':5}],
                'MapObjIdList':[1170,5],'MapObjResList':['DL_WdBird'],'LapNumber':3}
        untouched=byml_dump.build({'Obj':[{'ObjId':5}],'MapObjIdList':[5]})
        out,updates,n=alias.prepare(byml_dump.build(old),byml_dump.build(source),
            {'bird':byml_dump.build(course),'other':untouched})
        rows=byml_dump.parse(out);self.assertEqual(rows[0],old[0])
        new=next(r for r in rows if r['ObjId']==n)
        self.assertEqual((n,new['MgrId'],new['ResName']),(9021,1170,['DL_WdBird']))
        self.assertNotIn('other',updates)
        result=byml_dump.parse(updates['bird'])
        course['Obj'][0]['ObjId']=n;course['MapObjIdList'][0]=n
        self.assertEqual(result,course)

if __name__=='__main__':unittest.main()
