"""Regression checks for loader relocations and the emitted prefix trampolines."""
from pathlib import Path
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import costume_patch as patch


def branch_target(pc, word):
    offset = word & 0x03fffffc
    if offset & 0x02000000:
        offset -= 0x04000000
    return pc + offset


class RelocationTests(unittest.TestCase):
    def test_halfword_write_inside_instruction_is_rejected(self):
        for address in (0x0242e0ac, 0x0242e1dc):
            with self.assertRaisesRegex(ValueError, 'overlaps'):
                patch.check_relocation_overlap([address], {address + 2})

    def test_neighboring_instruction_is_not_rejected(self):
        patch.check_relocation_overlap([0x0242e0b0], {0x0242e0ae, 0x0242e0b4})

    def test_original_crash_destination_is_reproduced(self):
        site = 0x0242e0ac
        emitted = patch.branch(site, 0x02b186a8)
        loaded = (emitted & 0xffff0000) | 0x28e4
        self.assertEqual(branch_target(site, loaded), 0x02b10990)

    def test_replacement_call_sites_target_the_original_prefix_routine(self):
        for site, word in patch.PREFIX_CALLS.items():
            self.assertEqual(word & 1, 1)
            self.assertEqual(branch_target(site, word), 0x0242bcd0)


class NativePrefixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            patch.compiler_tools()
        except ValueError as error:
            raise unittest.SkipTest(str(error))
        with tempfile.TemporaryDirectory(prefix='mk8-prefix-test-') as directory:
            cls.code, cls.data, cls.symbols = patch.compile_native(Path(directory))

    def execute_prefix(self, index, character, variant):
        """Execute the tiny emitted prefix stub's integer/branch subset only."""
        registers = [0] * 32
        registers[4], registers[29] = 0x100b28e4, 0x8000
        memory = {0x8000: character, 0x8004: variant}
        pc = self.symbols['costume_prefix_' + str(index)]
        equal = False
        for _ in range(40):
            if pc == 0x0242bcd0:
                return registers[4]
            word, = struct.unpack_from('>I', self.code, pc - patch.CODE)
            opcode, rt, ra = word >> 26, (word >> 21) & 31, (word >> 16) & 31
            immediate = word & 0xffff
            if immediate & 0x8000:
                immediate -= 0x10000
            next_pc = pc + 4
            if opcode == 32:
                registers[rt] = memory[registers[ra] + immediate]
            elif opcode == 11:
                equal = registers[ra] == immediate
            elif opcode == 16:
                bo, bi = (word >> 21) & 31, (word >> 16) & 31
                self.assertEqual(bi, 2)
                self.assertIn(bo, (4, 12))
                if equal == (bo == 12):
                    displacement = word & 0xfffc
                    if displacement & 0x8000:
                        displacement -= 0x10000
                    next_pc = pc + displacement
            elif opcode in (14, 15):
                base = registers[ra] if ra else 0
                registers[rt] = (base + (immediate << 16 if opcode == 15 else immediate)) & 0xffffffff
            elif opcode == 18:
                self.assertEqual(word & 3, 0, 'Tail call must preserve the original caller LR')
                next_pc = branch_target(pc, word)
            else:
                self.fail('Unexpected prefix instruction %08x' % word)
            pc = next_pc
        self.fail('Prefix stub did not reach its original callee')

    def test_only_mario_variant_one_changes_the_path(self):
        for index in range(2):
            for character, variant in ((0, 0), (0, 2), (1, 1), (4, 1), (16, 1)):
                self.assertEqual(self.execute_prefix(index, character, variant), 0x100b28e4)
            self.assertEqual(self.execute_prefix(index, 0, 1), self.symbols['costume_prefix'])

    def test_dk_costume_paths(self):
        for index in range(2):
            for variant, symbol in ((1, 'costume_prefix_funky'), (2, 'costume_prefix_snorlax')):
                self.assertEqual(self.execute_prefix(index, 9, variant), self.symbols[symbol])
            for variant in (0, 3, 255):
                self.assertEqual(self.execute_prefix(index, 9, variant), 0x100b28e4)

    def test_mutable_state_is_in_the_writable_region(self):
        for name in ('chosen', 'lists', 'initializing_control'):
            self.assertGreaterEqual(self.symbols[name], patch.DATA)
            self.assertLess(self.symbols[name], patch.DATA + len(self.data))


if __name__ == '__main__':
    unittest.main()
