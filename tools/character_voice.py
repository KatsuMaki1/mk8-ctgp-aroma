"""Stage independent R.O.B. voice labels without replacing Morton's sounds.

The generated archive is experimental and is never installed by this module.
"""
from pathlib import Path
import argparse,hashlib,json,re,struct
import szs,character_assets as assets,character_tables as tables

def u32(data,at):return struct.unpack_from('>I',data,at)[0]
def s32(data,at):return struct.unpack_from('>i',data,at)[0]
def bit(text,index):
    data=text.encode()+bytes(1);byte=index//8
    return ((data[byte]>>(7-index%8))&1) if byte<len(data) else 0

class Archive:
    def __init__(self,path):
        self.path=Path(path)
        with self.path.open('rb') as f:
            self.header=f.read(64)
            if self.header[:8]!=bytes.fromhex('46534152feff0040'):raise ValueError('Expected Wii U BFSAR')
            self.blocks=[];self.payloads={}
            for n in range(struct.unpack_from('>H',self.header,16)[0]):
                kind,pad,off,size=struct.unpack_from('>HHII',self.header,20+n*12)
                self.blocks.append((kind,off,size))
                if kind in (0x2000,0x2001):f.seek(off);self.payloads[kind]=f.read(size)
        if [k for k,o,s in self.blocks]!=[0x2000,0x2001,0x2002]:raise ValueError('Unexpected BFSAR blocks')
        strings=self.payloads[0x2000];table=8+s32(strings,12);n=u32(strings,table)
        self.names=[]
        for i in range(n):
            kind,pad,off,size=struct.unpack_from('>HHiI',strings,table+4+i*12)
            if kind!=0x1f01:raise ValueError('Unknown string reference')
            text=strings[table+off:table+off+size]
            if text[-1:]!=bytes(1):raise ValueError('Unterminated archive name')
            self.names.append(text[:-1].decode())
        if len(set(self.names))!=n:raise ValueError('Duplicate archive name')
        self.tree=8+s32(strings,20);self.root=u32(strings,self.tree);nodes=u32(strings,self.tree+4)
        self.ids={}
        for i in range(nodes):
            leaf,b,l,r,index,item=struct.unpack_from('>HHIIII',strings,self.tree+8+i*20)
            if leaf:self.ids[self.names[index]]=item
        if set(self.ids)!=set(self.names):raise ValueError('Search tree does not cover all strings')
        for name,item in self.ids.items():
            if self.lookup(name)!=item:raise ValueError('Archive tree lookup mismatch')
        self.info=self.payloads[0x2001];self.table=8+s32(self.info,12)
        self.count=u32(self.info,self.table)
        self.records=[self.table+s32(self.info,self.table+8+i*8) for i in range(self.count)]
        if self.records!=sorted(set(self.records)):raise ValueError('Unordered sound records')
        self.sound_end=8+s32(self.info,20)
        self.boundaries=sorted(set(self.records+[8+s32(self.info,a+4) for a in range(8,72,8)]+[len(self.info)]))

    def lookup(self,name):
        block=self.payloads[0x2000];node=self.root
        for _ in range(4096):
            leaf,index,left,right,string,item=struct.unpack_from('>HHIIII',block,self.tree+8+node*20)
            if leaf:return item if self.names[string]==name else None
            node=right if bit(name,index) else left
        raise ValueError('Cyclic archive search tree')

    def sound(self,index):
        start=self.records[index];end=next(x for x in self.boundaries if x>start)
        return self.info[start:end]

def make_strings(names,ids):
    if len(names)!=len(set(names)):raise ValueError('Duplicate output label')
    strings=bytearray();refs=[];table_size=4+len(names)*12
    for name in names:
        data=name.encode()+bytes(1);refs.append((table_size+len(strings),len(data)));strings.extend(data)
    table=struct.pack('>I',len(names))+b''.join(struct.pack('>HHiI',0x1f01,0,off,size) for off,size in refs)+strings
    nodes=[]
    def build(indices,start):
        here=len(nodes);nodes.append(None)
        if len(indices)==1:
            i=indices[0];nodes[here]=(1,0xffff,0xffffffff,0xffffffff,i,ids[names[i]]);return here
        for at in range(start,65536):
            left=[i for i in indices if not bit(names[i],at)]
            if left and len(left)!=len(indices):break
        else:raise ValueError('Indistinguishable sound labels')
        right=[i for i in indices if bit(names[i],at)]
        l=build(left,at+1);r=build(right,at+1);nodes[here]=(0,at,l,r,0xffffffff,0xffffffff)
        return here
    root=build(list(range(len(names))),0)
    block=bytearray(b'STRG'+bytes(4)+struct.pack('>HHiHHi',0x2400,0,16,0x2401,0,0))
    block.extend(table);block.extend(bytes(-len(block)%4));tree=len(block)
    block.extend(struct.pack('>II',root,len(nodes)))
    block.extend(b''.join(struct.pack('>HHIIII',*n) for n in nodes))
    block.extend(bytes(-len(block)%32));struct.pack_into('>I',block,4,len(block));struct.pack_into('>i',block,20,tree-8)
    return bytes(block)

def clone_sounds(archive,mapping,allowed_kinds=(0x2202,)):
    pairs=list(mapping.items()) if isinstance(mapping,dict) else list(mapping)
    names=archive.names+[new for old,new in pairs];ids=dict(archive.ids)
    for n,(old,new) in enumerate(pairs):
        if new in ids:raise ValueError('R.O.B. audio label already exists')
        item=ids[old]
        if item>>24!=1:raise ValueError('Only sound labels can be cloned')
        ids[new]=(item&0xff000000)|(archive.count+n)
    strings=make_strings(names,ids)
    original=archive.info;table=archive.table;end_table=table+4+archive.count*8;delta=len(pairs)*8
    info=bytearray(original[:end_table])+bytearray(delta)+original[end_table:]
    struct.pack_into('>I',info,table,archive.count+len(pairs))
    for i,start in enumerate(archive.records):struct.pack_into('>i',info,table+8+i*8,start+delta-table)
    for at in range(16,72,8):
        old=s32(original,at+4)
        if old not in (-1,0):struct.pack_into('>i',info,at+4,old+delta)
    for n,(old,new) in enumerate(pairs):
        index=archive.ids[old]&0xffffff;record=bytearray(archive.sound(index))
        if struct.unpack_from('>H',record,12)[0] not in allowed_kinds or not u32(record,20)&1:
            raise ValueError('Unexpected sound kind or missing name: '+old)
        struct.pack_into('>I',record,24,len(archive.names)+n)
        start=len(info);info.extend(record)
        struct.pack_into('>HHi',info,table+4+(archive.count+n)*8,0x2200,0,start-table)
    info.extend(bytes(-len(info)%32));struct.pack_into('>I',info,4,len(info))
    for i,old_start in enumerate(archive.records):
        if info[old_start+delta:old_start+delta+len(archive.sound(i))]!=archive.sound(i):
            raise ValueError('An original sound record changed')
    return strings,bytes(info),ids

def rename_bar(data):
    if data[:4]!=b'SARC':raise ValueError('Expected voice SARC')
    files=szs.sarc_read(data);output=[];labels={};old_waves={}
    for name,payload,h in files:
        new_name=name.replace('MOR','ROB') if 'MOR' in name else name
        if name=='_param.bin':
            mutable=bytearray(payload);pool=u32(payload,24);length=u32(payload,28)
            if pool+length!=len(payload):raise ValueError('Unexpected voice string pool')
            at=pool
            while at<len(payload):
                end=payload.find(bytes(1),at)
                if end<0:raise ValueError('Unterminated voice label')
                text=payload[at:end]
                if b'MOR' in text:
                    replacement=text.replace(b'MOR',b'ROB')
                    if len(replacement)!=len(text):raise ValueError('Voice name length changed')
                    mutable[at:end]=replacement
                    if text.startswith((b'pVO_',b'pSE_HORN_')) and not text.endswith(b'.bfwav'):labels[text.decode()]=replacement.decode()
                at=end+1
            payload=bytes(mutable)
        elif name.endswith('.bfwav'):old_waves[new_name]=assets.digest(payload)
        output.append((new_name,payload))
    result=szs.sarc_write(output,{name:32 for name,p in output},struct.unpack_from('>H',data,16)[0])
    check={name:payload for name,payload,h in szs.sarc_read(result)}
    if any(assets.digest(check[n])!=h for n,h in old_waves.items()):raise ValueError('Voice waveform changed')
    return result,labels

def build(source_bfsar,source_content,output):
    source_content,output=Path(source_content),Path(output)
    if output.exists():raise ValueError('Voice output already exists')
    output.mkdir(parents=True);labels={};bars={}
    for folder,old,new in [('driver','SNDG_Morton.bars','SNDG_ROB.bars'),('driver_menu','SNDG_M_Morton.bars','SNDG_M_ROB.bars')]:
        data,mapping=rename_bar((source_content/'audio'/folder/old).read_bytes())
        path=output/'custom/characters/ROB/audio'/folder/new;path.parent.mkdir(parents=True);path.write_bytes(data)
        labels.update(mapping);bars[path.relative_to(output).as_posix()]=assets.digest(data)
    archive=Archive(source_bfsar)
    if not labels or not set(labels)<=set(archive.ids):raise ValueError('Voice labels absent from source BFSAR')
    strings,info,ids=clone_sounds(archive,labels)
    file_entry=archive.blocks[2];blocks=[(0x2000,strings),(0x2001,info)]
    header=bytearray(archive.header);offset=64
    for i,(kind,data) in enumerate(blocks):
        struct.pack_into('>HHII',header,20+i*12,kind,0,offset,len(data));offset+=len(data)
    struct.pack_into('>HHII',header,44,0x2002,0,offset,file_entry[2]);struct.pack_into('>I',header,12,offset+file_entry[2])
    dest=output/'audio/turbo_sound.bfsar';dest.parent.mkdir(parents=True)
    original_file_hash=hashlib.sha256()
    source_hash=hashlib.sha256(archive.header+archive.payloads[0x2000]+archive.payloads[0x2001])
    with dest.open('wb') as target,Path(source_bfsar).open('rb') as src:
        target.write(header);target.write(strings);target.write(info);src.seek(file_entry[1])
        remaining=file_entry[2]
        while remaining:
            chunk=src.read(min(1024*1024,remaining))
            if not chunk:raise ValueError('Source archive truncated')
            original_file_hash.update(chunk);source_hash.update(chunk);target.write(chunk);remaining-=len(chunk)
    check=Archive(dest)
    if any(check.lookup(n)!=i for n,i in ids.items()):raise ValueError('Voice search tree readback differs')
    new_file_hash=hashlib.sha256()
    with dest.open('rb') as f:
        f.seek(check.blocks[2][1])
        while chunk:=f.read(1024*1024):new_file_hash.update(chunk)
    if new_file_hash.digest()!=original_file_hash.digest():raise ValueError('Original sound-file block changed')
    manifest={'status':'staged-only; runtime voice routing required','new_sound_labels':labels,
              'source_bfsar_sha256':source_hash.hexdigest(),
              'old_sound_count':archive.count,'new_sound_count':check.count,'preserved_file_block_sha256':original_file_hash.hexdigest(),
              'bfsar_sha256':assets.digest(dest.read_bytes()),'bars':bars}
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');return manifest

def audio_label(raw,label='ROB'):
    """Give appended driver 37 a unique voice prefix; keep all other labels."""
    base,items=tables.read_sections(raw)
    if raw[:4]!=b'AUDO':raise ValueError('Expected Audio.bin')
    result=bytearray(raw[:base]);offsets=[];seen=False
    for tag,section in items:
        offsets.append(len(result)-base)
        if tag!=b'DRSE':result.extend(section);continue
        if struct.unpack_from('>HH',section,4)!=(38,1):raise ValueError('Independent driver audio axis missing')
        pool=u32(section,8)
        if pool!=164:raise ValueError('Unexpected voice prefix pool')
        previous=u32(section,12+37*4);old=section[pool+previous:section.find(bytes(1),pool+previous)]
        if old==label.encode():return raw
        if old!=b'MOR':raise ValueError('Unexpected donor voice prefix')
        new=bytearray(section);struct.pack_into('>I',new,12+37*4,len(section)-pool)
        new.extend(label.encode()+bytes(1));new.extend(bytes(-len(new)%4))
        if new[:12+37*4]!=section[:12+37*4] or new[12+38*4:len(section)]!=section[12+38*4:]:
            raise ValueError('Original driver voice entry changed')
        result.extend(new);seen=True
    if not seen:raise ValueError('Missing DRSE audio section')
    struct.pack_into('>I',result,4,len(result));struct.pack_into('>%dI'%len(offsets),result,16,*offsets)
    check=tables.read_sections(bytes(result))[1]
    if any(a!=b for (t,a),(_,b) in zip(items,check) if t!=b'DRSE'):raise ValueError('Unrelated audio parameter changed')
    return bytes(result)

def bind_bar_ids(data,archive,label_aliases=None):
    """Bind BARS records to the installed BFSAR, not the replacement donor IDs.

    A v0x54 BARS record stores an explicit low-24-bit sound ID at +0x24.
    Changing its label alone does not change which sound the bank overrides.
    Waveform names and payloads are intentionally retained.
    """
    entries=szs.sarc_read(data);output=[];changes=[];found=False
    for name,payload,h in entries:
        if name!='_param.bin':output.append((name,payload));continue
        found=True;raw=bytearray(payload)
        if raw[:8]!=b'BARS\xfe\xff\x00\x20' or u32(raw,12)!=0x54:
            raise ValueError('Unexpected BARS record format')
        start,length,pool=u32(raw,16),u32(raw,20),u32(raw,24)
        if start!=32 or length%84 or pool!=start+length or pool+u32(raw,28)!=len(raw):
            raise ValueError('Unexpected BARS record directory')
        for at in range(start,pool,84):
            label_at=pool+u32(raw,at)
            if not pool<=label_at<len(raw):raise ValueError('Invalid BARS label offset')
            end=raw.index(0,label_at);old=raw[label_at:end].decode()
            label=(label_aliases or {}).get(old,old)
            if len(label)!=len(old):raise ValueError('BARS alias must preserve string offsets')
            sound=archive.lookup(label)
            if sound is None or sound>>24!=1:raise ValueError('Missing BFSAR sound: '+label)
            before=u32(raw,at+36);after=sound&0xffffff
            raw[label_at:end]=label.encode();struct.pack_into('>I',raw,at+36,after)
            changes.append({'label':label,'old_label':old,'before':before,'after':after})
        output.append((name,bytes(raw)))
    if not found:raise ValueError('Missing BARS parameters')
    result=szs.sarc_write(output,szs.sarc_aligns(data,32),struct.unpack_from('>H',data,16)[0])
    checked={n:p for n,p,h in szs.sarc_read(result)}
    for name,payload,h in entries:
        if name!='_param.bin' and checked[name]!=payload:raise ValueError('Audio sample changed')
    return result,changes

def silent_fwav(raw):
    """Mute a release sample while retaining its valid FWAV format/duration."""
    if raw[:6]!=b'FWAV\xfe\xff':raise ValueError('Expected big endian FWAV')
    info=u32(raw,24);audio=u32(raw,36)
    if raw[info:info+4]!=b'INFO' or raw[audio:audio+4]!=b'DATA':raise ValueError('Missing FWAV blocks')
    result=bytearray(raw);encoding=raw[info+8]
    if encoding not in (0,1,2):raise ValueError('Unsupported FWAV encoding')
    end=audio+u32(raw,audio+4)
    if end>len(raw):raise ValueError('Truncated FWAV data')
    result[audio+8:end]=bytes(end-audio-8)
    if encoding==2:
        table=info+28;count=u32(raw,table)
        for i in range(count):
            channel=table+u32(raw,table+8+i*8);dsp=channel+u32(raw,channel+12)
            if not info<=dsp or dsp+46>info+u32(raw,info+4):raise ValueError('Invalid DSP context')
            result[dsp+32:dsp+46]=bytes(14)
    return bytes(result)

def authored_normal_horn(data):
    """Use the mod's custom special horn for normal presses, not donor samples."""
    entries=szs.sarc_read(data);files={n:p for n,p,h in entries};param=files['_param.bin']
    start,pool,stride=u32(param,16),u32(param,24),u32(param,12)
    if stride!=84:raise ValueError('Unknown BARS record size')
    horns={}
    for at in range(start,pool,stride):
        p=pool+u32(param,at);label=param[p:param.index(bytes(1),p)].decode()
        if label.startswith('pSE_HORN_MORTON_'):
            p=pool+u32(param,at+4);name=param[p:param.index(bytes(1),p)].decode()
            horns[label.rsplit('MORTON_',1)[1]]=(at,name)
    if set(horns)!=set(('ON','OFF','ON_SP')):raise ValueError('Incomplete private horn bank')
    on,on_name=horns['ON'];special,special_name=horns['ON_SP'];off,off_name=horns['OFF']
    if len({on_name,special_name,off_name})!=3:raise ValueError('Horn samples unexpectedly shared')
    special_sample=files[special_name];files[on_name]=special_sample
    files[off_name]=silent_fwav(files[off_name])
    mutable=bytearray(param)
    # Retain the ON sound ID and its label; use the authored special's playback
    # settings with its waveform. No other voice or horn event is modified.
    mutable[on+52:on+84]=param[special+52:special+84];files['_param.bin']=bytes(mutable)
    result=szs.sarc_write(list(files.items()),szs.sarc_aligns(data,32),struct.unpack_from('>H',data,16)[0])
    check={n:p for n,p,h in szs.sarc_read(result)}
    if check[on_name]!=special_sample:raise ValueError('Custom horn sample readback differs')
    for name,payload,h in entries:
        if name not in ('_param.bin',on_name,off_name) and check[name]!=payload:raise ValueError('Unrelated voice changed')
    return result,{'normal_wave':on_name,'authored_wave':special_name,'release_wave':off_name,
                   'authored_sha256':assets.digest(special_sample)}

def reaction_groups(raw,sound_aliases=None):
    """Append the Morton reaction groups under ROB names, retaining weights."""
    if raw[:8]!=b'BSIS\0\0\0\1':raise ValueError('Unknown random sound table')
    count=u32(raw,8);offsets=list(struct.unpack_from('>%dI'%count,raw,12))
    if offsets!=sorted(set(offsets)) or offsets[0]!=12+count*4:raise ValueError('Invalid group directory')
    records=[];clones=[]
    for start,end in zip(offsets,offsets[1:]+[len(raw)]):
        record=raw[start:end];n=u32(record,0)
        pointers=list(struct.unpack_from('>%dI'%(n+1),record,4))
        if any(p<start+8+n*4 or p>=end for p in pointers):raise ValueError('Invalid reaction group pointer')
        name_at=pointers[0];name=raw[name_at:raw.index(bytes(1),name_at)]
        records.append((start,record,n,name))
        if name.endswith(b'_ROB'):raise ValueError('ROB reactions already present')
        if name.endswith(b'_MOR'):clones.append((start,record,n,name))
    if not clones:raise ValueError('Missing Morton reaction groups')
    result=bytearray(12+4*(count+len(clones)));result[:8]=raw[:8]
    struct.pack_into('>I',result,8,count+len(clones));new_offsets=[]
    for index,(start,record,n,name) in enumerate(records+clones):
        new_start=len(result);new_offsets.append(new_start);block=bytearray(record)
        if index>=count:
            block[:]=block.replace(b'_MOR',b'_ROB')
            for old,new in (sound_aliases or {}).items():
                if len(old)!=len(new):raise ValueError('Reaction alias must retain pointer layout')
                block[:]=block.replace(old.encode()+bytes(1),new.encode()+bytes(1))
        for i in range(n+1):struct.pack_into('>I',block,4+i*4,u32(record,4+i*4)+new_start-start)
        result.extend(block)
        if index<count and block[8+n*4:]!=record[8+n*4:]:raise ValueError('Original reaction payload changed')
    struct.pack_into('>%dI'%len(new_offsets),result,12,*new_offsets)
    return bytes(result),len(clones)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('source-bfsar','source-content','output'):p.add_argument('--'+n,required=True,type=Path)
    a=p.parse_args();r=build(a.source_bfsar,a.source_content,a.output)
    print(json.dumps({k:r[k] for k in ('status','old_sound_count','new_sound_count')},indent=2))
