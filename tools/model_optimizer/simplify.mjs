import fs from 'node:fs';
// Use the locally audited meshoptimizer module; no network dependency.
const {MeshoptSimplifier:S}=await import(process.argv[2]);await S.ready;
const root=process.argv[3];let report=[];const r2=process.env.CTGP_OPT_PROFILE==='R2';
const deny=/road|ground|soil|dirt|sand|ramp|boost|jump|water|lava|flow|gravel|cobble|sea|startline|startgate|ef_|panel|arrow|bridge|fence|guard|rail|wall_road|offroad|grassoff|grassedg|zebra|kerb|curb|floor|paved|plank|track|sidewalk/i;
for(const dir of fs.readdirSync(root).filter(n=>fs.existsSync(root+'/'+n+'/meshes/meshes.json')&&(!process.argv[4]||n===process.argv[4]))){
 const folder=root+'/'+dir+'/meshes';let rows=[];
 for(const m of JSON.parse(fs.readFileSync(folder+'/meshes.json'))){
  const names=m.Name+' '+m.material;
  const decor=/tree|leaf|leav|plant|flower|rock|cliff|mount|build|house|tower|rope|chain|pipe|statue|cloud|wall|grass|object|prop|pole|light|trim|stone|brick|bark|palm|bush/i.test(names);
  if(deny.test(names)||dir==='Gu_GhostValley3'&&/wood/i.test(names)||r2&&!decor){
   const old=folder+'/'+m.id+'.newidx';if(fs.existsSync(old))fs.unlinkSync(old);continue;
  }
  function array(suffix,type){const b=fs.readFileSync(folder+'/'+m.id+suffix);return new type(b.buffer,b.byteOffset,b.length/type.BYTES_PER_ELEMENT);}
  const idx=array('.idx',Uint32Array),pos=array('.pos',Float32Array),attr=array('.attr',Float32Array);
  const weights=m.attributes.flatMap(n=>n==='_n0'?[.05,.05,.05]:n.startsWith('_c')?[.5,.5,.5,.5]:[.5,.5]);
  const [out,error]=S.simplifyWithAttributes(idx,pos,3,attr,m.stride,weights,null,Math.floor(idx.length*(r2?.5:.6)/3)*3,r2?3:2,['LockBorder','ErrorAbsolute']);
  if(out.length>=idx.length*.99)continue;
  fs.writeFileSync(folder+'/'+m.id+'.newidx',Buffer.from(out.buffer,out.byteOffset,out.byteLength));
  rows.push({id:m.id,name:m.Name,material:m.material,before:idx.length,after:out.length,error});
 }
 fs.writeFileSync(folder+'/simplification.json',JSON.stringify(rows,null,2));
 const row={directory:dir,shapes:rows.length,trianglesRemoved:rows.reduce((a,x)=>a+(x.before-x.after)/3,0)};report.push(row);console.log(JSON.stringify(row));
}
fs.writeFileSync(root+'/geometry_summary.json',JSON.stringify(report,null,2));
