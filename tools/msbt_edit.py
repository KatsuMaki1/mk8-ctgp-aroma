"""Replace text inside numbered MSBT messages (variable length) and rebuild TXT2/sizes.

All other messages, section order, labels and padding stay byte-identical; the result is re-parsed and checked.
"""
import argparse, struct
from pathlib import Path

def parse(raw):
    if raw[:8] != b'MsgStdBn': raise ValueError('Not an MSBT')
    e = '>' if raw[8:10] == b'\xfe\xff' else '<'
    pos, secs = 0x20, []
    while pos < len(raw):
        tag = raw[pos:pos+4]; size = struct.unpack(e+'I', raw[pos+4:pos+8])[0]
        secs.append([tag, raw[pos+16:pos+16+size], raw[pos+4:pos+16]]); pos += 16 + (size + 15) // 16 * 16
    return e, secs

def messages(e, secs):
    d = dict((t, x) for t, x, _ in secs); txt = d[b'TXT2']; n = struct.unpack(e+'I', txt[:4])[0]
    offs = struct.unpack(e+'%dI' % n, txt[4:4+4*n]) + (len(txt),); enc = 'utf-16-be' if e == '>' else 'utf-16-le'
    ids = {}
    nli = d.get(b'NLI1')
    if nli:
        c = struct.unpack(e+'I', nli[:4])[0]
        for i in range(c):
            ident, index = struct.unpack(e+'II', nli[4+i*8:12+i*8]); ids[ident] = index
    return [txt[offs[i]:offs[i+1]].decode(enc) for i in range(n)], ids, enc

def replace(raw, edits):
    """edits: {numeric id: (old, new)}"""
    e, secs = parse(raw); msgs, ids, enc = messages(e, secs); out = list(msgs); changed = {}
    for ident, (old, new) in edits.items():
        i = ids[ident]
        if old not in out[i]: raise ValueError('Message %d does not contain %r' % (ident, old))
        out[i] = out[i].replace(old, new); changed[ident] = out[i]
    strings = [m.encode(enc) for m in out]; n = len(strings); start = 4 + 4*n; offs = []; pos = start
    for s in strings: offs.append(pos); pos += len(s)
    new_txt = struct.pack(e+'I', n) + struct.pack(e+'%dI' % n, *offs) + b''.join(strings)
    result = bytearray(raw[:0x20])
    for tag, data, hdr in secs:
        if tag == b'TXT2': data = new_txt
        size_hdr = struct.pack(e+'I', len(data)) + hdr[4:]
        result += tag + size_hdr + data
        result += b'\xab' * (-len(data) % 16)
    struct.pack_into(e+'I', result, 0x12, len(result))
    # verify
    e2, s2 = parse(bytes(result)); m2, i2, _ = messages(e2, s2)
    assert i2 == ids and len(m2) == len(msgs)
    for k in range(len(msgs)):
        assert m2[k] == out[k]
    for ident in ids:
        if ident not in edits: assert m2[ids[ident]] == msgs[ids[ident]]
    for (t1, d1, _), (t2, d2, _) in zip(secs, s2):
        assert t1 == t2 and (t1 == b'TXT2' or d1 == d2)
    return bytes(result), changed

if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('src'); p.add_argument('dst'); p.add_argument('--ids', type=int, nargs='+', required=True)
    p.add_argument('--old', required=True); p.add_argument('--new', required=True); a = p.parse_args()
    out, ch = replace(Path(a.src).read_bytes(), {i: (a.old, a.new) for i in a.ids}); Path(a.dst).write_bytes(out); print(ch)
