// Export only, or verify an in-place BFRES patch without reserializing resources.
using System;using System.IO;using System.Linq;using System.Text.Json;using System.Collections.Generic;
using BfresLibrary;using BfresLibrary.Helpers;using Syroot.BinaryData;
using G=BfresLibrary.Swizzling.GX2;
class P {
static void WriteFloats(string path,IEnumerable<float> data){using var w=new BinaryWriter(File.Create(path));foreach(var x in data)w.Write(x);}
static void Main(string[] a){
var mode=a[0];var f=new ResFile(a[1]);var dir=a[2];Directory.CreateDirectory(dir);
if(mode=="profile"){
 var shapes=f.Models.Values.SelectMany(model=>model.Shapes.Values.Select(s=>new {model=model.Name,s.Name,material=model.Materials.Values.ElementAt(s.MaterialIndex).Name,triangles=s.Meshes[0].IndexCount/3}));
 var textures=f.Textures.Values.Cast<BfresLibrary.WiiU.Texture>().Select(t=>new {t.Name,t.Width,t.Height,t.MipCount,format=t.Format.ToString(),bytes=(t.Data?.Length??0)+(t.MipData?.Length??0)});
 File.WriteAllText(Path.Combine(dir,"profile.json"),JsonSerializer.Serialize(new{shapes,textures},new JsonSerializerOptions{WriteIndented=true}));return;
}
if(mode=="export"){
 int id=0;var rows=new List<object>();
 foreach(var model in f.Models.Values)foreach(var s in model.Shapes.Values){
  var m=s.Meshes[0];var mat=model.Materials.Values.ElementAt(s.MaterialIndex);int i=id++;
  if(s.VertexSkinCount!=0||s.Meshes.Count!=1||m.SubMeshes.Count!=1||m.PrimitiveType.ToString()!="Triangles"||m.IndexCount<3000)continue;
  var h=new VertexBufferHelper(model.VertexBuffers[s.VertexBufferIndex],ByteOrder.BigEndian);
  var p=h["_p0"].Data;WriteFloats(Path.Combine(dir,i+".pos"),p.SelectMany(v=>new[]{v.X,v.Y,v.Z}));
  var ns=new[]{"_n0","_u0","_u1","_c0","_c1"}.Where(n=>h.Attributes.Any(x=>x.Name==n)).ToArray();
  var attrs=ns.Select(n=>h[n].Data).ToArray();int stride=ns.Sum(n=>n=="_n0"?3:n.StartsWith("_c")?4:2);
  using(var w=new BinaryWriter(File.Create(Path.Combine(dir,i+".attr"))))for(int v=0;v<p.Length;v++)for(int j=0;j<ns.Length;j++){
   w.Write(attrs[j][v].X);w.Write(attrs[j][v].Y);if(ns[j]=="_n0"||ns[j].StartsWith("_c"))w.Write(attrs[j][v].Z);if(ns[j].StartsWith("_c"))w.Write(attrs[j][v].W);
  }
  using(var w=new BinaryWriter(File.Create(Path.Combine(dir,i+".idx"))))foreach(var ix in m.GetIndices())w.Write(ix+m.FirstVertex);
  rows.Add(new{id=i,model=model.Name,s.Name,material=mat.Name,vertices=p.Length,indices=m.IndexCount,first=m.FirstVertex,buffer_offset=m.IndexBuffer.BufferOffset,index_format=m.IndexFormat.ToString(),stride,attributes=ns});
 }
 File.WriteAllText(Path.Combine(dir,"meshes.json"),JsonSerializer.Serialize(rows,new JsonSerializerOptions{WriteIndented=true}));
 Console.WriteLine("Exported "+rows.Count+" eligible meshes");return;
}
if(mode=="textures"){
 var result=new List<object>();int id=0;
 foreach(var tex in f.Textures.Values.Cast<BfresLibrary.WiiU.Texture>()){
  int i=id++;if(Math.Max(tex.Width,tex.Height)<=512||tex.Depth!=1||tex.ArrayLength>1||tex.Data==null)continue;
  uint cap=tex.Name.ToLower().Contains("bake")||tex.Name.ToLower().Contains("light")||tex.Name.ToLower().Contains("shadow")||tex.Name=="B L"||tex.Name=="b"?2048u:1024u;
  if(a[1].Contains("Gu_DivBowser"))cap=1024;
  if(Environment.GetEnvironmentVariable("CTGP_OPT_PROFILE")=="R2"){
   string n=tex.Name.ToLower();
   bool readable=new[]{"road","ground","asphalt","logo","sign","arrow","text","start","line","zebra"}.Any(x=>n.Contains(x));
   bool bake=new[]{"bake","light","shadow","aomap"}.Any(x=>n.Contains(x))||n=="b l"||n=="b";
   bool detail=new[]{"_nrm","_spm","normal","specular"}.Any(x=>n.Contains(x));
   cap=detail?512u:readable||bake?1024u:512u;
  }
  int drop=0;while(Math.Max(tex.Width>>drop,tex.Height>>drop)>cap)drop++;
  if(drop==0)continue;
  var levels=new List<byte[]>();uint count=tex.MipCount-(uint)Math.Min(drop,(int)tex.MipCount-1);
  if(tex.MipCount<=drop){
   if(tex.Format.ToString()!="T_BC1_UNorm"&&tex.Format.ToString()!="T_BC3_UNorm")continue;
   File.WriteAllBytes(Path.Combine(dir,i+".basebc"),tex.GetDeswizzledData(0,0));
   string converted=Path.Combine(dir,i+".resampled");if(!File.Exists(converted))continue;
   levels.Add(File.ReadAllBytes(converted));count=1;
  }else for(int l=drop;l<tex.MipCount;l++)levels.Add(tex.GetDeswizzledData(0,l));
  var flat=levels.SelectMany(b=>b).ToArray();var surf=G.CreateGx2Texture(flat,tex.Name,(uint)tex.TileMode,(uint)tex.AAMode,Math.Max(1,tex.Width>>drop),Math.Max(1,tex.Height>>drop),1,(uint)tex.Format,tex.SwizzlePattern,(uint)tex.Dim,count);
  surf.compSel=new[]{(byte)tex.CompSelR,(byte)tex.CompSelG,(byte)tex.CompSelB,(byte)tex.CompSelA};surf.texRegs=G.CreateRegisters(surf);
  // Encode/decode every mip, asserting exact preservation of the author's BC blocks.
  for(int l=0;l<levels.Count;l++)if(!G.Decode(surf,0,l).SequenceEqual(levels[l]))throw new Exception("Texture mip roundtrip failed: "+tex.Name+" "+l);
  File.WriteAllBytes(Path.Combine(dir,i+".data"),surf.data);File.WriteAllBytes(Path.Combine(dir,i+".mips"),surf.mipData);
  result.Add(new{id=i,tex.Name,old_width=tex.Width,old_height=tex.Height,old_bytes=(tex.Data?.Length??0)+(tex.MipData?.Length??0),width=surf.width,height=surf.height,mip_count=surf.numMips,tile_mode=surf.tileMode,swizzle=surf.swizzle,alignment=surf.alignment,pitch=surf.pitch,offsets=surf.mipOffset,registers=surf.texRegs,drop,bytes=surf.data.Length+surf.mipData.Length});
 }
 File.WriteAllText(Path.Combine(dir,"textures.json"),JsonSerializer.Serialize(result,new JsonSerializerOptions{WriteIndented=true}));Console.WriteLine("Prepared "+result.Count+" smaller textures");return;
}
if(mode=="verify"){
 var other=new ResFile(a[3]);if(!f.Models.Keys.SequenceEqual(other.Models.Keys)||!f.Textures.Keys.SequenceEqual(other.Textures.Keys))throw new Exception("Resource keys changed");
 int id=0;foreach(var modelPair in f.Models){var model=modelPair.Value;var dest=other.Models[modelPair.Key];if(!model.Shapes.Keys.SequenceEqual(dest.Shapes.Keys)||!model.Materials.Keys.SequenceEqual(dest.Materials.Keys))throw new Exception("Model changed");
  foreach(var vb in model.VertexBuffers.Select((v,i)=>new{v,i}))for(int j=0;j<vb.v.Buffers.Count;j++)for(int k=0;k<vb.v.Buffers[j].Data.Length;k++)if(!vb.v.Buffers[j].Data[k].SequenceEqual(dest.VertexBuffers[vb.i].Buffers[j].Data[k]))throw new Exception("Vertex data changed");
  foreach(var shapePair in model.Shapes){var s=shapePair.Value;string p=Path.Combine(dir,id+++".newidx");var t=dest.Shapes[shapePair.Key];if(File.Exists(p)){
    var raw=File.ReadAllBytes(p);var expected=Enumerable.Range(0,raw.Length/4).Select(i=>BitConverter.ToUInt32(raw,i*4)-s.Meshes[0].FirstVertex);
    if(!expected.SequenceEqual(t.Meshes[0].GetIndices())||t.Meshes[0].IndexCount!=t.Meshes[0].SubMeshes.Sum(x=>(long)x.Count))throw new Exception("Index roundtrip mismatch");
   }else if(!s.Meshes[0].GetIndices().SequenceEqual(t.Meshes[0].GetIndices()))throw new Exception("Protected shape changed: "+shapePair.Key);
  }
 }
 var texdir=Path.Combine(Path.GetDirectoryName(dir),"textures");
 var textureRows=JsonDocument.Parse(File.ReadAllText(Path.Combine(texdir,"textures.json"))).RootElement.EnumerateArray().ToArray();
 foreach(var pair in f.Textures){var before=(BfresLibrary.WiiU.Texture)pair.Value;var after=(BfresLibrary.WiiU.Texture)other.Textures[pair.Key];var match=textureRows.Where(x=>x.GetProperty("Name").GetString()==before.Name).ToArray();
  if(match.Length==0){if(!(before.Data??Array.Empty<byte>()).SequenceEqual(after.Data??Array.Empty<byte>())||!(before.MipData??Array.Empty<byte>()).SequenceEqual(after.MipData??Array.Empty<byte>()))throw new Exception("Unchanged texture altered");continue;}
  var t=match[0];int drop=t.GetProperty("drop").GetInt32(),ti=t.GetProperty("id").GetInt32();
  if(after.Width!=t.GetProperty("width").GetUInt32()||after.Height!=t.GetProperty("height").GetUInt32()||after.MipCount!=t.GetProperty("mip_count").GetUInt32()||before.Format!=after.Format)throw new Exception("Texture metadata mismatch");
  for(int l=0;l<after.MipCount;l++){
   byte[] expected=before.MipCount<=drop?File.ReadAllBytes(Path.Combine(texdir,ti+".resampled")):before.GetDeswizzledData(0,l+drop);
   if(!expected.SequenceEqual(after.GetDeswizzledData(0,l)))throw new Exception("Texture data mismatch: "+pair.Key);
  }
 }
 Console.WriteLine("BFRES reloaded; vertices, protected meshes and every texture verified");return;
}
throw new Exception("Unknown mode");
}
}
