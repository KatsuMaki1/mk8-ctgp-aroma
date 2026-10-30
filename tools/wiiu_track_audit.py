"""Stage a read-only profile of the current pack's original custom courses."""
from pathlib import Path
import sys,json,struct,subprocess,hashlib
import cup0,szs,byml_dump
CONTENT=Path('C:/Users/evant/AppData/Roaming/Cemu/mlc01/usr/title/0005000e/1010ed00/content')
ROOT=Path('C:/Users/evant/Documents/Codex/2026-10-25/files-mentioned-by-the-user-handoff/work/wiiu_optimization')
TARGETS={'Gu_SkyArena','Gu_DivBowser','Gu_PacMountain','Gu_BoulderCanyon','Gu_DelfinoIsle','Gu_GhostValley3','Gu_N64MarioRaceway2','Gu_ChocoIsland1'}
def run():
    ROOT.mkdir(parents=True,exist_ok=True);report=[]
    for c in cup0.parse((CONTENT/'data.cup0').read_bytes()):
        if c.type!=2:continue
        for t in c.tracks:
            folder=CONTENT/'course'/t.dir;model=folder/'course_model.szs';raw=model.read_bytes()
            mu=byml_dump.parse((folder/'course_muunt.byaml').read_bytes())
            objects=mu.get('Obj',[])
            item={'cup':c.name,'name':t.name,'directory':t.dir,'compressed_model_bytes':len(raw),'uncompressed_model_bytes':struct.unpack_from('>I',raw,4)[0] if raw[:4]==b'Yaz0' else len(raw),'objects':len(objects),'object_counts':{str(i):sum(x.get('ObjId')==i for x in objects) for i in sorted({x.get('ObjId',-1) for x in objects})},'files':{p.name:{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in folder.iterdir() if p.is_file()}}
            report.append(item)
            if t.dir in TARGETS:
                dest=ROOT/t.dir;dest.mkdir(exist_ok=True)
                arc=dest/'model.sarc'
                if not arc.exists():
                    subprocess.run(['C:/Program Files/Wiimm/SZS/wszst.exe','decompress',str(model),'--dest',str(arc),'--overwrite','--max-file-size=256m'],check=True,stdout=subprocess.DEVNULL)
                data=arc.read_bytes()
                if data[:4]==b'FRES':entries=[('model.bfres',data,0,0)];ver=None
                else:entries,off,ver=szs.sarc_info(data)
                models=[(n,b) for n,b,h,a in entries if b[:4]==b'FRES']
                assert len(models)==1,(t.dir,[n for n,b in models])
                name,b=models[0];(dest/'model.bfres').write_bytes(b)
                (dest/'archive.json').write_text(json.dumps({'bfres_member':name,'members':[(n,len(b),a) for n,b,h,a in entries],'version':ver,'alignments':szs.sarc_aligns(data,0x20) if ver else {}},indent=2))
                print(t.dir,len(b),len(objects),flush=True)
    (ROOT/'inventory.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Audited',len(report),'courses; targeted',len(TARGETS))
if __name__=='__main__':run()

