"""Character expansion must preserve both native and modded vehicle records."""
import struct, sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
import character_tables as tables

def fixture(magic, axes):
    tags=list(axes)+[b'TEST'];base=16+4*len(tags)
    out=bytearray(base);out[:4]=magic
    struct.pack_into('>HH',out,8,len(tags),base)
    offsets=[]
    for tag in tags:
        offsets.append(len(out)-base)
        if tag == b'TEST':out.extend(b'TEST'+bytes(28));continue
        ax,ay,stride=axes[tag];x=37 if ax else 1;y=42 if tag==b'BDDR' else 14 if tag==b'WDDR' else 1
        pool=b'Mro'+bytes(1)+b'Mtn'+bytes(1) if tag in (b'DRVR',b'DRSE') else b''
        out.extend(tag+struct.pack('>HHI',x,y,12+x*y*stride if pool else 0))
        for i in range(x*y):
            record=bytearray(bytes([i%251])*stride)
            if pool:struct.pack_into('>I',record,16 if tag==b'DRVR' else 0,4 if i==28 else 0)
            out.extend(record)
        out.extend(pool)
    struct.pack_into('>I',out,4,len(out))
    struct.pack_into('>%dI'%len(tags),out,16,*offsets)
    return bytes(out)

class CharacterTablesTest(unittest.TestCase):
    def test_independent_model_identity_changes_only_new_identity_bytes(self):
        raw=bytearray(fixture(b'PRTS',tables.PART_AXES));base,items=tables.read_sections(raw)
        section=base
        for tag,data in items:
            if tag==b'DTOM':
                for i in range(37):raw[section+12+i*4:section+16+i*4]=bytes([i,i,0,0])
            section+=len(data)
        expanded=tables.expand(bytes(raw));new=tables.independent_model_identity(expanded)
        self.assertEqual(len(new),len(expanded))
        changed=[i for i,(a,b) in enumerate(zip(expanded,new)) if a!=b]
        self.assertEqual(len(changed),2);self.assertTrue(all(new[i]==41 for i in changed))
        with self.assertRaises(ValueError):tables.independent_model_identity(expanded,28)
    def test_all_existing_and_cross_vehicle_records_preserved(self):
        old=fixture(b'PRTS',tables.PART_AXES);new=tables.expand(old)
        tables.verify(old,new)
        entries=dict(tables.sections(new)[1])
        self.assertEqual(struct.unpack_from('>HH',entries[b'BDDR'],4),(38,42))
        self.assertEqual(struct.unpack_from('>HH',entries[b'WDDR'],4),(38,14))
        drvr=entries[b'DRVR'];pool=struct.unpack_from('>I',drvr,8)[0]
        self.assertEqual(drvr[pool:],b'Mro'+bytes(1)+b'Mtn'+bytes(1))
        self.assertEqual(drvr[12+37*500:12+38*500],drvr[12+28*500:12+29*500])

    def test_physics_is_exact_morton_copy_and_tamper_is_rejected(self):
        old=fixture(b'PERF',tables.PERF_AXES);new=tables.expand(old)
        tag,section=tables.sections(new)[1][0]
        self.assertEqual(section[12+37*52:12+38*52],section[12+28*52:12+29*52])
        changed=bytearray(new);changed[len(changed)-1]^=1
        with self.assertRaises(ValueError):tables.verify(old,bytes(changed))

    def test_refuses_double_expansion_or_invalid_donor(self):
        old=fixture(b'PERF',tables.PERF_AXES)
        with self.assertRaises(ValueError):tables.expand(tables.expand(old))
        with self.assertRaises(ValueError):tables.expand(old,[{'id':37,'stats_donor':-1}])

    def test_audio_driver_axis_and_pool_preserve_other_audio(self):
        old=fixture(b'AUDO',tables.AUDIO_AXES);new=tables.expand(old)
        tables.verify(old,new)
        rows=dict(tables.read_sections(new)[1]);section=rows[b'DRSE']
        self.assertEqual(struct.unpack_from('>HHI',section,4),(38,1,164))
        self.assertEqual(section[12+37*4:12+38*4],section[12+28*4:12+29*4])

if __name__=='__main__':unittest.main()
