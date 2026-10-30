"""Build an independent R.O.B. slot candidate against the installed EUR81 RPX.

Build writes only a separate candidate. Gameplay/voice/CPU validation is pending.
"""
from pathlib import Path
import argparse,json,struct,subprocess,tempfile
import rpxlib,costume_patch as patch,character_assets as assets,bflyt,szs

SOURCE=Path(__file__).parent/'native/character_slots.c'
MARKER=b'MK8_INDEPENDENT_ROB_EUR81_V1'
HOOKS={'char_create':0x025d623c,'char_setup':0x025d65f4,
       'char_available':0x025d6470,'char_button':0x0257c49c,
       'char_icon':0x0255a668,'char_name':0x025d269c,'char_finalise':0x0242fc70,
       'char_texture_name':0x0255a6e0,'char_sound_lookup':0x02060fb8,'char_audio_init':0x02068904,
       'char_menu_voice':0x020cc99c}
WORDS={'char_create':0x9421ffb0,'char_setup':0x9421feb8,
       'char_available':0x7c0802a6,'char_button':0x9421ff60,
       'char_icon':0x81440000,'char_name':0x9421ffc0,'char_finalise':0x7c0802a6,
       'char_texture_name':0x9421ffa0,'char_sound_lookup':0x80630004,'char_audio_init':0x9421ff08,
       'char_menu_voice':0x9421ff20}
TARGETS={'char_create':'character_create','char_setup':'character_setup',
         'char_available':'character_available','char_button':'character_button',
         'char_icon':'character_icon','char_name':'character_name','char_finalise':'character_finalise',
         'char_texture_name':'character_texture_name','char_sound_lookup':'character_sound_lookup','char_audio_init':'character_audio_init',
         'char_menu_voice':'character_menu_voice'}
HORN=0x02623d30
AUDIO_CLASS=0x0206897c
VOICE_PREFIX_BOUND=0x02067798

def voice_prefix_patch(sections):
    # UI selection and race voice events share this prefix formatter. Its
    # original early return rejects ID37 before the expanded DRSE is read.
    if rpxlib.word_at(sections,VOICE_PREFIX_BOUND)!=0x28040025:
        raise ValueError('Unexpected voice prefix character bound')
    return {VOICE_PREFIX_BOUND:0x28040026}
ARRAYS={0x025d2cb0:(12,3),0x025d6288:(27,30),0x025d6af0:(31,15),
        0x025d7cfc:(23,31),0x025d8e1c:(23,31),0x025d9a68:(24,31),
        0x025d9d40:(24,31),0x025dbe0c:(10,28),0x025dc5e8:(31,28)}
# Only audited control counts/bounds. 0x24 also means Villager's ID elsewhere.
COUNTS=[0x025d6270,0x025d62ac,0x025d631c,0x025d2ca8,
        0x025d7dc0,0x025d7e04,0x025d7e34,0x025d7e68,
        0x025d8e3c,0x025d8f64,0x025d9a78,0x025d9aa0,0x025d9ad0,
        0x025d9d4c,0x025d9d74,0x025d9da0,0x025d9dfc,0x025d9e24,
        0x025d9e50,0x025d9e7c,0x025d9ed4,0x025d9f1c,
        0x025dbdf4,0x025dbe08,0x025dc5f4,0x025dc668,0x025dc67c,
        0x025dc698,0x025dc6d0,0x025dc6e0,0x025dc6f4,0x025dc710,
        0x025dc730,0x025dc75c]
STRIDES=[0x0242bed0,0x0242bf3c,0x0242e4e0,0x02556588,0x02556db8]

def array_gateway(address,dst,src):
    name='character_array_%08x'%address
    out=['.balign 4','.global '+name,name+':','stwu 1,-96(1)','stw 0,8(1)',
         'mflr 0','stw 0,12(1)','mfcr 0','stw 0,16(1)',
         'mfctr 0','stw 0,20(1)','mfxer 0','stw 0,24(1)']
    out += [f'stw {r},{32+(r-3)*4}(1)' for r in range(3,13)]
    out += [f'mr 3,{src}','bl character_button_array','stw 3,28(1)']
    out += [f'lwz {r},{32+(r-3)*4}(1)' for r in range(3,13)]
    out += ['lwz 0,20(1)','mtctr 0','lwz 0,24(1)','mtxer 0',
            'lwz 0,16(1)','mtcrf 255,0','lwz 0,12(1)','mtlr 0',
            'lwz 0,8(1)',f'lwz {dst},28(1)','addi 1,1,96',
            f'b return_array_{address:08x}']
    return out

def branch_target(address,word):
    if word&0xfc000003!=0x48000000:raise ValueError('Expected existing tail hook')
    offset=word&0x03fffffc
    if offset&0x02000000:offset-=0x04000000
    return address+offset

def recipe_gateway(sections):
    code=next(s for s in sections if s['addr']==0x02b10000)
    matches=[]
    for off in range(0,len(code['data'])-7,4):
        a,b=struct.unpack_from('>II',code['data'],off)
        if a==0x9421fea8 and b&0xfc000003==0x48000000:
            if branch_target(code['addr']+off+4,b)==0x0242bde0:matches.append(code['addr']+off)
    if len(matches)!=1:raise ValueError('Ambiguous original vehicle recipe gateway')
    return matches[0]

def check_entry(sections,address,expected):
    word=rpxlib.word_at(sections,address)
    if word!=expected:raise ValueError('Unexpected entry instruction at %08x'%address)
    # Native functions may save LR before allocating their frame. Starting a
    # C wrapper at stwu then loses the preceding mflr's live r0 value.
    if word>>26==37 and rpxlib.word_at(sections,address-4)==0x7c0802a6:
        raise ValueError('Hook is after mflr rather than at function entry: %08x'%address)

def compile_module(tmp,sections,cb,db,private_voice=False):
    gcc,nm=patch.compiler_tools();assembly=['.section .text.tramp,"ax",@progbits']
    for name,a in HOOKS.items():
        word=rpxlib.word_at(sections,a)
        check_entry(sections,a,WORDS[name])
        assembly += ['.balign 4','.global original_'+name,'original_'+name+':',
                     '.long 0x%08x'%word,'b return_'+name]
    for a,(dst,src) in ARRAYS.items():assembly+=array_gateway(a,dst,src)
    assembly+=['.balign 4','.global character_horn_name','character_horn_name:',
               'stwu 1,-16(1)','stw 0,4(1)','mfcr 0','stw 0,8(1)',
               'cmpwi 29,38','bne horn_invalid','lis 5,character_resource_name@ha',
               'addi 5,5,character_resource_name@l','b horn_done','horn_invalid:',
               'li 5,0','horn_done:','lwz 0,8(1)','mtcrf 255,0','lwz 0,4(1)',
               'addi 1,1,16','b return_char_horn']
    # This audio reader only distinguishes native Mii from ordinary drivers.
    # Keep the actual selected ID 37; alias its one temporary name-table index.
    assembly+=['.balign 4','.global character_audio_class','character_audio_class:',
               'cmpwi 27,38','bne audio_class_done','li 27,29','audio_class_done:',
               'cmplwi 27,38','b return_char_audio_class']
    recipe=recipe_gateway(sections)
    assembly+=['.balign 4','.global previous_char_recipe','previous_char_recipe:',
               '.long 0x9421fea8','b return_char_recipe']
    (tmp/'gateway.S').write_text('\n'.join(assembly)+'\n')
    previous={name:branch_target(a,rpxlib.word_at(sections,a))
              for name,a in [('previous_char_prefix',0x0242bcd0),('previous_char_vehicle_icon',0x02557754)]}
    linker=''.join('%s = 0x%x;\n'%(n,a) for n,a in previous.items())
    linker+=''.join('return_%s = 0x%x;\n'%(n,a+4) for n,a in HOOKS.items())
    linker+=''.join('return_array_%08x = 0x%x;\n'%(a,a+4) for a in ARRAYS)
    linker+='return_char_recipe = 0x%x;\n'%(recipe+4)
    linker+='return_char_horn = 0x%x;\n'%(HORN+4)
    linker+='return_char_audio_class = 0x%x;\n'%(AUDIO_CLASS+4)
    linker+=f'SECTIONS {{ .text 0x{cb:x} : {{ *(.text*) *(.rodata*) }} .data 0x{db:x} : {{ *(.data*) *(.sdata*) BYTE(0) }} .bss ALIGN(4) : {{ *(.bss*) *(.sbss*) *(COMMON) }} /DISCARD/ : {{ *(.comment) *(.eh_frame*) }} }}'
    (tmp/'module.ld').write_text(linker)
    elf=tmp/'module.elf'
    run=subprocess.run([str(gcc),'-Os','-ffreestanding','-fno-builtin','-fno-pic','-fno-stack-protector',
        '-fno-asynchronous-unwind-tables','-fno-unwind-tables','-mcpu=750','-m32','-mbig-endian',
        '-msdata=none','-ffixed-r2','-ffixed-r13','-Wall','-Wextra','-Werror','-nostdlib',
        *(['-DROB_PRIVATE_VOICE'] if private_voice else []),
        '-Wl,--build-id=none','-Wl,-T,'+str(tmp/'module.ld'),str(SOURCE),str(tmp/'gateway.S'),'-lgcc','-o',str(elf)],capture_output=True,text=True)
    if run.returncode:raise ValueError(run.stdout+run.stderr)
    symbols={}
    for line in subprocess.check_output([str(nm),'-n',str(elf)],text=True).splitlines():
        fields=line.split()
        if len(fields)==3:symbols[fields[2]]=int(fields[0],16)
        elif 'U' in fields:raise ValueError('Unresolved native symbol')
    _,parts=rpxlib.load(elf)
    code=next(s['data'] for s in parts if s['name']=='.text')
    mutable=[s for s in parts if s['name'] in ('.data','.bss') and s['size']]
    end=max(db,*[s['addr']+s['size'] for s in mutable]);data=bytearray(end-db)
    if len(data)>0x1000:raise ValueError('State reservation exceeded')
    for s in mutable:
        if s['t']!=8:data[s['addr']-db:s['addr']-db+len(s['data'])]=s['data']
    return code,bytes(data),symbols

def build(source,output,private_voice=False):
    source,output=Path(source),Path(output)
    raw,sections=rpxlib.load(source)
    if any(MARKER in s['data'] for s in sections):raise ValueError('Already installed')
    code=next(s for s in sections if s['addr']==0x02b10000)
    data=next(s for s in sections if s['addr']==0x10300000)
    cb=(code['addr']+len(code['data'])+4095)&~4095
    db=(data['addr']+len(data['data'])+4095)&~4095
    with tempfile.TemporaryDirectory() as tmp:text,mutable,symbols=compile_module(Path(tmp),sections,cb,db,private_voice)
    patches={a:patch.branch(a,symbols[TARGETS[n]]) for n,a in HOOKS.items()}
    if private_voice:patches.update(voice_prefix_patch(sections))
    if rpxlib.word_at(sections,HORN)!=0x38a00000:raise ValueError('Unexpected horn-name fallback')
    patches[HORN]=patch.branch(HORN,symbols['character_horn_name'])
    if rpxlib.word_at(sections,AUDIO_CLASS)!=0x281b0026:raise ValueError('Unexpected audio driver-name bound')
    patches[AUDIO_CLASS]=patch.branch(AUDIO_CLASS,symbols['character_audio_class'])
    for a,(dst,src) in ARRAYS.items():
        expected=0x380002fc|(dst<<21)|(src<<16)
        if rpxlib.word_at(sections,a)!=expected:raise ValueError('Unexpected inline pointer')
        patches[a]=patch.branch(a,symbols['character_array_%08x'%a])
    for a in COUNTS:
        word=rpxlib.word_at(sections,a)
        if word&0xffff!=36:raise ValueError('Unexpected control bound')
        patches[a]=word+1
    for a in STRIDES:
        word=rpxlib.word_at(sections,a)
        if word>>26!=7 or word&0xffff!=37:raise ValueError('Unexpected character stride')
        patches[a]=word+1
    # Enter after the existing vehicle wrapper has retained its recipe flags.
    # Copying its source descriptor before that wrapper would lose custom karts.
    for a,n in [(recipe_gateway(sections),'character_recipe'),(0x0242bcd0,'character_prefix'),(0x02557754,'character_vehicle_icon')]:
        patches[a]=patch.branch(a,symbols[n])
    relocs={a for s in sections if s['name']=='.rela.text' for a,_,_ in struct.iter_unpack('>III',s['data'])}
    patch.check_relocation_overlap(patches,relocs)
    changes=[]
    for a,word in sorted(patches.items()):
        s=next(s for s in sections if s['addr']<=a<s['addr']+len(s['data']))
        before=rpxlib.word_at(sections,a);b=bytearray(s['data']);struct.pack_into('>I',b,a-s['addr'],word);s['data']=bytes(b)
        changes.append({'address':a,'before':before,'after':word})
    code['data']+=bytes(cb-code['addr']-len(code['data']))+text
    data['data']+=bytes(db-data['addr']-len(data['data']))+mutable
    info=next(s for s in sections if s['t']==0x80000004);b=bytearray(info['data'])
    for offset,end,base in ((4,cb+len(text),0x02000000),(12,db+len(mutable),0x10000000)):
        struct.pack_into('>I',b,offset,max(struct.unpack_from('>I',b,offset)[0],((end+255)&~255)-base))
    info['data']=bytes(b)
    result=patch.repack(raw,sections);output.parent.mkdir(parents=True,exist_ok=True);output.write_bytes(result)
    _,check=rpxlib.load(output)
    for s in sections:
        if s['t']!=0x80000003 and s['data']!=next(t['data'] for t in check if t['i']==s['i']):raise ValueError('RPX roundtrip differs')
    manifest={'source_sha256':assets.digest(raw),'output_sha256':assets.digest(result),
              'status':'experimental-uninstalled','character_id':37,'stats_donor':'Morton',
              'changes':changes,'symbols':symbols,'voice_isolation':private_voice,'voice_gameplay_tested':False,
              'cpu_roster':False,'gameplay_tested':False}
    Path(str(output)+'.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True,type=Path);p.add_argument('--output',required=True,type=Path)
    p.add_argument('--private-voice',action='store_true')
    a=p.parse_args();print(json.dumps(build(a.source,a.output,a.private_voice),indent=2))
