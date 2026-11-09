"""Export the complete EUR81 Cemu payload with explicit relocation audit."""
from pathlib import Path
import struct,json
import rpxlib,retarget
from mkpack import write_hax
C=0x02b10000;D=0x10300000;TC=0x0f800000;TD=0x10400000
GT=retarget.GT_SHIFT;GD=retarget.GD_SHIFT

def build(source,stock,output,noncode=(),nonpointer_words=()):
 raw,ss=rpxlib.load(source);_,os=rpxlib.load(stock)
 code=next(s['data'] for s in ss if s['addr']==C);data=next(s['data'] for s in ss if s['addr']==D)
 text=next(s for s in os if s['name']=='.text');textend=text['addr']+len(text['data'])
 def mapped(v):
  if C<=v<C+len(code):return TC+v-C
  if D<=v<D+len(data):return TD+v-D
  if 0x02000000<=v<textend:return v+GT
  if 0x10000000<=v<0x102aa500:return v+GD
  return v
 changes=[];patches=[];verify=[];seeds=set()
 for old in os:
  if old['name'] not in ('.text','.rodata','.data'):continue
  new=next(s for s in ss if s['addr']==old['addr'])
  assert len(old['data'])==len(new['data'])
  for o in range(0,len(old['data']),4):
   before=old['data'][o:o+4];after=new['data'][o:o+4]
   if before==after:continue
   a=old['addr']+o;w=int.from_bytes(after,'big');v=int.from_bytes(before,'big')
   if old['name']=='.text':
    dest=a+GT
    # ponytail: call sites into Cemu's import stubs (past .text) have console-specific bytes and targets; skip those hooks on Aroma.
    # Upgrade path: plugin reads the live bl target and relocates the hook's call to it.
    if v>>26==18 and a+((v&0x3fffffc)-(0x4000000 if v&0x2000000 else 0))>=textend:
     print('Aroma: skipping import call hook at %x'%a);continue
    if w>>26==18 and not w&2:
     offset=w&0x3fffffc;offset-=0x4000000 if offset&0x2000000 else 0;t=a+offset
     if C<=t<C+len(code):seeds.add(t)
     w=retarget.encode_branch(w,dest,mapped(t))
    # Other modified instructions are bounds/strides/immediates, not addresses.
   else:
    dest=a+GD;w=mapped(w);v=mapped(v)
    if C<=int.from_bytes(after,'big')<C+len(code):seeds.add(int.from_bytes(after,'big'))
   patches.append((dest,struct.pack('>I',w)));verify.append((dest,struct.pack('>I',v)))
 # Function pointers in payload tables and native standard prologues seed CFG.
 for blob in (code,data):
  for o in range(0,len(blob)-3,4):
   v=int.from_bytes(blob[o:o+4],'big')
   if C<=v<C+len(code) and not v&3:seeds.add(v)
 for o in range(0,len(code)-3,4):
  w=int.from_bytes(code[o:o+4],'big')
  if w==0x7c0802a6 or w&0xffff0000==0x94210000:seeds.add(C+o)
  if w>>26==15 and not (w>>16)&31 and (0x0200<=w&65535<=((C+len(code)+0x8000)>>16) or 0x1000<=w&65535<=((D+len(data)+0x8000)>>16)):seeds.add(C+o)
 def ascii_seed(a):
  chunk=code[a-C:a-C+128].split(bytes([0]),1)[0]
  return len(chunk)>=4 and all(32<=v<127 or v in (9,10,13) for v in chunk)
 seeds={a for a in seeds if not ascii_seed(a) and not any(lo<=a<hi for lo,hi in noncode)}
 instructions=set();queue=list(seeds)
 while queue:
  pc=queue.pop()
  while C<=pc<C+len(code)-3 and pc not in instructions and not any(lo<=pc<hi for lo,hi in noncode):
   instructions.add(pc);w=int.from_bytes(code[pc-C:pc-C+4],'big');op=w>>26
   if op==18:
    off=w&0x3fffffc;off-=0x4000000 if off&0x2000000 else 0;t=off if w&2 else pc+off
    if C<=t<C+len(code):queue.append(t)
    if not w&1:break
   elif op==16:
    off=w&0xfffc;off-=0x10000 if off&0x8000 else 0;t=pc+off
    if C<=t<C+len(code):queue.append(t)
   elif op==19 and ((w>>1)&1023) in (16,528):
    if not w&1 and ((w>>21)&31)==20:break
   pc+=4
 oldcb=retarget.CB;retarget.CB=C
 try:
  blob=retarget.Blob(code,data);words=list(blob.W);audit=[];writes={}
  for pc in sorted(instructions):
   i=(pc-C)//4;w=blob.W[i]
   if w>>26!=15 or (w>>16)&31:continue
   hi=w&65535
   if not (0x0200<=hi<=((C+len(code)+0x8000)>>16) or 0x1000<=hi<=((D+len(data)+0x8000)>>16)):continue
   consumers=blob.consumers(i);newhi=set();pairs=[]
   for j,kind in consumers:
    lo=blob.W[j]&65535;v=(hi<<16)|lo if kind=='ori' else (hi<<16)+retarget.sx16(lo)
    n=mapped(v)
    if n==v:continue
    h=(n>>16)&65535 if kind=='ori' else ((n+0x8000)>>16)&65535
    newhi.add(h);pairs.append((j,n&65535,v,n))
   if not pairs:continue
   if len(newhi)!=1 or len(pairs)!=len(consumers):raise ValueError('Ambiguous lis at %08x'%pc)
   writes[i]=(w&0xffff0000)|next(iter(newhi))
   for j,lo,v,n in pairs:
    nw=(blob.W[j]&0xffff0000)|lo
    if j in writes and writes[j]!=nw:raise ValueError('Conflicting relocation')
    writes[j]=nw;audit.append({'kind':'lis','at':hex(C+j*4),'old':hex(v),'new':hex(n)})
  for pc in sorted(instructions):
   i=(pc-C)//4;w=blob.W[i]
   if w>>26==18:
    if w&2:raise ValueError('Absolute branch at %08x word %08x'%(pc,w))
    off=w&0x3fffffc;off-=0x4000000 if off&0x2000000 else 0;t=pc+off;nt=mapped(t)
    if nt==t:raise ValueError('Unknown branch target %08x from %08x'%(t,pc))
    writes[i]=retarget.encode_branch(w,TC+pc-C,nt)
  for i,w in writes.items():words[i]=w
  # Aligned pointer tables embedded after functions also need relocation.
  for i,w in enumerate(blob.W):
   if C+i*4 in instructions or C+i*4 in nonpointer_words:continue
   n=mapped(w)
   if n!=w:words[i]=n;audit.append({'kind':'code_table','at':hex(C+i*4),'old':hex(w),'new':hex(n)})
  converted=b''.join(struct.pack('>I',w) for w in words)+struct.pack('>I',0x4e800020)
 finally:retarget.CB=oldcb
 mutable=bytearray(data)
 for o in range(32,len(data)-3,4):
  w=int.from_bytes(data[o:o+4],'big');n=mapped(w)
  if n!=w:struct.pack_into('>I',mutable,o,n);audit.append({'kind':'data','at':hex(D+o),'old':hex(w),'new':hex(n)})
 from aroma_features import private_cup0_path
 mutable=private_cup0_path(bytes(mutable[32:]))
 files={'Addr.bin':struct.pack('>II',TC,TD+32),'Code.bin':converted,'Data.bin':mutable,'Patches.hax':write_hax(patches),'Verify.hax':write_hax(verify)}
 out=Path(output);out.mkdir(parents=True,exist_ok=True)
 import hashlib
 for n,b in files.items():(out/n).write_bytes(b)
 manifest={'region':'EUR','game_version':81,'console_tested':False,'features':['Complete current CTGP payload','Independent ROB R19','Booster48 R3','TT150/200 P4','Toad Harbor original ramp'],'source_rpx_sha256':hashlib.sha256(raw).hexdigest(),'patch_count':len(patches),'cfg_instructions':len(instructions),'relocations':audit,'files':{n:hashlib.sha256(b).hexdigest() for n,b in files.items()},'tt_records_separated':False}
 (out/'Features.json').write_text(json.dumps(manifest,indent=2)+'\n');return manifest

