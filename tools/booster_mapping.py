"""Resolve Booster models without assuming internal IDs follow cup order."""

# Canonical menu position -> internal Cnsw ID. Internal production order differs
# from release/cup order from wave 3 onward. Console race observations confirm
# these permutations; the source previews/minimaps identify the remaining ports.
COURSE_CODES = (
    11,12,13,14,15,16,17,18,21,22,23,24,25,26,27,28,
    31,33,34,62,35,32,37,38,41,47,42,44,55,43,36,45,
    65,46,63,58,48,53,52,61,54,56,66,64,51,67,57,68,
)

def model_sources(rows):
    result={}
    for row in rows:
        codes={n for res in row['resources'] for n in res['models'] if n.startswith('Cnsw_')}
        if len(codes)!=1:raise ValueError('Ambiguous Booster model: '+row['key'])
        code=int(codes.pop().split('_')[1]);wave,slot=divmod(code,10)
        if not 1<=wave<=6 or not 1<=slot<=8:raise ValueError('Invalid Booster model ID')
        number=COURSE_CODES.index(code)+1
        if number in result:raise ValueError('Duplicate Booster model ID')
        result[number]=row['key']
    if set(result)!=set(range(1,49)):raise ValueError('Incomplete Booster model audit')
    return result
