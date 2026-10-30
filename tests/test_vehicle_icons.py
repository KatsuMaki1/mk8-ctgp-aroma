import json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import vehicle_icons as icons
import vehicle_patch as vehicles

class IconInstallTests(unittest.TestCase):
    def test_transaction_and_full_vehicle_rollback(self):
        self.exercise(False)

    def test_failed_rpx_install_restores_every_changed_file(self):
        self.exercise(True)

    def exercise(self,fail):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);content=root/'content';backup=root/'code_backups/VehicleSlots'
            cs=root/'code_backups/MarioCostumeSelector/state.json';menu=content/'ui/cmn/menu.szs'
            rpx=root/'code/Turbo.rpx';candidate=root/'candidate.rpx';prepared=root/'prepared'
            for p in [backup,cs.parent,menu.parent,rpx.parent,prepared]:p.mkdir(parents=True,exist_ok=True)
            rpx.write_bytes(b'old vehicle selector');menu.write_bytes(b'menu with DK icons');cs.write_bytes(b'old selector state')
            candidate.write_bytes(b'new selector');(prepared/'menu.szs').write_bytes(b'menu with DK and vehicle icons')
            digest=icons.patch.digest;members={f'timg/ct_KP_{n}^q.bflim':digest(b'icon') for n in icons.NAMES}
            meta={'input_sha256':digest(menu.read_bytes()),'output_sha256':digest((prepared/'menu.szs').read_bytes()),'members':members}
            (prepared/'manifest.json').write_text(json.dumps(meta))
            Path(str(candidate)+'.json').write_text(json.dumps({'output_sha256':digest(candidate.read_bytes()),'vehicle_slots':{'icons':list(members)}}))
            original_state={'status':'experimental','rpx_after':digest(rpx.read_bytes()),'rpx_before':digest(b'costume baseline'),'target':str(rpx.resolve()),'parameters':{}}
            state=backup/'state.json';state.write_text(json.dumps(original_state));old_state=state.read_bytes()
            (backup/'Turbo.rpx.before-vehicles').write_bytes(b'costume baseline')
            (backup/'selector-state.before.json').write_bytes(b'costume baseline state')
            def install(*a):
                rpx.write_bytes(candidate.read_bytes());cs.write_bytes(b'new selector state')
                if fail:raise RuntimeError('simulated install failure')
            with patch.object(icons.patch,'ensure_cemu_closed'),patch.object(icons.patch,'install',side_effect=install),patch.object(icons,'hashed_member',return_value=b'icon'):
                if fail:
                    with self.assertRaisesRegex(RuntimeError,'simulated'):icons.install(content,candidate,prepared)
                    self.assertEqual(rpx.read_bytes(),b'old vehicle selector');self.assertEqual(cs.read_bytes(),b'old selector state')
                    self.assertEqual(menu.read_bytes(),b'menu with DK icons');self.assertEqual(state.read_bytes(),old_state)
                else:
                    icons.install(content,candidate,prepared)
                    self.assertEqual(json.loads(state.read_text())['rpx_after'],digest(candidate.read_bytes()))
                    self.assertEqual(menu.read_bytes(),b'menu with DK and vehicle icons')
                    candidate.write_bytes(b'updated vehicle selector')
                    Path(str(candidate)+'.json').write_text(json.dumps({'output_sha256':digest(candidate.read_bytes()),
                        'vehicle_slots':{'body':39,'tire':21,'icons':list(members)}}))
                    vehicles.upgrade(candidate,content)
                    self.assertEqual(rpx.read_bytes(),b'updated vehicle selector')
                    self.assertEqual(menu.read_bytes(),b'menu with DK and vehicle icons')
                    self.assertEqual(json.loads(state.read_text())['rpx_after'],digest(candidate.read_bytes()))
                    vehicles.restore(content)
                    self.assertEqual(rpx.read_bytes(),b'costume baseline');self.assertEqual(cs.read_bytes(),b'costume baseline state')
                    self.assertEqual(menu.read_bytes(),b'menu with DK icons')

if __name__=='__main__':unittest.main()
