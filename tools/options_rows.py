"""Private copies of the game's VS setting-row assets for the Options page."""
from pathlib import Path
import struct,subprocess,tempfile
import bflyt,szs,character_menu

def rebuild(raw,parts):
 head=bytearray(raw[:20]);body=b''.join(b for _,b in parts)
 struct.pack_into('>I',head,12,20+len(body));struct.pack_into('>H',head,16,len(parts))
 return bytes(head)+body

def build_menu(menu,common,output,*,pink=False):
 menu,common=Path(menu).read_bytes(),Path(common).read_bytes()
 entries={h:b for _,b,h,_ in szs.sarc_info(szs.yaz0_decode(menu))[0]}
 cmn={h:b for _,b,h,_ in szs.sarc_info(szs.yaz0_decode(common))[0]}
 # Keep all native row pane/animation names. Only our private layout copy
 # receives text sizing changes; ordinary VS menus retain their stock assets.
 raw=cmn[0x01afc831];row=[]
 for t,o,n in bflyt.sections(raw):
  b=bytearray(raw[o:o+n]);name=bflyt.cstr(b[12:36]) if t in ('pan1','pic1','txt1','prt1','bnd1','wnd1') else ''
  if t=='txt1' and name in ('T_Text_00','T_Text_01'):
   # Wide, single-line fields. The native model supplies a bounded value.
   struct.pack_into('>2f',b,112,24. if name=='T_Text_00' else 22.,32.)
   struct.pack_into('>2f',b,76,385. if name=='T_Text_00' else 365.,54.)
   # Title above the selector, value centered in its native value box.
   struct.pack_into('>2f',b,44,0.,(48. if pink else 65.) if name=='T_Text_00' else 0.)
  if t=='pan1' and name=='N_Change_00':
   struct.pack_into('>2f',b,44,0.,0.)
  if t in ('pan1','bnd1') and name in ('N_All_00','B_List_00'):
   # Native row initialization derives the touch-arrow positions from this
   # bound; shrinking the picture alone leaves the right arrow off-screen.
   struct.pack_into('>2f',b,76,440.,90.)
  if t=='prt1' and name=='L_Btn_LR':
   struct.pack_into('>2f',b,76,440.,68.)
  if t=='wnd1' and name=='W_Line_00':b[8]&=~1
  if t=='grp1':
   group=bflyt.cstr(b[8:32])
   # The generic row's type-5 pattern is a stacked competition editor.
   # Keep our private copy in its compact native label/value arrangement.
   if group=='G_Ptn_00':
    b=b[:36];struct.pack_into('>H',b,32,0);struct.pack_into('>I',b,4,len(b))
   if group=='G_InOut_00':
    b=b[:36]+b'N_All_00'.ljust(24,b'\0')
    struct.pack_into('>H',b,32,1);struct.pack_into('>I',b,4,len(b))
  row.append((t,b))
 private_row=rebuild(raw,row)
 single=entries[0x44e1a771]
 parts=[(t,bytearray(single[o:o+n])) for t,o,n in bflyt.sections(single)]
 if any(t=='prt1' and bflyt.cstr(b[12:36]).startswith('P_OptionRow_') for t,b in parts):raise ValueError('Rows already present')
 # Minimal native Parts pane: 96-byte header, no material/pane overrides.
 template=next(b for t,b in parts if t=='prt1')
 additions=[]
 for i,y in enumerate((175.,60.,-55.,-170.) if pink else (145.,0.,-145.)):
  b=bytearray(template[:96]);b[12:36]=f'P_OptionRow_{i:02}'.encode().ljust(24,b'\0')
  b[8]=1;b[9]=4;b[10]=255
  struct.pack_into('>10f',b,44,0.,y,0.,0.,0.,0.,1.,1.,440.,130.)
  struct.pack_into('>I2f',b,84,0,1.,1.)
  b.extend(b'ctgp_OptionRow\0');b.extend(bytes(-len(b)%4));struct.pack_into('>I',b,4,len(b))
  additions.append(('prt1',b))
 # Under the native page's N_All_00 so entry/exit fade applies to the rows.
 closing=max(i for i,(t,_) in enumerate(parts) if t=='pae1')
 parts[closing:closing]=additions
 merged=character_menu.replace_archive(menu,{0x44e1a771:rebuild(single,parts)}, {'blyt/ctgp_OptionRow.bflyt':private_row})
 with tempfile.TemporaryDirectory() as tmp:
  src=Path(tmp)/'menu.sarc';src.write_bytes(merged);dst=Path(tmp)/'menu.szs'
  subprocess.run([r'C:/Program Files/Wiimm/SZS/wszst.exe','compress',str(src),'--yaz0','--dest',str(dst)],check=True,capture_output=True)
  packed=dst.read_bytes();assert szs.yaz0_decode(packed)==merged
  Path(output).write_bytes(packed)
 check={h:b for _,b,h,_ in szs.sarc_info(merged)[0]}
 assert set(check)-set(entries)=={szs.sarc_hash('blyt/ctgp_OptionRow.bflyt')}
 assert all(check[h]==b for h,b in entries.items() if h!=0x44e1a771)
