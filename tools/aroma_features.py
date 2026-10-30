"""Append the EUR v81 costume/vehicle runtime to an existing verified Aroma pack.

Input game must be the unmodified v81 RPX. This recompiles our own native
sources for console addresses; a Cemu Turbo.rpx cannot be copied to Aroma.
"""
import argparse,json,struct,tempfile
from pathlib import Path
import costume_patch as patch
import vehicle_patch as vehicles
import vehicle_catalog as catalog
import rpxlib,retarget
from mkpack import parse_hax,write_hax

def private_cup0_path(data):
    """Keep blob pointers fixed while moving CUP0 out of game root enumeration."""
    offset=0x17dc
    old=b'data.cup0'+bytes(3)
    new=b'custom/cup0'+bytes(1)
    if data[offset:offset+12] not in (old,new):
        raise ValueError('Unknown CUP0 filename slot; refusing to relocate it')
    return data[:offset]+new+data[offset+12:]

def console_address(a):
    if 0x02000000<=a<0x02c00000:return a+retarget.GT_SHIFT
    if 0x10000000<=a<0x10300000:return a+retarget.GD_SHIFT
    return a

def build(pack,stock,output,cemu_baseline=None):
    pack,stock,output=map(Path,(pack,stock,output))
    _,sections=rpxlib.load(stock)
    code=(pack/'Code.bin').read_bytes();data=(pack/'Data.bin').read_bytes()
    if cemu_baseline:
        # Carry the two existing signed-field CTGP fixes and the speedometer
        # format from the user's proven Cemu baseline, with exact guards.
        _,cemu=rpxlib.load(cemu_baseline)
        current=next(s['data'] for s in cemu if s['addr']==0x02b10000)
        current_data=next(s['data'][32:] for s in cemu if s['addr']==0x10300000)
        mapped,mapped_data,_=retarget.Blob(code,data).retarget(0x02b10000,0x10300020,
            lambda a:a-retarget.GT_SHIFT,lambda a:a-retarget.GD_SHIFT)
        differences=[i for i in range(0,len(mapped),4) if mapped[i:i+4]!=current[i:i+4]]
        if differences!=[0x23d0,0x23e0]:raise ValueError('Unexpected CTGP code differences from Cemu baseline')
        expected=[0x54ac3032,0x7d8c3670,0x558c003a,0x4bffab28,
                  0x552b3032,0x7d6b3670,0x556b003a,0x4bffab28]
        if current[0x78a0:0x78c0]!=struct.pack('>8I',*expected):raise ValueError('Unknown signed-field CTGP helpers')
        data_diff=[i for i in range(len(data)) if mapped_data[i]!=current_data[i]]
        if data_diff!=list(range(0x1954,0x1959)) or data[0x1954:0x1959]!=b' km/h' or any(current_data[i] for i in data_diff):raise ValueError('Unknown CTGP data changes')
        code=bytearray(code);code.extend(bytes(0x78c0-len(code)))
        for offset in differences:code[offset:offset+4]=current[offset:offset+4]
        code[0x78a0:0x78c0]=current[0x78a0:0x78c0];code=bytes(code)
        data=bytearray(data);data[0x1954:0x1959]=bytes(5);data=bytes(data)
    if struct.unpack('>II',(pack/'Addr.bin').read_bytes())!=(retarget.CB,retarget.DB):raise ValueError('Unsupported console pack layout')
    patches=parse_hax((pack/'Patches.hax').read_bytes());verify=parse_hax((pack/'Verify.hax').read_bytes())
    if len(patches)!=len(verify) or [a for a,d in patches]!=[a for a,d in verify]:raise ValueError('Pack verification coverage differs')
    hooks={**patch.HOOKS,**vehicles.VEHICLE_HOOKS}
    expected={a:w for a,w in hooks.values()};expected.update(patch.PREFIX_CALLS)
    expected.update({a:p[0] for a,p in vehicles.STRIDES.items()})
    relocs={a for s in sections if s['name']=='.rela.text' for a,_,_ in struct.iter_unpack('>III',s['data'])}
    patch.check_relocation_overlap(expected,relocs)
    for a,w in expected.items():
        if rpxlib.word_at(sections,a)!=w:raise ValueError('Wrong stock game build at %08x'%a)
    if set(console_address(a) for a in expected)&set(a for a,d in patches):raise ValueError('Feature hook conflicts with existing CTGP hook')
    # Keep original CTGP blobs intact and append within the existing loader's
    # mapped code/data areas, with alignment and independent mutable storage.
    code_offset=(len(code)+4095)&~4095;data_offset=(len(data)+4095)&~4095
    code_base=retarget.CB+code_offset;data_base=retarget.DB+data_offset
    saved=(patch.HOOKS,patch.PREFIX_SITES,patch.EXTRA_CFLAGS,patch.EXTRA_ASSEMBLY,patch.CODE,patch.DATA)
    try:
        patch.HOOKS={n:(console_address(a),w) for n,(a,w) in hooks.items()}
        patch.PREFIX_SITES=tuple(console_address(a) for a in patch.PREFIX_SITES)
        patch.EXTRA_CFLAGS=['-DVEHICLE_SLOTS'];patch.EXTRA_ASSEMBLY=vehicles.GATEWAY
        patch.CODE,patch.DATA=code_base,data_base
        with tempfile.TemporaryDirectory(prefix='mk8-aroma-features-') as tmp:
            native,mutable,symbols=patch.compile_native(Path(tmp),address_map=console_address)
    finally:
        patch.HOOKS,patch.PREFIX_SITES,patch.EXTRA_CFLAGS,patch.EXTRA_ASSEMBLY,patch.CODE,patch.DATA=saved
    added=[]
    for name,(address,before) in hooks.items():
        at=console_address(address);target=symbols['costume_'+name]
        added.append((at,struct.pack('>I',patch.branch(at,target)),struct.pack('>I',before)))
    for i,(address,before) in enumerate(patch.PREFIX_CALLS.items()):
        at=console_address(address);word=patch.branch(at,symbols['costume_prefix_'+str(i)])|1
        added.append((at,struct.pack('>I',word),struct.pack('>I',before)))
    for address,(before,after) in vehicles.STRIDES.items():
        added.append((console_address(address),struct.pack('>I',after),struct.pack('>I',before)))
    final_code=code+bytes(code_offset-len(code))+native
    final_code+=bytes((-len(final_code))%4)+struct.pack('>I',0x4e800020)
    final_data=data+bytes(data_offset-len(data))+mutable
    final_data=private_cup0_path(final_data)
    # Plugin log pointer always refers to the final blr word, independently of
    # the original pack's old stub. No feature entry point depends on that stub.
    files={'Addr.bin':(pack/'Addr.bin').read_bytes(),'Code.bin':final_code,'Data.bin':final_data,
           'Patches.hax':write_hax(patches+[(a,d) for a,d,v in added]),
           'Verify.hax':write_hax(verify+[(a,v) for a,d,v in added])}
    for name,payload in files.items():
        if name.endswith('.hax'):parse_hax(payload)
    output.mkdir(parents=True,exist_ok=True)
    for name,payload in files.items():(output/name).write_bytes(payload)
    manifest={'region':'EUR','game_version':81,'console_tested':False,
              'features':['CTGP','Mario/DK costumes','custom part icons']+[c['name'] for c in catalog.CHOICES],
              'catalog':{'bodies':catalog.BODIES,'tires':catalog.TIRES},
              'stock_sha256':patch.digest(stock.read_bytes()),'feature_code_base':code_base,'feature_data_base':data_base,
              'symbols':symbols,'added_hooks':len(added),'files':{n:patch.digest(d) for n,d in files.items()},
              'content_required':['ui','custom','common/mush/Parts.bin','common/mush/Performance.bin'],
              'note':'Experimental console build; requires matching CTGP content and real Wii U testing.'}
    (output/'Features.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('Built EUR v81 console feature pack:',len(added),'guarded hooks; console testing required')
    return manifest

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--pack',required=True);p.add_argument('--stock',required=True);p.add_argument('--output',required=True);p.add_argument('--cemu-baseline');a=p.parse_args()
    build(a.pack,a.stock,a.output,a.cemu_baseline)
