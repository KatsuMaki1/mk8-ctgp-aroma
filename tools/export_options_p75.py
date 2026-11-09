"""Export the P46 (CTGP server id 1010EB01) payload as an Aroma code pack, protecting UTF-16 from relocation."""
from pathlib import Path
import sys,json
import rpxlib,rpx_to_aroma
WORK=Path('C:/Users/evant/Documents/Codex/2026-10-25/files-mentioned-by-the-user-handoff/work')
REPO=Path(__file__).resolve().parents[1]
def run():
 nonptr=set()
 for file,count in [('booster_pass_20261031/r3/Turbo_Booster48_R3.rpx.json',1502),('tt200/Turbo_TT200_P4.rpx.json',4),('dlc_paths/Turbo_Custom_AOC.rpx.json',3712)]:
  meta=json.loads((WORK/file).read_text());a=meta['symbols']['bcp_assets'];nonptr.update(a+i*8 for i in range(count))
 _,old=rpxlib.load(WORK/'dlc_paths/Turbo_Custom_AOC.rpx')
 oldmeta=json.loads((WORK/'dlc_paths/Turbo_Custom_AOC.rpx.json').read_text())
 oldend=0x2b10000+len(next(x['data'] for x in old if x['addr']==0x2b10000))
 native=WORK/'booster_pass_20261031/r4/Turbo_BCP_R4.rpx'
 nm=json.loads(Path(str(native)+'.json').read_text());_,ns=rpxlib.load(native)
 newend=0x2b10000+len(next(x['data'] for x in ns if x['addr']==0x2b10000))
 nonptr.update(nm['symbols']['bcp_assets']+i*8 for i in range(nm['assets']))
 source=WORK/'pink_drift_p2/Turbo_Options_P75_WwCtCard.rpx'
 meta=json.loads(Path(str(source)+'.json').read_text());symbols=meta['symbols'];_,ss=rpxlib.load(source)
 code=next(s['data'] for s in ss if s['addr']==0x2b10000);end=0x2b10000+len(code)
 addresses=sorted(set(v for v in symbols.values() if 0x2b10000<=v<=end))+[end]
 strings=[]
 for name,a in symbols.items():
  if not name.startswith('__compound_literal.'):continue
  stop=next(x for x in addresses if x>a);strings.append((a,stop))
  nonptr.update(range(a&~3,(stop+3)&~3,4))
 out=WORK/'aroma_p75/release/sd/cafeloader/000500001010ED00'
 report=rpx_to_aroma.build(source,Path('C:/Users/evant/AppData/Roaming/Cemu/mlc01/usr/title/0005000e/1010ed00/code/Turbo.rpx.bak'),out,
  noncode=[(oldmeta['symbols']['_restgpr_31_x']+20,oldend),(nm['symbols']['_restgpr_31_x']+20,newend),(symbols['_restgpr_31_x']+20,(symbols['_restgpr_31_x']+0xfff)&~0xfff)],nonpointer_words=nonptr)
 converted=(out/'Code.bin').read_bytes()
 for a,stop in strings:assert converted[a-0x2b10000:stop-0x2b10000]==code[a-0x2b10000:stop-0x2b10000],'UTF-16 was relocated as an address'
 report['features']=['CTGP game server id 1010EB01 (own matchmaking pool)','CTGP R4 fixes and corrected Booster order','Maple Wiggler routes and Sundae fix','ROB R20 audio adapter',
  'Native Options selectors P6, 119 country IDs, eight EUR languages','Cached message refresh and Solo focus repair','TT 150/200 P4','DSI capture retained by v0.28 plugin']
 report.update(country_online_flag_fixed=False,options_console_validated=False,utf16_literals_preserved=len(strings),optimization_profile='R3')
 (out/'Features.json').write_text(json.dumps(report,indent=2)+'\n')
 (WORK/'aroma_p75/export_verification.json').write_text(json.dumps({'hooks':report['patch_count'],'utf16_literals_checked':len(strings),'source_rpx':str(source),'protected_words':len(nonptr)},indent=2))
 print('Export verified:',report['patch_count'],'hooks;',len(strings),'UTF16 literals byte-identical.',flush=True)
if __name__=='__main__':run()
