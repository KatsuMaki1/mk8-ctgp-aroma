from pathlib import Path
import struct,json,tempfile,subprocess
import rpxlib,costume_patch as patch,game_options,bflyt,szs,character_menu,options_panel
def build_rpx(source,output,*,pink=False,red_background=False,tt_capture=False,tt_ghosts=False,local_tt_adapter=False):
 raw,ss=rpxlib.load(source);code=next(s for s in ss if s['addr']==0x2b10000);data=next(s for s in ss if s['addr']==0x10300000)
 if b'MK8_OPTIONS_NATIVE_SUBMENU_V1' in code['data']:raise ValueError('Already installed')
 hooks={'sub_top_create':(0x25eeb98,0x9421ffc8),'sub_top_event':(0x25efc94,0x9421ffc0),'sub_enter':(0x25e7e9c,0x7c0802a6),'sub_calc':(0x25e73f0,0x7c0802a6),'country_get':(0x24cb344,0x81630034),'country_local_get':(0x24cc5bc,0x7c0802a6),'flag_texture':(0x255dee4,0x7c0802a6),'set_visible_trace':(0x2531bdc,0x2c040000),'anim_frame_trace':(0x2530ee0,0x7c0802a6),'globe_plate':(0x25145fc,0x7c0802a6),'language_code':(0x2566024,0x7c0802a6),'language_message':(0x253d690,0x7c0802a6)}
 expected={0x25eeb98:patch.branch(0x25eeb98,0x2b1b2c8),0x25efc94:patch.branch(0x25efc94,0x2b1b440)}
 hooks['sub_create']=(0x25e79d8,0x9421ffc8)
 hooks.update({'language_set_default':(0x25367ac,0x7c0802a6),'language_set_named':(0x25367e8,0x7c0802a6),
               'language_set_pane':(0x2536848,0x7c0802a6),'language_page_calc':(0x253e744,0x7c0802a6)})
 if pink:hooks.update({'drift':(0x21c9ba8,0x9421ffc8),'dash':(0x21c59d4,0x9421ffd0)})
 expected.update({a:w for a,w in hooks.values() if a not in expected})
 extra_flags=[]
 call_patches={}
 for a,name,target in ((0x24bd998,'act_simple_address_id_ex',0x2b08b88),(0x24bd9c4,'act_simple_address_id_ex',0x2b08b88),(0x29f853c,'act_simple_address_id',0x2b08b90)):
  call_patches[a]=name;expected[a]=patch.branch(a,target)|1
 if tt_capture:
  if not pink:raise ValueError('TT capture needs the shared physics option state')
  hooks['tt_course_event']=(0x25bc400,0x9421ffa8)
  expected[0x25bc400]=0x9421ffa8
  generated=Path(__file__).resolve().parents[1]/'work/tt_categories'
  if not (generated/'catalog_next.h').exists():raise ValueError('Generate the TT server/client catalog first')
  extra_flags+=['-DENABLE_TT_CAPTURE',f'-I{generated}',f'-I{Path(__file__).resolve().parent / "native"}']
 if tt_ghosts:
  if not tt_capture:raise ValueError('Ghost scope requires accepted course-click capture')
  scope_hooks={'tt_save_record':(0x24f41c8,0x9421feb8),'tt_upload_sequence':(0x25c8ca0,0x9421ff70),'tt_online_exit':(0x25cf00c,0x7c0802a6),'tt_online_enter':(0x25cbe30,0x9421ff80),'tt_title_update':(0x2596e3c,0x9421ffb8),'tt_online_calc':(0x25cde3c,0x7c0802a6),'tt_online_event':(0x25cde78,0x9421ffd8),'tt_list_build':(0x25c6584,0x3d80ffff),'tt_footer':(0x2585b00,0x9421ff88),'tt_ghost_event':(0x25c81e8,0x9421ffe0),'tt_ghost_enter':(0x25c79e8,0x9421ff70),'tt_personal_get':(0x24f2714,0x7c0802a6),'tt_mgr_start':(0x24f22ac,0x7c0802a6),
   'tt_name_generate':(0x24f400c,0x9421ff78),'tt_directory':(0x24cdc98,0x9421ffd8),
   'tt_personal_reload':(0x24f0a04,0x7c0802a6),'tt_remove':(0x24f2944,0x7c0802a6)}
  hooks.update(scope_hooks);expected.update({a:w for a,w in scope_hooks.values()})
  expected[0x25c9d1c]=patch.branch(0x25c9d1c,0x2740e1c)|1
  call_patches[0x25c9d1c]='tt_staff_format'
  extra_flags+=['-DENABLE_TT_GHOST_SCOPE']
  if local_tt_adapter:extra_flags+=['-DENABLE_TT_LOCAL_ADAPTER']
 if red_background:
  # These globals and the existing class hook belong to the guarded P4 TT module.
  if rpxlib.word_at(ss,0x1030c000)!=2 or rpxlib.word_at(ss,0x1030c010)!=0 or rpxlib.word_at(ss,0x25ea5b0)!=patch.branch(0x25ea5b0,0x2b32260):
   raise ValueError('Unknown TT module: refusing background hook')
  hooks.update({'tt_background_calc':(0x25e4f2c,0x7c0802a6),'tt_background_class_calc':(0x25ea5b0,0x7c0802a6)})
  expected[0x25e4f2c]=0x7c0802a6
  expected[0x25ea5b0]=patch.branch(0x25ea5b0,0x2b32260)
  extra_flags+=['-DENABLE_TT_RED_BACKGROUND','-Wl,--defsym,previous_tt_background_class_calc=0x2b32260']
 mode=0x25e8114;word=rpxlib.word_at(ss,mode);delta=word&0x3fffffc;delta=delta-0x4000000 if delta&0x2000000 else delta;previous=mode+delta
 if word>>26!=18:raise ValueError('Expected existing TT mode hook')
 for a,w in expected.items():
  if rpxlib.word_at(ss,a)!=w:raise ValueError('Unknown existing options hook')
 if rpxlib.word_at(ss,0x10305000)!=1:raise ValueError('Unknown speedometer state')
 cb=(code['addr']+len(code['data'])+4095)&~4095;db=(data['addr']+len(data['data'])+4095)&~4095
 with tempfile.TemporaryDirectory() as temp:
  catalog=Path(__file__).resolve().parents[1]/'work/options_i18n'
  if not (catalog/'options_catalog.h').exists():raise ValueError('Build the Options localization catalog first')
  text,mutable,symbols=game_options.compile_module(Path(temp),code_address=cb,data_address=db,hooks=hooks,source=Path(__file__).parent/'native/options_submenu.c',cflags=(*(['-DENABLE_PINK_DRIFT','-DENABLE_OPTIONS_STORE'] if pink else []),*extra_flags,f'-I{catalog}',f'-Wl,--defsym,previous_mode_event=0x{previous:x}',),data_limit=0x50000)
 code['data']+=bytes(cb-code['addr']-len(code['data']))+text;data['data']+=bytes(db-data['addr']-len(data['data']))+mutable
 hooks['sub_mode_event']=(mode,word)
 for name,(a,w) in hooks.items():
  s=next(s for s in ss if s['addr']<=a<s['addr']+len(s['data']));b=bytearray(s['data']);struct.pack_into('>I',b,a-s['addr'],patch.branch(a,symbols['pink_'+name if name in ('drift','dash','sparks','particle_color','uniform_color') else name]));s['data']=bytes(b)
 for a,name in call_patches.items():
  s=next(s for s in ss if s['addr']<=a<s['addr']+len(s['data']));b=bytearray(s['data']);struct.pack_into('>I',b,a-s['addr'],patch.branch(a,symbols[name])|1);s['data']=bytes(b)
 info=next(s for s in ss if s['t']==0x80000004);b=bytearray(info['data'])
 for off,end,base in [(4,cb+len(text),0x2000000),(12,db+len(mutable),0x10000000)]:struct.pack_into('>I',b,off,max(struct.unpack_from('>I',b,off)[0],((end+255)&~255)-base))
 info['data']=bytes(b);result=patch.repack(raw,ss);Path(output).write_bytes(result)
 _,check=rpxlib.load(output)
 for s in ss:
  if s['t']!=0x80000003:assert next(x['data'] for x in check if x['i']==s['i'])==s['data']
 Path(str(output)+'.json').write_text(json.dumps({'source_sha256':patch.digest(raw),'output_sha256':patch.digest(result),'symbols':symbols,'runtime_verified':False},indent=2))


def build_menu(source,output):
    packed=Path(source).read_bytes()
    entries={h:b for n,b,h,a in szs.sarc_info(szs.yaz0_decode(packed))[0]}
    top=szs.sarc_hash('blyt/mn_TopMenu_00.bflyt');old=entries[top]
    parts=[(t,bytearray(old[o:o+n])) for t,o,n in bflyt.sections(old) if not(t=='prt1' and bflyt.cstr(old[o+12:o+36])=='P_Speedometer_00')]
    rows=['P_Single_00','P_Multi_00','P_OnlineSingle_00','P_OnlineMulti_00','P_MarioKartTV_00','P_Catalog_00']
    for t,b in parts:
        name=bflyt.cstr(b[12:36]) if t=='prt1' else ''
        if name in rows:struct.pack_into('>f',b,0x30,struct.unpack_from('>f',b,0x30)[0]-20.-5.*rows.index(name))
        if name=='L_TopMenuContents_00':
            struct.pack_into('>f',b,44,-26.);struct.pack_into('>2f',b,68,1.10,1.10)
        if name=='L_TopMenuContents_02':
            struct.pack_into('>2f',b,44,230.,10.);struct.pack_into('>2f',b,68,.75,.75)
    # X is U+E002 from the existing message font, not a newly drawn button.
    txt=next(b for t,b in parts if t=='txt1')
    def footer_text(name,text,x,y,size,width):
        b=bytearray(txt);b[12:36]=name.encode().ljust(24,bytes(1));b[9]=4;b[10]=255
        struct.pack_into('>3f',b,44,x,y,0);struct.pack_into('>2f',b,76,width,48)
        off=struct.unpack_from('>I',b,100)[0];v=text.encode('utf-16-be')+bytes(2);b=b[:off]+v;b.extend(bytes(-len(b)%4));struct.pack_into('>I',b,4,len(b));struct.pack_into('>HH',b,84,len(v),len(v));struct.pack_into('>2f',b,112,size,size)
        return ('txt1',b)
    ti=next(i for i,(t,b) in enumerate(parts) if t=='txl1');texindex=struct.unpack_from('>H',parts[ti][1],8)[0]
    parts[ti]=('txl1',bytearray(character_menu.texture_reference(parts[ti][1],'tc_CTGP_SettingsGray^l.bflim')))
    parts[ti]=('txl1',bytearray(character_menu.texture_reference(parts[ti][1],'tc_PlusBtnIcon_00^f.bflim')))
    mi=next(i for i,(t,b) in enumerate(parts) if t=='mat1');mat=parts[mi][1];n=struct.unpack_from('>H',mat,8)[0];offs=struct.unpack_from('>'+str(n)+'I',mat,12)
    mats=[bytearray(mat[a:(offs[i+1] if i+1<n else len(mat))]) for i,a in enumerate(offs)]
    m=bytearray(mats[0]);m[:28]=b'CTGP_SettingsGray'.ljust(28,bytes(1));struct.pack_into('>H',m,40,texindex);mats.append(m)
    m=bytearray(mats[0]);m[:28]=b'CTGP_NativeX'.ljust(28,bytes(1));struct.pack_into('>H',m,40,texindex+1);mats.append(m)
    header=bytearray(mat[:12]);struct.pack_into('>H',header,8,len(mats));pos=12+4*len(mats);ptr=[]
    for m in mats:ptr.append(pos);pos+=len(m)
    mat=header+struct.pack('>'+str(len(ptr))+'I',*ptr)+b''.join(mats);struct.pack_into('>I',mat,4,len(mat));parts[mi]=('mat1',mat)
    pic=bytearray(next(b for t,b in parts if t=='pic1'));pic[12:36]=b'P_CTGPSettingsGray_00'.ljust(24,bytes(1));pic[9]=4;pic[10]=255
    struct.pack_into('>10f',pic,44,75,35,0,0,0,0,1,1,72,72);pic[84:100]=bytes([255])*16;struct.pack_into('>H',pic,100,n);pic[102]=1;struct.pack_into('>8f',pic,104,0,0,1,0,0,1,1,1)
    # Parent under N_Contens_00: inherit the native footer entry/exit transform,
    # opacity and visibility instead of drawing early at RootPane scope.
    parent=next(i for i,(t,b) in enumerate(parts) if t=='pan1' and bflyt.cstr(b[12:36])=='N_Contens_00')
    depth=0;closing=None
    for i in range(parent+1,len(parts)):
        if parts[i][0]=='pas1':depth+=1
        elif parts[i][0]=='pae1':
            depth-=1
            if depth==0:closing=i;break
    if closing is None:raise ValueError('Footer group has no closing marker')
    # Keep the art inside the actual native footer control, so press/hold
    # animations affect it exactly like Statistics, not an unrelated picture.
    touch=bytearray(next(b for t,b in parts if t=='prt1' and bflyt.cstr(b[12:36])=='L_TopMenuContents_00'))
    touch[12:36]=b'P_SettingsTouch_00'.ljust(24,bytes(1));struct.pack_into('>3f',touch,44,75,0,0);struct.pack_into('>2f',touch,68,1,1)
    pos=0;patched=set()
    while True:
        pos=touch.find(b'pic1',pos)
        if pos<0:break
        name=bflyt.cstr(touch[pos+12:pos+36])
        if name=='P_MnMiiverse_00':struct.pack_into('>H',touch,pos+100,n);patched.add(name)
        if name=='P_PlusBtnIcon_00':struct.pack_into('>H',touch,pos+100,n+1);patched.add(name)
        pos+=4
    if patched!={'P_MnMiiverse_00','P_PlusBtnIcon_00'}:raise ValueError('Native footer image overrides missing')
    parts[closing:closing]=[('prt1',touch)]
    def rebuild(data,parts):
        head=bytearray(data[:20]);body=b''.join(b for t,b in parts);struct.pack_into('>I',head,12,20+len(body));struct.pack_into('>H',head,16,len(parts));return bytes(head)+body
    single=0x44e1a771;oldsingle=entries[single];sp=[(t,bytearray(oldsingle[o:o+n])) for t,o,n in bflyt.sections(oldsingle)]
    b=bytearray(next(b for t,b in sp if t=='txt1'));b[12:36]=b'T_CTGPOptions_00'.ljust(24,bytes(1));b[8]&=~1;b[9]=4
    struct.pack_into('>3f',b,44,-290,285,0);struct.pack_into('>2f',b,76,650,70)
    off=struct.unpack_from('>I',b,100)[0];text='Options'.encode('utf-16-be')+bytes(2);b=b[:off]+text;b.extend(bytes(-len(b)%4));struct.pack_into('>I',b,4,len(b));struct.pack_into('>HH',b,84,len(text),len(text));struct.pack_into('>2f',b,112,42,42)
    closing=max(i for i,(t,x) in enumerate(sp) if t=='pae1');sp.insert(closing,('txt1',b))
    gear=Path(__file__).resolve().parents[1]/'work/options_panel/settings_gray.bflim'
    merged=character_menu.replace_archive(packed,{top:rebuild(old,parts),single:rebuild(oldsingle,sp)},{'timg/tc_CTGP_SettingsGray^l.bflim':gear.read_bytes()})
    with tempfile.TemporaryDirectory() as tmp:
        p=Path(tmp)/'menu.sarc';p.write_bytes(merged);out=Path(tmp)/'menu.szs'
        subprocess.run([r'C:/Program Files/Wiimm/SZS/wszst.exe','compress',str(p),'--yaz0','--dest',str(out)],check=True,capture_output=True)
        result=out.read_bytes();assert szs.yaz0_decode(result)==merged;Path(output).write_bytes(result)
    original={h:b for n,b,h,a in szs.sarc_info(szs.yaz0_decode(Path(source).read_bytes()))[0]}
    after={h:b for n,b,h,a in szs.sarc_info(merged)[0]}
    assert set(after)-set(original)=={szs.sarc_hash('timg/tc_CTGP_SettingsGray^l.bflim')}
    assert all(after[h]==b for h,b in original.items() if h not in (top,single))
