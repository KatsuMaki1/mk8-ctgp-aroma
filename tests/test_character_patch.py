import struct,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import character_patch as c,costume_patch as p

class Gateways(unittest.TestCase):
    def test_voice_prefix_accepts_only_the_one_appended_driver(self):
        section={'t':1,'fl':2,'addr':c.VOICE_PREFIX_BOUND,'data':struct.pack('>I',0x28040025)}
        result=c.voice_prefix_patch([section])
        bound=result[c.VOICE_PREFIX_BOUND]&65535
        for driver in range(256):
            self.assertEqual(driver<bound,driver<37 or driver==37)
        section['data']=struct.pack('>I',0x28040024)
        with self.assertRaises(ValueError):c.voice_prefix_patch([section])

    @classmethod
    def setUpClass(cls):
        base=min(0x0242bcd0,*c.HOOKS.values());raw=bytearray(0x025d7000-base)
        for name,a in c.HOOKS.items():struct.pack_into('>I',raw,a-base,c.WORDS[name])
        struct.pack_into('>I',raw,0x0242bcd0-base,p.branch(0x0242bcd0,0x02b18000))
        struct.pack_into('>I',raw,0x02557754-base,p.branch(0x02557754,0x02b18100))
        code=struct.pack('>II',0x9421fea8,p.branch(0x02b10004,0x0242bde0))
        sections=[{'t':1,'fl':2,'addr':base,'data':bytes(raw)},
                  {'t':1,'fl':2,'addr':0x02b10000,'data':code}]
        cls.base=0x02b22000
        with tempfile.TemporaryDirectory() as d:
            cls.code,cls.data,cls.symbols=c.compile_module(Path(d),sections,cls.base,0x1030a000)

    def test_all_inline_callbacks_preserve_native_live_state(self):
        for a,(dst,src) in c.ARRAYS.items():
            with self.subTest(address=hex(a)):
                r=[0x100000+i for i in range(32)];r[1]=0x20000000;before=r[:]
                lr,ctr,cr,xer=0xabcdef00,0x55667788,0xaa55aa55,0x11223344
                memory={};pc=self.symbols['character_array_%08x'%a];called=False
                for _ in range(100):
                    if pc==a+4:break
                    w=struct.unpack_from('>I',self.code,pc-self.base)[0];nxt=pc+4
                    op=w>>26;rt=(w>>21)&31;ra=(w>>16)&31;imm=w&65535;imm=imm-65536 if imm&32768 else imm
                    if op in (36,37):
                        addr=r[ra]+imm;memory[addr]=r[rt]
                        if op==37:r[ra]=addr
                    elif op==32:r[rt]=memory[r[ra]+imm]
                    elif op==14:r[rt]=(r[ra] if ra else 0)+imm
                    elif w==0x7c0802a6:r[0]=lr
                    elif w==0x7c0902a6:r[0]=ctr
                    elif w==0x7c0102a6:r[0]=xer
                    elif w==0x7c000026:r[0]=cr
                    elif w==0x7c0803a6:lr=r[0]
                    elif w==0x7c0903a6:ctr=r[0]
                    elif w==0x7c0103a6:xer=r[0]
                    elif w==0x7c0ff120:cr=r[0]
                    elif op==31 and (w>>1)&1023==444:
                        rs=(w>>21)&31;rb=(w>>11)&31;r[ra]=r[rs]|r[rb]
                    elif op==18:
                        target=c.branch_target(pc,w&~1)
                        if w&1:
                            self.assertEqual(target,self.symbols['character_button_array'])
                            self.assertEqual(r[3],before[src]);called=True
                            for k in [0,*range(3,13)]:r[k]=0xdead0000+k
                            r[3]=0x1030b000;lr=nxt;ctr=cr=xer=0
                        else:nxt=target
                    else:self.fail('Unsupported gateway instruction %08x'%w)
                    pc=nxt
                self.assertTrue(called);self.assertEqual(pc,a+4)
                expected=before[:];expected[dst]=0x1030b000
                self.assertEqual(r,expected)
                self.assertEqual((lr,ctr,cr,xer),(0xabcdef00,0x55667788,0xaa55aa55,0x11223344))

    def test_trampolines_return_to_original_next_instruction(self):
        for name,a in c.HOOKS.items():
            start=self.symbols['original_'+name]-self.base
            word,branch=struct.unpack_from('>II',self.code,start)
            self.assertEqual(word,c.WORDS[name])
            self.assertEqual(c.branch_target(self.base+start+4,branch),a+4)
        start=self.symbols['previous_char_recipe']-self.base
        word,branch=struct.unpack_from('>II',self.code,start)
        self.assertEqual(word,0x9421fea8)
        self.assertEqual(c.branch_target(self.base+start+4,branch),0x02b10004)

    def test_rejects_the_crashing_hook_after_link_register_save(self):
        sections=[{'t':1,'fl':2,'addr':0x0242fc70,
                   'data':struct.pack('>II',0x7c0802a6,0x9421fff0)}]
        c.check_entry(sections,0x0242fc70,0x7c0802a6)
        with self.assertRaisesRegex(ValueError,'after mflr'):
            c.check_entry(sections,0x0242fc74,0x9421fff0)

    def test_only_new_driver_changes_audio_class_name_index(self):
        for value in (0,1,28,29,37,38,39,255):
            regs=[0x1000+i for i in range(32)];regs[27]=value;before=regs[:]
            pc=self.symbols['character_audio_class'];equal=False
            for _ in range(12):
                if pc==c.AUDIO_CLASS+4:break
                word=struct.unpack_from('>I',self.code,pc-self.base)[0];op=word>>26;nxt=pc+4
                if op in (10,11):equal=regs[(word>>16)&31]==(word&65535)
                elif op==16:
                    bo=(word>>21)&31;delta=word&0xfffc;delta=delta-65536 if delta&32768 else delta
                    if equal==(bo==12):nxt=pc+delta
                elif op==14:regs[(word>>21)&31]=word&65535
                elif op==18:nxt=c.branch_target(pc,word)
                else:self.fail('Unexpected audio alias instruction')
                pc=nxt
            self.assertEqual(pc,c.AUDIO_CLASS+4)
            before[27]=29 if value==38 else value;self.assertEqual(regs,before)

if __name__=='__main__':unittest.main()
