"""Keep the two segmented Maple Treeway Wigglers on phase-locked paths."""
import copy,math,struct
import byml_dump

def xyz(p):return tuple(p[k] for k in ('X','Y','Z'))
def f32(x):return struct.unpack('>f',struct.pack('>f',x))[0]

def sample_loop(points,count=256):
    vertices=[xyz(p['Translate']) for p in points]
    edges=[math.dist(a,b) for a,b in zip(vertices,vertices[1:]+vertices[:1])]
    length=sum(edges)
    if length<=0:raise ValueError('Empty Wiggler loop')
    out=[];edge=0;start=0.0
    for i in range(count):
        distance=length*i/count
        while edge<len(edges)-1 and distance>start+edges[edge]:start+=edges[edge];edge+=1
        ratio=(distance-start)/edges[edge] if edges[edge] else 0
        a,b=vertices[edge],vertices[(edge+1)%len(vertices)]
        p=copy.deepcopy(points[0]);p['Translate']={k:f32(a[j]+(b[j]-a[j])*ratio) for j,k in enumerate(('X','Y','Z'))}
        p['ControlPoints']=[copy.deepcopy(p['Translate']),copy.deepcopy(p['Translate'])]
        out.append(p)
    return out,length

def fix(data):
    d=byml_dump.parse(data);report=[]
    for head_path,parts in ((18,(20,21,22,23)),(19,(24,25,26,27))):
        head=next(o for o in d['Obj'] if o['ObjId']==1192 and o['Obj_Path']==head_path)
        body=[next(o for o in d['Obj'] if o['ObjId'] in (9018,9019) and o['Obj_Path']==p) for p in parts]
        points,length=sample_loop(d['Path'][head_path]['PathPt'])
        head_position=xyz(head['Translate'])
        for obj in [head]+body:
            path=obj['Obj_Path'];offset=0.0 if obj is head else math.dist(xyz(obj['Translate']),head_position)
            delay=round(offset/length*len(points));phase=(-delay)%len(points)
            d['Path'][path]['PathPt']=copy.deepcopy(points[phase:]+points[:phase])
            d['Path'][path]['IsClosed']=True
            # All five actors now traverse exactly the same closed point set,
            # at equal speed, starting at distinct phases. No accumulated drift.
            obj['Speed']=head['Speed'];obj['Obj_PathPoint']=0
            obj['Translate']=copy.deepcopy(d['Path'][path]['PathPt'][0]['Translate'])
            report.append({'path':path,'delay_points':delay,'offset_units':offset,'loop_units':length})
    output=byml_dump.build(d)
    if byml_dump.parse(output)!=d:raise ValueError('Wiggler BYAML roundtrip failed')
    return output,report
