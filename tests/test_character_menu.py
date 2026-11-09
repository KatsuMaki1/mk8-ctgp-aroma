import sys,struct,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import character_menu as menus,character_assets as assets,szs

class ArchiveAliasTest(unittest.TestCase):
    def test_hidden_logo_alias_preserves_other_resources(self):
        names=['timg/left.bflim','timg/right.bflim','blyt/character.bflyt']
        old=szs.sarc_write(list(zip(names,[b'left',b'old hidden right',b'keep ROB layout'])))
        left,right,layout=map(szs.sarc_hash,names)
        new=menus.replace_archive(old,{left:b'uploaded CTGP logo'},{},aliases={right:left})
        entries=assets.hashed_entries(new)
        self.assertEqual(entries[left],b'uploaded CTGP logo');self.assertEqual(entries[right],entries[left])
        self.assertEqual(entries[layout],b'keep ROB layout')
        count=struct.unpack_from('>H',new,26)[0]
        ranges={h:(a,b) for h,attr,a,b in struct.iter_unpack('>IIII',new[32:32+16*count])}
        self.assertEqual(ranges[left],ranges[right])
    def test_rejects_alias_cycles_and_missing_targets(self):
        old=szs.sarc_write([('one',b'one'),('two',b'two')]);one,two=map(szs.sarc_hash,['one','two'])
        with self.assertRaises(ValueError):menus.replace_archive(old,{}, {},aliases={one:two,two:one})
        with self.assertRaises(ValueError):menus.replace_archive(old,{}, {},aliases={one:0xffffffff})

if __name__=='__main__':unittest.main()
