"""Extend character parameter axes, preserving existing vehicle extensions."""
import struct
from vehicle_tables import sections
from character_catalog import VANILLA_COUNT, CHARACTERS

PART_AXES = {b'DTOM': (True, False, 4), b'DRVR': (True, False, 500),
             b'BDDR': (True, False, 8), b'WDDR': (True, False, 16),
             b'DREF': (True, False, 4)}
PERF_AXES = {b'PTDV': (True, False, 52)}
AUDIO_AXES = {b'DRSE': (True, False, 4)}

def independent_model_identity(raw,model_id=41):
    """Keep donor rig/stats while separating the appended driver's model key."""
    if raw[:4]!=b'PRTS' or not 0<=model_id<256:raise ValueError('Invalid model identity')
    base,items=read_sections(raw);result=bytearray(raw);offset=base;seen=False
    for tag,section in items:
        if tag==b'DTOM':
            if struct.unpack_from('>HH',section,4)!=(38,1):raise ValueError('Expected independent driver axis')
            if model_id in section[12:12+37*4:4] or model_id in section[13:12+37*4:4]:raise ValueError('Model identity already used')
            at=12+37*4
            if section[at:at+4]!=section[12+28*4:12+29*4]:raise ValueError('Unexpected donor identity')
            result[offset+at:offset+at+2]=bytes([model_id,model_id]);seen=True
        offset+=len(section)
    if not seen:raise ValueError('Missing model identity table')
    return bytes(result)

def expand(raw, catalog=CHARACTERS):
    axes = {b'PRTS':PART_AXES,b'PERF':PERF_AXES,b'AUDO':AUDIO_AXES}.get(raw[:4])
    if axes is None:
        raise ValueError('Unknown parameter table')
    if [c['id'] for c in catalog] != list(range(VANILLA_COUNT, VANILLA_COUNT + len(catalog))):
        raise ValueError('Character IDs must append contiguously')
    if any(not 0 <= c['stats_donor'] < VANILLA_COUNT for c in catalog):
        raise ValueError('Invalid character donor')
    base, items = read_sections(raw)
    result = bytearray(raw[:base]); offsets = []; seen = set()
    for tag, old in items:
        offsets.append(len(result) - base)
        if tag not in axes:
            result.extend(old)
            continue
        seen.add(tag)
        ax, ay, stride = axes[tag]
        x, y = struct.unpack_from('>HH', old, 4)
        if (ax and x != VANILLA_COUNT) or (ay and y != VANILLA_COUNT):
            raise ValueError('Unexpected character dimension: ' + repr(tag))
        end = 12 + x*y*stride
        if end > len(old):
            raise ValueError('Truncated records: ' + repr(tag))
        tail = old[end:]
        if tag in (b'DRVR',b'DRSE'):
            if struct.unpack_from('>I', old, 8)[0] != end:
                raise ValueError('Unknown DRVR string pool offset')
            for i in range(x):
                off = struct.unpack_from('>I', old, 12+i*stride+(16 if tag==b'DRVR' else 0))[0]
                if off >= len(tail) or bytes(1) not in tail[off:]:
                    raise ValueError('Invalid DRVR string reference')
        elif tail:
            raise ValueError('Unexpected parameter suffix: ' + repr(tag))
        nx = x + (len(catalog) if ax else 0)
        ny = y + (len(catalog) if ay else 0)
        header = bytearray(old[:12])
        struct.pack_into('>HH', header, 4, nx, ny)
        if tag in (b'DRVR',b'DRSE'):
            struct.pack_into('>I', header, 8, 12+nx*ny*stride)
        result.extend(header)
        for row in range(ny):
            sy = row if row < y else catalog[row-y]['stats_donor']
            for col in range(nx):
                sx = col if col < x else catalog[col-x]['stats_donor']
                start = 12 + (sy*x+sx)*stride
                result.extend(old[start:start+stride])
        result.extend(tail)
    if seen != set(axes):
        raise ValueError('Missing character tables')
    struct.pack_into('>I', result, 4, len(result))
    struct.pack_into('>%dI' % len(offsets), result, 16, *offsets)
    output = bytes(result)
    verify(raw, output, catalog)
    return output

def verify(original, expanded, catalog=CHARACTERS):
    axes = {b'PRTS':PART_AXES,b'PERF':PERF_AXES,b'AUDO':AUDIO_AXES}[original[:4]]
    before = read_sections(original)[1]; after = read_sections(expanded)[1]
    if [t for t, _ in before] != [t for t, _ in after]:
        raise ValueError('Section directory changed')
    for (tag, a), (_, b) in zip(before, after):
        if tag not in axes:
            if a != b: raise ValueError('Unrelated section changed')
            continue
        ax, ay, stride = axes[tag]
        x, y = struct.unpack_from('>HH', a, 4)
        nx, ny = struct.unpack_from('>HH', b, 4)
        if (nx, ny) != (x+(len(catalog) if ax else 0), y+(len(catalog) if ay else 0)):
            raise ValueError('Invalid output dimensions')
        for row in range(ny):
            sy = row if row < y else catalog[row-y]['stats_donor']
            for col in range(nx):
                sx = col if col < x else catalog[col-x]['stats_donor']
                if b[12+(row*nx+col)*stride:12+(row*nx+col+1)*stride] != a[12+(sy*x+sx)*stride:12+(sy*x+sx+1)*stride]:
                    raise ValueError('Existing/donor record differs: ' + repr(tag))
        if a[12+x*y*stride:] != b[12+nx*ny*stride:]:
            raise ValueError('String pool changed')
        if tag in (b'DRVR',b'DRSE'):
            if struct.unpack_from('>I', b, 8)[0] != 12+nx*ny*stride:
                raise ValueError('String pool offset differs')
        elif a[8:12] != b[8:12]:
            raise ValueError('Unrelated section metadata changed')

def read_sections(raw):
    if raw[:4]!=b'AUDO':return sections(raw)
    # The shared section directory has the same layout for audio parameters.
    # Reuse its strict bounds/order validation without relaxing other tools.
    return sections(b'PRTS'+raw[4:])
