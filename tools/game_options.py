"""Reversible Cemu EUR81 game-options / per-course sky prototype."""
from pathlib import Path
import argparse, hashlib, json, struct, subprocess, tempfile
import costume_patch as patch
import costumes, rpxlib, szs, bflyt

CODE, DATA = 0x02b1b000, 0x10305000
MARKER = b'MK8_GAME_OPTIONS_EUR81_V1'
HOOKS = {
    'format0': (0x0272c02c, 0x7c0802a6),
    'format1': (0x0272c240, 0x9421fd88),
    'format2': (0x0272c8fc, 0x7c0802a6),
    'create': (0x025eeb98, 0x9421ffc8),
    'event': (0x025efc94, 0x9421ffc0),
    'hud': (0x02b15758, 0x7c0802a6),
}

def sha(data): return hashlib.sha256(data).hexdigest()

def compile_module(directory, *, code_address=CODE, data_address=DATA, hooks=HOOKS, source=None, cflags=()):
    gcc, nm = patch.compiler_tools()
    assembly = ['.section .text.tramp,"ax",@progbits', '.balign 4']
    for name, (address, word) in hooks.items():
        assembly += [f'.global original_{name}', f'original_{name}:', f'.long 0x{word:x}', f'b return_{name}']
    (directory/'gateway.S').write_text('\n'.join(assembly)+'\n')
    (directory/'module.ld').write_text(
        ''.join(f'return_{n} = 0x{a+4:x};\n' for n,(a,w) in hooks.items())+
        f'SECTIONS {{ .text 0x{code_address:x} : {{ *(.text*) *(.rodata*) }} '
        f'.data 0x{data_address:x} : {{ *(.data*) *(.sdata*) BYTE(0) }} '
        '.bss ALIGN(4) : { *(.bss*) *(.sbss*) *(COMMON) } /DISCARD/ : { *(.comment) *(.eh_frame*) } }')
    elf=directory/'module.elf'
    subprocess.run([str(gcc),'-Os','-ffreestanding','-fno-builtin','-fno-pic','-fno-stack-protector',
        '-fno-asynchronous-unwind-tables','-fno-unwind-tables','-mcpu=750','-m32','-mbig-endian',
        '-msdata=none','-ffixed-r2','-ffixed-r13','-Wall','-Wextra','-Werror','-nostdlib',*cflags,
        '-Wl,--build-id=none','-Wl,-T,'+str(directory/'module.ld'),
        str(source or Path(__file__).parent/'native/game_options.c'),str(directory/'gateway.S'),'-lgcc','-o',str(elf)],
        check=True,capture_output=True,text=True)
    symbols={}
    for line in subprocess.check_output([str(nm),'-n',str(elf)],text=True).splitlines():
        fields=line.split()
        if len(fields)==3:symbols[fields[2]]=int(fields[0],16)
        elif fields and 'U' in fields:raise ValueError('Unresolved module symbol: '+line)
    _,sections=rpxlib.load(elf)
    code=next(s['data'] for s in sections if s['name']=='.text')
    mutable=[s for s in sections if s['name'] in ('.data','.bss') and s['size']]
    end=max(data_address,*[s['addr']+s['size'] for s in mutable]);data=bytearray(end-data_address)
    if end>data_address+0x1000:raise ValueError('Module state exceeds reservation')
    for s in mutable:
        if s['t']!=8:data[s['addr']-data_address:s['addr']-data_address+len(s['data'])]=s['data']
    return code,bytes(data),symbols

def build_rpx(source,output,sky_only=False):
    raw,sections=rpxlib.load(source)
    if any(MARKER in s['data'] for s in sections):raise ValueError('Restore GameOptions before rebuilding')
    code=next(s for s in sections if s['addr']==0x02b10000)
    data=next(s for s in sections if s['addr']==0x10300000)
    info=next(s for s in sections if s['t']==0x80000004)
    if code['addr']+len(code['data'])>CODE or data['addr']+len(data['data'])>DATA:raise ValueError('Payload reservation overlaps existing code/data')
    relocs={a for s in sections if s['name']=='.rela.text' for a,_,_ in struct.iter_unpack('>III',s['data'])}
    hooks={n:v for n,v in HOOKS.items() if not sky_only or n.startswith('format')}
    patch.check_relocation_overlap([a for a,w in hooks.values()],relocs)
    for name,(address,word) in hooks.items():
        if rpxlib.word_at(sections,address)!=word:raise ValueError('Wrong game/hook '+name)
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        text,mutable,symbols=compile_module(Path(tmp))
    if CODE+len(text)>0x02000000+struct.unpack_from('>I',info['data'],4)[0]:raise ValueError('Text reservation too small')
    changes=[]
    for name,(address,word) in hooks.items():
        section=next(s for s in sections if s['t']==1 and s['addr']<=address<s['addr']+len(s['data']))
        b=bytearray(section['data']);after=patch.branch(address,symbols['options_'+name]);struct.pack_into('>I',b,address-section['addr'],after);section['data']=bytes(b)
        changes.append({'name':name,'address':address,'before':word,'after':after})
    code['data']+=bytes(CODE-code['addr']-len(code['data']))+text
    data['data']+=bytes(DATA-data['addr']-len(data['data']))+mutable
    fileinfo=bytearray(info['data']);struct.pack_into('>I',fileinfo,12,max(struct.unpack_from('>I',fileinfo,12)[0],((DATA+len(mutable)+255)&~255)-0x10000000));info['data']=bytes(fileinfo)
    result=patch.repack(raw,sections);costumes.atomic_write(output,result)
    meta={'source_sha256':sha(raw),'output_sha256':sha(result),'changes':changes,'symbols':symbols,'sky_only':sky_only}
    _,after=rpxlib.load(output)
    for s in after:
        if s['t']==0x80000003:continue
        expected=next(x for x in sections if x['i']==s['i'])
        if s['data']!=expected['data']:raise ValueError('Repack payload mismatch')
    Path(str(output)+'.json').write_text(json.dumps(meta,indent=2)+'\n')
    return meta

def menu_button(source,output):
    packed=Path(source).read_bytes();raw=bytearray(szs.yaz0_decode(packed));offset=struct.unpack_from('>I',raw,12)[0]
    target=szs.sarc_hash('blyt/mn_TopMenu_00.bflyt');node=None
    for i in range(struct.unpack_from('>H',raw,26)[0]):
        pos=32+16*i;h,attr,a,b=struct.unpack_from('>4I',raw,pos)
        if h==target:node=pos;layout=bytes(raw[offset+a:offset+b]);break
    if node is None:raise ValueError('Main menu layout missing')
    sections=[(t,bytearray(layout[o:o+n])) for t,o,n in bflyt.sections(layout)]
    if any(b'P_Speedometer_00' in b for t,b in sections):raise ValueError('Menu button already installed')
    part=bytearray(next(b for t,b in sections if t=='prt1' and bflyt.cstr(b[12:36])=='P_Single_00'))
    # Offset the parts themselves so the menu entrance animations retain their
    # original parent transforms. Tighten the six rows to make room below.
    rows=['P_Single_00','P_Multi_00','P_OnlineSingle_00','P_OnlineMulti_00','P_MarioKartTV_00','P_Catalog_00']
    for t,b in sections:
        name=bflyt.cstr(b[12:36]) if t=='prt1' else ''
        if name in rows:
            struct.pack_into('>f',b,0x30,struct.unpack_from('>f',b,0x30)[0]+20.+5.*rows.index(name))
    part[12:36]=b'P_Speedometer_00'.ljust(24,bytes(1))
    struct.pack_into('>3f',part,0x2c,-345.,-170.,0.)
    struct.pack_into('>2f',part,0x44,0.55,0.55)
    # Insert as a direct child of RootPane, before its last closing marker.
    closing=max(i for i,(t,b) in enumerate(sections) if t=='pae1')
    sections.insert(closing,('prt1',part))
    header=bytearray(layout[:20]);body=b''.join(bytes(b) for t,b in sections)
    struct.pack_into('>I',header,12,20+len(body));struct.pack_into('>H',header,16,len(sections));new=bytes(header)+body
    while len(raw)%0x2000:raw+=bytes(1)
    start=len(raw)-offset;raw+=new;struct.pack_into('>II',raw,node+8,start,start+len(new));struct.pack_into('>I',raw,8,len(raw))
    with tempfile.TemporaryDirectory() as tmp:
        sarc=Path(tmp)/'menu.sarc';dest=Path(tmp)/'menu.szs';sarc.write_bytes(raw)
        subprocess.run([r'C:\Program Files\Wiimm\SZS\wszst.exe','compress',str(sarc),'--yaz0','--dest',str(dest)],check=True,capture_output=True)
        result=dest.read_bytes()
    if szs.yaz0_decode(result)!=raw:raise ValueError('Menu compression roundtrip mismatch')
    before={h:b for n,b,h,a in szs.sarc_info(szs.yaz0_decode(packed))[0]};after={h:b for n,b,h,a in szs.sarc_info(bytes(raw))[0]}
    if before.keys()!=after.keys() or any(before[h]!=after[h] for h in before if h!=target):raise ValueError('Unrelated menu resource changed')
    costumes.atomic_write(output,result)

def install(content,candidate,menu=None):
    patch.ensure_cemu_closed();content=Path(content);candidate=Path(candidate)
    target=content.parent/'code/Turbo.rpx';backup=content.parent/'code_backups/GameOptions';backup.mkdir(parents=True,exist_ok=True)
    if (backup/'state.json').exists():raise ValueError('GameOptions already tracked; restore before replacing')
    meta=json.loads(Path(str(candidate)+'.json').read_text())
    if sha(target.read_bytes())!=meta['source_sha256'] or sha(candidate.read_bytes())!=meta['output_sha256']:raise ValueError('Candidate/source changed')
    original=target.read_bytes();menu_path=content/'ui/cmn/menu.szs';old_menu=menu_path.read_bytes() if menu else None
    (backup/'Turbo.rpx').write_bytes(original)
    if old_menu is not None:(backup/'menu.szs').write_bytes(old_menu)
    try:
        costumes.atomic_write(target,candidate.read_bytes())
        if menu:costumes.atomic_write(menu_path,Path(menu).read_bytes())
        (backup/'state.json').write_text(json.dumps({'rpx':sha(target.read_bytes()),'menu':sha(menu_path.read_bytes()) if menu else None},indent=2)+'\n')
    except Exception:
        costumes.atomic_write(target,original)
        if old_menu is not None:costumes.atomic_write(menu_path,old_menu)
        raise

def restore(content):
    patch.ensure_cemu_closed();content=Path(content);backup=content.parent/'code_backups/GameOptions';state_path=backup/'state.json';state=json.loads(state_path.read_text());target=content.parent/'code/Turbo.rpx';menu=content/'ui/cmn/menu.szs'
    if sha(target.read_bytes())!=state['rpx'] or state['menu'] and sha(menu.read_bytes())!=state['menu']:raise ValueError('Installed files changed; refusing restore')
    costumes.atomic_write(target,(backup/'Turbo.rpx').read_bytes())
    if state['menu']:costumes.atomic_write(menu,(backup/'menu.szs').read_bytes())
    state_path.rename(backup/('state.restored-'+state['rpx'][:16]+'.json'))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['build','install','restore']);p.add_argument('--content',required=True);p.add_argument('--output');p.add_argument('--sky-only',action='store_true');a=p.parse_args();content=Path(a.content)
    if a.command=='build':
        if not a.output:p.error('--output is required')
        out=Path(a.output);build_rpx(content.parent/'code/Turbo.rpx',out,a.sky_only)
        if not a.sky_only:menu_button(content/'ui/cmn/menu.szs',str(out)+'.menu.szs')
    elif a.command=='install':install(content,a.output,None if a.sky_only else str(a.output)+'.menu.szs')
    else:restore(content)
