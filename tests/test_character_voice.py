import sys,struct,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import character_voice as voice,character_tables as tables
from test_character_tables import fixture

class VoiceLabelsTest(unittest.TestCase):
    def test_reaction_groups_preserve_original_weights_and_append_rob(self):
        label=b'VOICE_JUMP_ACTION_MOR\0';sound=b'pVO_MOR_JUMP\0'
        start=16;payload=struct.pack('>III',1,start+12,start+12+len(label))+label+struct.pack('>I',123)+sound
        raw=b'BSIS\0\0\0\1'+struct.pack('>II',1,start)+payload
        result,count=voice.reaction_groups(raw)
        self.assertEqual(count,1);self.assertEqual(voice.u32(result,8),2)
        first,second=struct.unpack_from('>II',result,12)
        self.assertEqual(result[first+12:second],payload[12:])
        group=voice.u32(result,second+4);child=voice.u32(result,second+8)
        self.assertEqual(result[group:group+len(label)],label.replace(b'_MOR',b'_ROB'))
        self.assertEqual(voice.u32(result,child),123)
        self.assertEqual(result[child+4:],sound.replace(b'_MOR',b'_ROB'))
        with self.assertRaises(ValueError):voice.reaction_groups(result)

    def test_private_prefix_preserves_existing_entries_and_other_sections(self):
        old=fixture(b'AUDO',tables.AUDIO_AXES).replace(b'Mtn\0',b'MOR\0')
        expanded=tables.expand(old)
        new=voice.audio_label(expanded)
        a=dict(tables.read_sections(expanded)[1]);b=dict(tables.read_sections(new)[1])
        self.assertEqual(a[b'TEST'],b[b'TEST'])
        self.assertEqual(a[b'DRSE'][:160],b[b'DRSE'][:160])
        pool=voice.u32(b[b'DRSE'],8)
        for index,expected in ((28,b'MOR'),(37,b'ROB')):
            at=pool+voice.u32(b[b'DRSE'],12+index*4)
            self.assertEqual(b[b'DRSE'][at:at+4],expected+b'\0')
        self.assertEqual(voice.audio_label(new),new)
    def test_rejects_unexpanded_audio(self):
        with self.assertRaises(ValueError):voice.audio_label(fixture(b'AUDO',tables.AUDIO_AXES))

if __name__=='__main__':unittest.main()
