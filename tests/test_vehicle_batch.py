import copy,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import vehicle_batch as batch
import vehicle_catalog as catalog

class BatchTests(unittest.TestCase):
    def test_catalog_install_and_failed_install_rollback(self):
        for fail in (False,True):
            with self.subTest(fail=fail),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);content=root/'content';prepared=root/'prepared';candidate=root/'candidate.rpx'
                backup=root/'code_backups/VehicleSlots';cs=root/'code_backups/MarioCostumeSelector/state.json';rpx=root/'code/Turbo.rpx'
                for p in (content,prepared,backup,cs.parent,rpx.parent):p.mkdir(parents=True,exist_ok=True)
                old_state={'status':'active','rpx_after':batch.patch.digest(b'old rpx')}
                sp=backup/'state.json';sp.write_bytes(batch.json_bytes(old_state));rpx.write_bytes(b'old rpx');cs.write_bytes(b'old selector state')
                files={'common/mush/Parts.bin':b'new tables','custom/vehicles/New/kart/body/Model.szs':b'new model'}
                old_table=content/'common/mush/Parts.bin';old_table.parent.mkdir(parents=True);old_table.write_bytes(b'old tables')
                state_after=copy.deepcopy(old_state);state_after['icons']={'members':{catalog.icon(c):'hash' for c in catalog.CHOICES}}
                meta={'rpx_before':old_state['rpx_after'],'state_after':state_after,'files':{}}
                for rel,data in files.items():
                    p=prepared/'files'/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
                    before=(content/rel).read_bytes() if (content/rel).exists() else None
                    meta['files'][rel]={'before':batch.patch.digest(before) if before is not None else None,'after':batch.patch.digest(data)}
                (prepared/'batch.json').write_bytes(batch.json_bytes(meta));candidate.write_bytes(b'new rpx')
                manifest={'output_sha256':batch.patch.digest(candidate.read_bytes()),'vehicle_slots':{'bodies':catalog.BODIES,'tires':catalog.TIRES,'icons':list(state_after['icons']['members'])}}
                Path(str(candidate)+'.json').write_bytes(batch.json_bytes(manifest))
                def install(*a):
                    rpx.write_bytes(b'new rpx');cs.write_bytes(b'new selector state')
                    if fail:raise RuntimeError('test write failure')
                with patch.object(batch.patch,'ensure_cemu_closed'),patch.object(batch.patch,'install',side_effect=install):
                    if fail:
                        with self.assertRaisesRegex(RuntimeError,'test write'):batch.install(content,candidate,prepared)
                        self.assertEqual(rpx.read_bytes(),b'old rpx');self.assertEqual(cs.read_bytes(),b'old selector state')
                        self.assertEqual(json.loads(sp.read_text()),old_state);self.assertEqual(old_table.read_bytes(),b'old tables')
                        self.assertFalse((content/'custom/vehicles/New/kart/body/Model.szs').exists())
                    else:
                        batch.install(content,candidate,prepared)
                        self.assertEqual(rpx.read_bytes(),b'new rpx');self.assertEqual(old_table.read_bytes(),b'new tables')
                        self.assertEqual(json.loads(sp.read_text())['rpx_after'],manifest['output_sha256'])

if __name__=='__main__':unittest.main()
