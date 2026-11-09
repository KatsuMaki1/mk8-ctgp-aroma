"""Consolidate the twelve Boltthunder cups without changing track/icon IDs."""
import copy
import cup0

def consolidate(payload):
    original=cup0.parse(payload)
    cups=copy.deepcopy(original)
    bolt=[c for c in cups if any(t.dir.startswith('Gu_Bolt') for t in c.tracks)]
    if len(bolt)!=12:raise ValueError('Expected exactly twelve Boltthunder cups')
    bolt.sort(key=lambda c:c.cup_id)
    for i,c in enumerate(bolt):
        if c.cup_id!=36+i or [t.dir for t in c.tracks]!=['Gu_Bolt%02d'%(i*4+s) for s in range(4)]:
            raise ValueError('Unexpected Boltthunder cup/track ordering')
        c.type=3;c.icon=i
    if len({(c.type,c.icon) for c in cups})!=len(cups):raise ValueError('Page position collision')
    result=cup0.build(cups)
    checked=cup0.parse(result)
    for before,after in zip(original,checked):
        if not before.tracks[0].dir.startswith('Gu_Bolt'):
            if before!=after:raise ValueError('An unrelated cup changed')
        elif before.cup_id!=after.cup_id or before.name!=after.name or before.tracks!=after.tracks:
            raise ValueError('Boltthunder track/icon identity changed')
    return result
