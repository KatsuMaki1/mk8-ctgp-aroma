"""Reproduce the native caller keeping r8/CTR live across a leaf config call."""
from pathlib import Path
import struct,sys,tempfile,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import costume_patch as p
import vehicle_patch as v

class GatewayTests(unittest.TestCase):
    def test_race_readers_preserve_leaf_and_inline_state(self):
        old=(p.HOOKS,p.EXTRA_CFLAGS,p.EXTRA_ASSEMBLY)
        try:
            p.HOOKS={**p.HOOKS,**v.VEHICLE_HOOKS};p.EXTRA_CFLAGS=['-DVEHICLE_SLOTS'];p.EXTRA_ASSEMBLY=v.GATEWAY
            with tempfile.TemporaryDirectory() as d:code,data,syms=p.compile_native(Path(d))
        finally:p.HOOKS,p.EXTRA_CFLAGS,p.EXTRA_ASSEMBLY=old
        for entry in ['costume_vehicle_audio_body','costume_vehicle_race_body','costume_vehicle_unit_body','costume_vehicle_unit_tire']:
            for body in [0,7,38,39,40,41]:
                with self.subTest(entry=entry,body=body):
                    regs=[0x12340000+i for i in range(32)];regs[1]=0x1e201040
                    regs[3]=0x20000;regs[26]=body+1;regs[6]=body;regs[10]=21 if body==39 else 22 if body==40 else 12;before=regs[:]
                    cr=0xaabbccdd;mem={0x20020:0x30000,0x30054:body};pc=syms[entry]
                    end={'costume_vehicle_audio_body':0x02069028,'costume_vehicle_race_body':0x12345678,'costume_vehicle_unit_body':0x021bc358,'costume_vehicle_unit_tire':0x021bc394}[entry]
                    for _ in range(40):
                        if pc==end:break
                        word=struct.unpack_from('>I',code,pc-p.CODE)[0];nxt=pc+4
                        op=word>>26;rt=(word>>21)&31;ra=(word>>16)&31;imm=word&65535;imm=imm-65536 if imm&32768 else imm
                        if op in (36,37):
                            addr=regs[ra]+imm;mem[addr]=regs[rt]
                            if op==37:regs[ra]=addr
                        elif op==32:regs[rt]=mem[regs[ra]+imm]
                        elif op==14:regs[rt]=(regs[ra] if ra else 0)+imm
                        elif op==15:regs[rt]=((regs[ra] if ra else 0)+(imm<<16))&0xffffffff
                        elif word==0x7c000026:regs[0]=cr
                        elif word==0x7c0ff120:cr=regs[0]
                        elif word==0x4e800020:nxt=end
                        elif op in (10,11):cr=(cr&0x0fffffff)|((2 if regs[ra]==imm else 8 if regs[ra]<imm else 4)<<28)
                        elif op==16:
                            bo,bi=(word>>21)&31,(word>>16)&31
                            self.assertIn(bo,(4,12));cond=bool(cr&(1<<(31-bi)))
                            if cond==(bo==12):
                                delta=word&0xfffc;delta=delta-65536 if delta&32768 else delta;nxt=pc+delta
                        elif op==18:
                            delta=word&0x03fffffc;delta=delta-0x04000000 if delta&0x02000000 else delta;nxt=pc+delta
                            self.assertEqual(word&1,0)
                        else:self.fail('Unexpected reader instruction %08x'%word)
                        pc=nxt
                    self.assertEqual(pc,end)
                    if 'audio' in entry:
                        before[26]={39:7,40:30,41:7}.get(body,body)+1
                        self.assertEqual(cr,0x8abbccdd)
                        self.assertEqual(mem[syms['vehicle_audio_seen']],body+1)
                    elif 'unit_body' in entry:
                        self.assertEqual(mem[regs[30]+0x54],{39:7,40:30,41:7}.get(body,body))
                        self.assertEqual(cr,0xaabbccdd)
                    elif 'unit_tire' in entry:
                        self.assertEqual(mem[regs[3]],11 if body==40 else 12)
                        self.assertEqual(cr,0xaabbccdd)
                    else:
                        before[3]={39:7,40:30,41:7}.get(body,body);before[12]=0x30000
                        self.assertEqual(cr,0xaabbccdd)
                    self.assertEqual(regs,before)

    def test_native_leaf_live_registers_and_special_state_survive(self):
        old=(p.HOOKS,p.EXTRA_CFLAGS,p.EXTRA_ASSEMBLY)
        try:
            p.HOOKS={**p.HOOKS,**v.VEHICLE_HOOKS};p.EXTRA_CFLAGS=['-DVEHICLE_SLOTS'];p.EXTRA_ASSEMBLY=v.GATEWAY
            with tempfile.TemporaryDirectory() as d:code,data,syms=p.compile_native(Path(d))
        finally:p.HOOKS,p.EXTRA_CFLAGS,p.EXTRA_ASSEMBLY=old
        regs=[0]*32;regs[1]=0x1e6fd2f8;regs[3]=0x1e6fd300
        for i in range(4,9):regs[i]=0x10180000+i
        regs[8]=0x10180000;before=regs[:];lr=0x02431ff4;ctr=0x44444444;cr=0xaabbccdd;xer=0x12345678
        pc=syms['costume_vehicle_config'];mem={};callee_seen=False
        for _ in range(80):
            if pc==0x02431ff4:break
            word=struct.unpack_from('>I',code,pc-p.CODE)[0];next_pc=pc+4
            op=word>>26;rt=(word>>21)&31;ra=(word>>16)&31;imm=word&65535;imm=imm-65536 if imm&32768 else imm
            if op in (36,37):
                address=regs[ra]+imm;mem[address]=regs[rt]
                if op==37:regs[ra]=address
            elif op==32:regs[rt]=mem[regs[ra]+imm]
            elif op==14:regs[rt]=(regs[ra] if ra else 0)+imm
            elif word==0x7c0802a6:regs[0]=lr
            elif word==0x7c0902a6:regs[0]=ctr
            elif word==0x7c0102a6:regs[0]=xer
            elif word==0x7c000026:regs[0]=cr
            elif word==0x7c0803a6:lr=regs[0]
            elif word==0x7c0903a6:ctr=regs[0]
            elif word==0x7c0103a6:xer=regs[0]
            elif word==0x7c0ff120:cr=regs[0]
            elif word==0x4e800020:next_pc=lr
            elif op==18:
                delta=word&0x03fffffc;delta=delta-0x04000000 if delta&0x02000000 else delta
                self.assertEqual(pc+delta,syms['vehicle_config_impl']);self.assertEqual(word&1,1)
                # C ABI legitimately clobbers these. The native leaf did not.
                for i in range(4,13):regs[i]=0xdead0000+i
                ctr,cr,xer=1,2,3;lr=next_pc;callee_seen=True
            else:self.fail('Unexpected instruction %08x'%word)
            pc=next_pc
        self.assertEqual(pc,0x02431ff4);self.assertTrue(callee_seen)
        self.assertEqual(regs[1],before[1]);self.assertEqual(regs[3:9],before[3:9])
        self.assertEqual((lr,ctr,cr,xer),(0x02431ff4,0x44444444,0xaabbccdd,0x12345678))

if __name__=='__main__':unittest.main()
