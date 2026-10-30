import struct,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import aroma_features as aroma
import costume_patch as native
import vehicle_patch as vehicles

class AromaFeaturesTests(unittest.TestCase):
    def test_private_cup_path_preserves_blob_layout_and_rejects_unknown_slot(self):
        original=bytes(0x17dc)+b'data.cup0'+bytes(3)+b'tail'
        result=aroma.private_cup0_path(original)
        self.assertEqual(len(result),len(original))
        self.assertEqual(result[:0x17dc],original[:0x17dc])
        self.assertEqual(result[0x17dc:0x17e8],b'custom/cup0'+bytes(1))
        self.assertEqual(result[0x17e8:],original[0x17e8:])
        self.assertEqual(aroma.private_cup0_path(result),result)
        with self.assertRaises(ValueError):aroma.private_cup0_path(bytes(0x1800))

    def test_only_game_addresses_are_shifted(self):
        self.assertEqual(aroma.console_address(0x0253d47c),0x0e6bd47c)
        self.assertEqual(aroma.console_address(0x100d25d0),0x105d47d0)
        self.assertEqual(aroma.console_address(0x1018a18c),0x1068c38c)
        for value in [0,39,21,0x54,0x7000,0x10400020,0x0f808000]:
            self.assertEqual(aroma.console_address(value),value)

    def test_console_compilation_maps_native_services_and_trampoline_returns(self):
        saved=(native.HOOKS,native.PREFIX_SITES,native.EXTRA_CFLAGS,native.EXTRA_ASSEMBLY,native.CODE,native.DATA)
        hooks={**native.HOOKS,**vehicles.VEHICLE_HOOKS}
        try:
            native.HOOKS={n:(aroma.console_address(a),w) for n,(a,w) in hooks.items()}
            native.PREFIX_SITES=tuple(aroma.console_address(a) for a in native.PREFIX_SITES)
            native.EXTRA_CFLAGS=['-DVEHICLE_SLOTS'];native.EXTRA_ASSEMBLY=vehicles.GATEWAY
            native.CODE,native.DATA=0x0f808000,0x10403020
            with tempfile.TemporaryDirectory() as tmp:
                code,data,symbols=native.compile_native(Path(tmp),address_map=aroma.console_address)
                c=(Path(tmp)/'costume_selector.c').read_text();v=(Path(tmp)/'vehicle_slots.c').read_text()
                self.assertIn('0xe6bd47c',c);self.assertIn('0x105d47d0',v)
                self.assertNotIn('0x0253d47c',c);self.assertNotIn('0x100d25d0',v)
                for name,(address,original) in hooks.items():
                    pc=symbols['original_'+name];first,branch=struct.unpack_from('>II',code,pc-native.CODE)
                    self.assertEqual(first,original)
                    delta=branch&0x03fffffc;delta=delta-0x04000000 if delta&0x02000000 else delta
                    self.assertEqual(pc+4+delta,aroma.console_address(address)+4)
                self.assertTrue(data);self.assertLess(len(data),4096)
        finally:
            native.HOOKS,native.PREFIX_SITES,native.EXTRA_CFLAGS,native.EXTRA_ASSEMBLY,native.CODE,native.DATA=saved

if __name__=='__main__':unittest.main()
