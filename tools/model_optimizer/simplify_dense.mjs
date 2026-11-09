import fs from 'node:fs';
const {MeshoptSimplifier:S}=await import(process.argv[2]);await S.ready;S.useExperimentalFeatures=true;
const root=process.argv[3];
const deny=/road|ground|soil|dirt|sand|ramp|boost|jump|water|lava|flow|gravel|cobble|sea|startline|startgate|ef_|panel|arrow|bridge|fence|guard|rail|wall_road|offroad|grassoff|grassedg|zebra|kerb|curb|floor|paved|plank|track|sidewalk|sky|skydome|vr_/i;
const decor=/tree|leaf|leav|plant|flower|rock|cliff|mount|build|house|tower|rope|chain|pipe|statue|wall|grass|object|prop|pole|light|trim|stone|brick|bark|palm|bush|bench|barrel/i;
function activeTriangles(a){let count=0;for(let i=0;i<a.length;i+=3)if(a[i]!==a[i+1]&&a[i+1]!==a[i+2]&&a[i]!==a[i+2])count++;return count;}
for(const dir of fs.readdirSync(root)){
 const folder=root+'/'+dir+'/meshes';if(!fs.existsSync(folder+'/meshes.json')||fs.existsSync(root+'/'+dir+'/simplified.json'))continue;
 let stats=[];
 for(const m of JSON.parse(fs.readFileSync(folder+'/meshes.json'))){
  const names=m.Name+' '+m.material;if(deny.test(names)||!decor.test(names))continue;
  function array(ext,Type){const b=fs.readFileSync(folder+'/'+m.id+ext);return new Type(b.buffer,b.byteOffset,b.length/Type.BYTES_PER_ELEMENT);}
  const original=array('.idx',Uint32Array),pos=array('.pos',Float32Array),attr=array('.attr',Float32Array),output=Uint32Array.from(original);
  const weights=m.attributes.flatMap(n=>n==='_n0'?[.05,.05,.05]:n.startsWith('_c')?[.5,.5,.5,.5]:[.5,.5]);
  const size=m.index_format.includes('16')?2:4;let removed=0,changed=0;
  for(const part of m.submeshes){
   const begin=part.offset/size,count=part.count;
   if(!Number.isInteger(begin)||count%3||begin+count>original.length)throw Error('Invalid submesh extent');
   if(count<300)continue;
   const input=original.subarray(begin,begin+count);
   const [indices,error]=S.simplifyWithAttributes(input,pos,3,attr,m.stride,weights,null,Math.floor(count*.4/3)*3,3,['LockBorder','ErrorAbsolute']);
   if(indices.length>=count*.99)continue;
   // Preserve every native submesh offset/count and LOD descriptor. Fill the
   // unused tail with valid degenerate triangles rather than changing the
   // engine's culling/index-range metadata.
   output.set(indices,begin);output.fill(indices.length?indices[0]:input[0],begin+indices.length,begin+count);
   removed+=activeTriangles(input)-activeTriangles(indices);changed++;
  }
  if(removed){fs.writeFileSync(folder+'/'+m.id+'.newidx',Buffer.from(output.buffer));stats.push({id:m.id,name:m.Name,removed,submeshes:changed});}
 }
 fs.writeFileSync(root+'/'+dir+'/simplified.json',JSON.stringify(stats,null,2));
 console.log(dir,stats.reduce((n,s)=>n+s.removed,0),'decor triangles neutralized');
}
