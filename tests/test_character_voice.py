import sys,struct,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import character_voice as voice,character_tables as tables,szs
from test_character_tables import fixture

class VoiceLabelsTest(unittest.TestCase):
    def test_silent_release_keeps_fwav_headers_and_duration(self):
        raw=bytearray(160);raw[:6]=b'FWAV\xfe\xff'
        struct.pack_into('>I',raw,24,64);struct.pack_into('>I',raw,36,128)
        raw[64:68]=b'INFO';struct.pack_into('>I',raw,68,64);raw[72]=1
        raw[128:132]=b'DATA';struct.pack_into('>I',raw,132,32);raw[136:]=bytes(range(24))
        result=voice.silent_fwav(bytes(raw))
        self.assertEqual(result[:136],raw[:136]);self.assertEqual(result[136:],bytes(24))
        self.assertEqual(len(result),len(raw))

    def test_normal_horn_uses_authored_sample_without_touching_other_voices(self):
        labels=['pSE_HORN_MORTON_ON','pSE_HORN_MORTON_OFF','pSE_HORN_MORTON_ON_SP']
        names=['on.bfwav','off.bfwav','special.bfwav'];strings=bytearray();rows=bytearray(3*84)
        for i,(label,name) in enumerate(zip(labels,names)):
            label_offset=len(strings);strings.extend(label.encode()+bytes(1))
            file_offset=len(strings);strings.extend(name.encode()+bytes(1))
            struct.pack_into('>II',rows,i*84,label_offset,file_offset)
            struct.pack_into('>I',rows,i*84+36,100+i);rows[i*84+52:i*84+84]=bytes([i])*32
        header=bytearray(32);header[:8]=b'BARS\xfe\xff\x00\x20';pool=32+len(rows)
        struct.pack_into('>6I',header,8,pool+len(strings),84,32,len(rows),pool,len(strings))
        release=bytearray(160);release[:6]=b'FWAV\xfe\xff';struct.pack_into('>I',release,24,64);struct.pack_into('>I',release,36,128)
        release[64:68]=b'INFO';struct.pack_into('>I',release,68,64);release[72]=1
        release[128:132]=b'DATA';struct.pack_into('>I',release,132,32);release[136:]=bytes(range(24))
        param=bytes(header+rows+strings)
        raw=szs.sarc_write([('_param.bin',param),('on.bfwav',b'donor'),('off.bfwav',bytes(release)),('special.bfwav',b'custom ROB horn'),('voice.bfwav',b'keep me')])
        result,meta=voice.authored_normal_horn(raw);files={n:d for n,d,h in szs.sarc_read(result)}
        self.assertEqual(files['on.bfwav'],b'custom ROB horn');self.assertEqual(files['voice.bfwav'],b'keep me')
        self.assertEqual(files['special.bfwav'],b'custom ROB horn');self.assertEqual(files['off.bfwav'][136:],bytes(24))
        new_param=files['_param.bin'];self.assertEqual(voice.u32(new_param,68),100)
        self.assertEqual(new_param[32+52:32+84],param[32+168+52:32+168+84])

    def test_bars_rebinds_numeric_ids_without_changing_samples(self):
        class Archive:
            def lookup(self,label):return {'pVO_M_ROB_SELECT_CHAR':0x10012f1,'pSE_HORN_MORTON_ON':0x1000007}.get(label)
        label=b'pVO_M_ROB_SELECT_CHAR';strings=label+b'\0sample.bfwav\0'
        param=bytearray(116);param[:8]=b'BARS\xfe\xff\x00\x20'
        struct.pack_into('>6I',param,8,116+len(strings),84,32,84,116,len(strings))
        struct.pack_into('>I',param,36,len(label)+1);struct.pack_into('>I',param,68,0x1283);param.extend(strings)
        sample=b'authored waveform unchanged';raw=szs.sarc_write([('_param.bin',bytes(param)),('sample.bfwav',sample)])
        result,changes=voice.bind_bar_ids(raw,Archive())
        files={n:d for n,d,h in szs.sarc_read(result)}
        self.assertEqual(files['sample.bfwav'],sample)
        self.assertEqual(voice.u32(files['_param.bin'],68),0x12f1)
        self.assertEqual(changes[0]['before'],0x1283)
        expected=bytearray(param);struct.pack_into('>I',expected,68,0x12f1)
        self.assertEqual(files['_param.bin'],expected)
        self.assertEqual(voice.bind_bar_ids(result,Archive())[0],result)
        param[116:116+len(label)]=b'x'*len(label)
        missing=szs.sarc_write([('_param.bin',bytes(param)),('sample.bfwav',sample)])
        with self.assertRaisesRegex(ValueError,'Missing BFSAR'):voice.bind_bar_ids(missing,Archive())

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
