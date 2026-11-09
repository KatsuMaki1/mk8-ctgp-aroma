"""Append the settings panel to an existing EUR81 CTGP build and menu."""
from pathlib import Path
import struct,json,tempfile,subprocess
import rpxlib,costume_patch as patch,game_options,bflyt,szs,character_menu

def build_rpx(source,output):
 raw,ss=rpxlib.load(source);code=next(s for s in ss if s['addr']==0x2b10000);data=next(s for s in ss if s['addr']==0x10300000)
 if b'MK8_OPTIONS_PANEL_V1' in code['data']:raise ValueError('Already installed')
 hooks={'panel_create':(0x25eeb98,0x9421ffc8),'panel_event':(0x25efc94,0x9421ffc0)}
 expected={0x25eeb98:patch.branch(0x25eeb98,0x2b1b2c8),0x25efc94:patch.branch(0x25efc94,0x2b1b440)}
 for a,w in expected.items():
  if rpxlib.word_at(ss,a)!=w:raise ValueError('Unknown existing options hook')
 if rpxlib.word_at(ss,0x10305000)!=1:raise ValueError('Unknown speedometer state')
 cb=(code['addr']+len(code['data'])+4095)&~4095;db=(data['addr']+len(data['data'])+4095)&~4095
 with tempfile.TemporaryDirectory() as temp:
  text,mutable,symbols=game_options.compile_module(Path(temp),code_address=cb,data_address=db,hooks=hooks,source=Path(__file__).parent/'native/options_panel.c')
 code['data']+=bytes(cb-code['addr']-len(code['data']))+text;data['data']+=bytes(db-data['addr']-len(data['data']))+mutable
 for name,(a,w) in hooks.items():
  s=next(s for s in ss if s['addr']<=a<s['addr']+len(s['data']));b=bytearray(s['data']);struct.pack_into('>I',b,a-s['addr'],patch.branch(a,symbols[name]));s['data']=bytes(b)
 info=next(s for s in ss if s['t']==0x80000004);b=bytearray(info['data'])
 for off,end,base in [(4,cb+len(text),0x2000000),(12,db+len(mutable),0x10000000)]:struct.pack_into('>I',b,off,max(struct.unpack_from('>I',b,off)[0],((end+255)&~255)-base))
 info['data']=bytes(b);result=patch.repack(raw,ss);Path(output).write_bytes(result)
 _,check=rpxlib.load(output)
 for s in ss:
  if s['t']!=0x80000003:assert next(x['data'] for x in check if x['i']==s['i'])==s['data']
 Path(str(output)+'.json').write_text(json.dumps({'source_sha256':patch.digest(raw),'output_sha256':patch.digest(result),'symbols':symbols,'runtime_verified':False},indent=2))

def build_native_menu(source,output):
    packed=Path(source).read_bytes();entries={h:b for n,b,h,a in szs.sarc_info(szs.yaz0_decode(packed))[0]}
    target=szs.sarc_hash('blyt/mn_TopMenu_00.bflyt');layout=entries[target]
    parts=[(t,bytearray(layout[o:o+n])) for t,o,n in bflyt.sections(layout)]
    old=next(b for t,b in parts if t=='prt1' and bflyt.cstr(b[12:36])=='P_Speedometer_00')
    parts=[(t,b) for t,b in parts if not(t=='prt1' and bflyt.cstr(b[12:36])=='P_Speedometer_00')]
    rows=['P_Single_00','P_Multi_00','P_OnlineSingle_00','P_OnlineMulti_00','P_MarioKartTV_00','P_Catalog_00']
    for t,b in parts:
        name=bflyt.cstr(b[12:36]) if t=='prt1' else ''
        if name in rows:struct.pack_into('>f',b,0x30,struct.unpack_from('>f',b,0x30)[0]-20.-5.*rows.index(name))
    def transform(b,name,x,y,w=None,h=None):
        b=bytearray(b);b[12:36]=name.encode().ljust(24,bytes(1));struct.pack_into('>3f',b,44,x,y,0)
        if w is not None:struct.pack_into('>2f',b,76,w,h)
        return b
    wnd=next(b for t,b in parts if t=='wnd1')
    panel=transform(wnd,'P_OptionsPanel_00',0,0,800,400);panel[8]&=~1
    txt=next(b for t,b in parts if t=='txt1')
    def label(name,value,x,y,size):
        b=transform(txt,name,x,y,650,60);b[8]&=~1;b[9]=4;b[10]=255
        # Native txt1 string offset and capacity are relative to this section.
        off=struct.unpack_from('>I',b,100)[0];text=value.encode('utf-16-be')+bytes(2)
        b=b[:off]+text;b.extend(bytes(-len(b)%4));struct.pack_into('>I',b,4,len(b));struct.pack_into('>HH',b,84,len(text),len(text));struct.pack_into('>2f',b,112,size,size)
        b[104:112]=bytes([255])*8
        return ('txt1',b)
    def part(name,x,y,scale):
        b=transform(old,name,x,y);struct.pack_into('>2f',b,68,scale,scale);return ('prt1',b)
    # Reuse the native controller/settings pictogram and the existing material.
    tex='tc_SettingsIcon_Key^s.bflim'
    if szs.sarc_hash('timg/'+tex) not in entries:raise ValueError('Missing native settings icon')
    ti=next(i for i,(t,b) in enumerate(parts) if t=='txl1');texidx=struct.unpack_from('>H',parts[ti][1],8)[0]
    parts[ti]=('txl1',bytearray(character_menu.texture_reference(parts[ti][1],tex)))
    mi=next(i for i,(t,b) in enumerate(parts) if t=='mat1');mat=parts[mi][1];n=struct.unpack_from('>H',mat,8)[0];offs=struct.unpack_from('>'+str(n)+'I',mat,12)
    mats=[bytearray(mat[a:(offs[i+1] if i+1<n else len(mat))]) for i,a in enumerate(offs)]
    m=bytearray(mats[0]);m[:28]=b'CTGP_NativeSettings'.ljust(28,bytes(1));struct.pack_into('>H',m,40,texidx);mats.append(m)
    header=bytearray(mat[:12]);struct.pack_into('>H',header,8,len(mats));pos=12+4*len(mats);ptr=[]
    for m in mats:ptr.append(pos);pos+=len(m)
    mat=header+struct.pack('>'+str(len(ptr))+'I',*ptr)+b''.join(mats);struct.pack_into('>I',mat,4,len(mat));parts[mi]=('mat1',mat)
    pic=transform(next(b for t,b in parts if t=='pic1'),'P_SettingsIcon_00',-263,-285,48,48);pic[9]=4;pic[10]=255;pic[84:100]=bytes([255])*16;struct.pack_into('>H',pic,100,n);struct.pack_into('>8f',pic,104,0,0,1,0,0,1,1,1)
    closing=max(i for i,(t,b) in enumerate(parts) if t=='pae1')
    parts[closing:closing]=[('wnd1',panel),label('T_OptionsTitle_00','Options',0,130,40),label('T_OptionsBack_00','B  Retour',0,-135,28),part('P_OptionSpeed_00',0,20,.8),part('P_Settings_00',-130,-285,.32),('pic1',pic)]
    head=bytearray(layout[:20]);body=b''.join(b for t,b in parts);struct.pack_into('>I',head,12,20+len(body));struct.pack_into('>H',head,16,len(parts))
    result=character_menu.replace_archive(packed,{target:bytes(head)+body},{})
    with tempfile.TemporaryDirectory() as temp:
        p=Path(temp)/'menu.sarc';p.write_bytes(result);dest=Path(temp)/'menu.szs'
        subprocess.run([r'C:/Program Files/Wiimm/SZS/wszst.exe','compress',str(p),'--yaz0','--dest',str(dest)],check=True,capture_output=True)
        compressed=dest.read_bytes();assert szs.yaz0_decode(compressed)==result;Path(output).write_bytes(compressed)
    # No textures or other game resources may change or be added.
    after={h:b for n,b,h,a in szs.sarc_info(result)[0]}
    assert entries.keys()==after.keys()
    assert all(after[h]==b for h,b in entries.items() if h!=target)
    return len(compressed)
