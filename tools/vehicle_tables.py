"""Append one body and one tire to version-81 parameter tables by cloning donors."""
import struct

PART_AXES = {b'BODY':('body',None), b'TIRE':('tire',None), b'BDDR':(None,'body'),
             b'BDTR':('tire','body'), b'BDWG':(None,'body'), b'TRBD':('body','tire'),
             b'TIRP':('tire',None), b'TIEF':('tire',None), b'BDEF':('body',None)}
PERF_AXES = {b'PTBD':('body',None), b'PTTR':('tire',None)}
COUNTS = {'body':39,'tire':21}
DONORS = {'body':7,'tire':12}

def sections(raw):
    if raw[:4] not in (b'PRTS',b'PERF'): raise ValueError('Unexpected parameter magic')
    if struct.unpack_from('>I',raw,4)[0]!=len(raw): raise ValueError('Parameter size mismatch')
    n,base=struct.unpack_from('>HH',raw,8)
    if base<16+n*4 or base>len(raw): raise ValueError('Invalid section directory')
    offsets=[base+x for x in struct.unpack_from('>%dI'%n,raw,16)]
    if offsets!=sorted(set(offsets)) or offsets[0]!=base: raise ValueError('Invalid section offsets')
    return base,[(raw[a:a+4],raw[a:b]) for a,b in zip(offsets,offsets[1:]+[len(raw)])]

def expand(raw, axes, donors=None):
    donors=donors or {k:[v] for k,v in DONORS.items()}
    base,items=sections(raw);output=bytearray(raw[:base]);offsets=[];seen=set()
    for tag,section in items:
        offsets.append(len(output)-base)
        if tag not in axes:
            output.extend(section);continue
        seen.add(tag);ax,ay=axes[tag];x,y=struct.unpack_from('>HH',section,4)
        if (ax and x!=COUNTS[ax]) or (ay and y!=COUNTS[ay]): raise ValueError('Unexpected dimensions: '+repr(tag))
        payload=section[12:]
        if len(payload)%(x*y): raise ValueError('Unexpected record layout: '+repr(tag))
        stride=len(payload)//(x*y);nx=x+(len(donors[ax]) if ax else 0);ny=y+(len(donors[ay]) if ay else 0)
        head=bytearray(section[:12]);struct.pack_into('>HH',head,4,nx,ny);output.extend(head)
        for row in range(ny):
            old_y=donors[ay][row-y] if row>=y else row
            for col in range(nx):
                old_x=donors[ax][col-x] if col>=x else col
                start=(old_y*x+old_x)*stride
                output.extend(payload[start:start+stride])
    if seen!=set(axes): raise ValueError('Missing expected parameter section')
    struct.pack_into('>I',output,4,len(output))
    struct.pack_into('>%dI'%len(offsets),output,16,*offsets)
    result=bytes(output);verify(raw,result,axes,donors);return result

def verify(original,expanded,axes,donors=None):
    donors=donors or {k:[v] for k,v in DONORS.items()}
    _,old=sections(original);_,new=sections(expanded)
    if [t for t,s in old]!=[t for t,s in new]: raise ValueError('Changed section order')
    for (tag,a),(_,b) in zip(old,new):
        if tag not in axes:
            if a!=b: raise ValueError('Unrelated section changed')
            continue
        x,y=struct.unpack_from('>HH',a,4);nx,ny=struct.unpack_from('>HH',b,4)
        ax,ay=axes[tag];stride=(len(a)-12)//(x*y)
        if (nx,ny)!=(x+(len(donors[ax]) if ax else 0),y+(len(donors[ay]) if ay else 0)) or a[8:12]!=b[8:12]: raise ValueError('Changed metadata')
        for row in range(ny):
            for col in range(nx):
                sy=donors[ay][row-y] if row>=y else row;sx=donors[ax][col-x] if col>=x else col
                if b[12+(row*nx+col)*stride:12+(row*nx+col+1)*stride]!=a[12+(sy*x+sx)*stride:12+(sy*x+sx+1)*stride]:
                    raise ValueError('Original/donor record changed: '+repr(tag))
