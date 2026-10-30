"""Add two numeric Common.msbt labels without changing any existing message."""
from pathlib import Path
import hashlib,json,struct
from vehicle_catalog import CHOICES
IDS={c['message']:c['name'] for c in CHOICES}

def parse(raw):
    if raw[:10]!=b'MsgStdBn\xfe\xff' or raw[12]!=1:raise ValueError('Expected big-endian UTF-16 MSBT')
    if struct.unpack_from('>I',raw,18)[0]!=len(raw):raise ValueError('MSBT size mismatch')
    count=struct.unpack_from('>H',raw,14)[0];pos=32;out=[]
    for _ in range(count):
        tag=raw[pos:pos+4];size=struct.unpack_from('>I',raw,pos+4)[0]
        out.append((tag,raw[pos:pos+16],raw[pos+16:pos+16+size]));pos=(pos+16+size+15)&~15
    return out

def unpack(raw):
    sections=parse(raw);nl=next(d for t,h,d in sections if t==b'NLI1');tx=next(d for t,h,d in sections if t==b'TXT2')
    pairs=dict(struct.iter_unpack('>II',nl[4:]));n=struct.unpack_from('>I',tx,0)[0]
    offsets=list(struct.unpack_from('>%dI'%n,tx,4))+[len(tx)]
    texts=[tx[a:b] for a,b in zip(offsets,offsets[1:])]
    if struct.unpack_from('>I',nl,0)[0]!=len(pairs) or any(i>=n for i in pairs.values()):raise ValueError('Invalid MSBT label directory')
    return pairs,texts

def append(raw):
    old_pairs,old_texts=unpack(raw);pairs=dict(old_pairs);texts=list(old_texts)
    for id,text in IDS.items():
        encoded=text.encode('utf-16-be')+bytes(2)
        if id in pairs:
            if texts[pairs[id]]!=encoded:raise ValueError('Message ID collision')
        else:pairs[id]=len(texts);texts.append(encoded)
    nli=struct.pack('>I',len(pairs))+b''.join(struct.pack('>II',i,j) for i,j in sorted(pairs.items()))
    pos=4+4*len(texts);offsets=[]
    for t in texts:offsets.append(pos);pos+=len(t)
    txt=struct.pack('>I',len(texts))+struct.pack('>%dI'%len(texts),*offsets)+b''.join(texts)
    output=bytearray(raw[:32])
    for tag,header,data in parse(raw):
        data=nli if tag==b'NLI1' else txt if tag==b'TXT2' else data
        h=bytearray(header);struct.pack_into('>I',h,4,len(data));output.extend(h);output.extend(data)
        output.extend(bytes([0xab])*((-len(output))%16))
    struct.pack_into('>I',output,18,len(output));result=bytes(output)
    check,check_texts=unpack(result)
    if any(check[i]!=j or check_texts[j]!=old_texts[j] for i,j in old_pairs.items()):raise ValueError('Original message changed')
    return result

def prepare(base,content,out):
    base,content,out=Path(base),Path(content),Path(out);manifest={}
    for path in sorted((base/'ui').glob('*/Common.msbt')):
        rel=path.relative_to(base);active=content/rel;source=active if active.exists() else path
        original=source.read_bytes();result=append(original);dest=out/'messages'/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(result)
        manifest[rel.as_posix()]={'input_sha256':hashlib.sha256(original).hexdigest(),'output_sha256':hashlib.sha256(result).hexdigest(),
                                  'existed':active.exists(),'source':str(source)}
    if 'ui/ef/Common.msbt' not in manifest:raise ValueError('Missing French Common.msbt')
    (out/'messages.json').write_text(json.dumps(manifest,indent=2)+'\n');print('Prepared and verified labels in',len(manifest),'languages')
