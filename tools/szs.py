"""Yaz0 + SARC helpers (read, and write with literal-only Yaz0 so no compressor is needed)."""
import struct


def yaz0_decode(d):
    assert d[:4] == b'Yaz0'
    size, = struct.unpack('>I', d[4:8]); out = bytearray(); p = 16
    while len(out) < size:
        code = d[p]; p += 1
        for b in range(8):
            if len(out) >= size: break
            if code & (0x80 >> b): out.append(d[p]); p += 1
            else:
                b1, b2 = d[p], d[p + 1]; p += 2; dist = ((b1 & 0xF) << 8 | b2) + 1; n = b1 >> 4
                if n == 0: n = d[p] + 0x12; p += 1
                else: n += 2
                for _ in range(n): out.append(out[-dist])
    return bytes(out)


def yaz0_store(data):
    """valid Yaz0 stream made only of literals (8 literals per code byte): larger, but always correct"""
    out = bytearray(b'Yaz0' + struct.pack('>I', len(data)) + b'\0' * 8)
    for i in range(0, len(data), 8):
        chunk = data[i:i + 8]; out.append((0xFF << (8 - len(chunk))) & 0xFF if len(chunk) < 8 else 0xFF); out += chunk
    return bytes(out)


def sarc_read(s):
    """-> (list of (name, bytes) in archive order, header info)"""
    data_off, = struct.unpack('>I', s[0xC:0x10]); sfat = 0x14
    cnt, = struct.unpack('>H', s[sfat + 6:sfat + 8]); sfnt = sfat + 12 + cnt * 16; names = s[sfnt + 8:data_off]
    files = []
    for i in range(cnt):
        h, attr, a, b = struct.unpack('>IIII', s[sfat + 12 + i * 16:sfat + 12 + (i + 1) * 16])
        no = (attr & 0xFFFFFF) * 4
        files.append((names[no:names.index(b'\0', no)].decode(), s[data_off + a:data_off + b], h))
    return files


def sarc_hash(name, mult=0x65):
    h = 0
    for c in name.encode():
        h = (h * mult + c) & 0xFFFFFFFF
    return h


def sarc_info(s):
    """(list of (name, data, hash, abs_start), data_offset, version)"""
    data_off, = struct.unpack('>I', s[0xC:0x10]); ver, = struct.unpack('>H', s[0x10:0x12])
    out = []
    sfat = 0x14; cnt, = struct.unpack('>H', s[sfat + 6:sfat + 8]); sfnt = sfat + 12 + cnt * 16; names = s[sfnt + 8:data_off]
    for i in range(cnt):
        h, attr, a, b = struct.unpack('>IIII', s[sfat + 12 + i * 16:sfat + 12 + (i + 1) * 16]); no = (attr & 0xFFFFFF) * 4
        out.append((names[no:names.index(b'\0', no)].decode(), s[data_off + a:data_off + b], h, data_off + a))
    return out, data_off, ver


def sarc_write(files, aligns=None, version=0x100):
    """files: list of (name, bytes). Nodes sorted by name hash (required by the game). aligns: {name: alignment} (default 4)."""
    aligns = aligns or {}
    nodes = sorted(((sarc_hash(n), n, d) for n, d in files), key=lambda t: t[0])
    cnt = len(nodes)
    names = bytearray(); noff = []
    for _, n, _ in nodes:
        noff.append(len(names)); names += n.encode() + b'\0'
        while len(names) % 4: names += b'\0'
    data_off_min = 0x14 + 12 + cnt * 16 + 8 + len(names)
    # data layout: the archive's data section starts at an offset aligned to the largest file alignment
    amax = max([aligns.get(n, 4) for _, n, _ in nodes] + [4])
    data_off = (data_off_min + amax - 1) // amax * amax
    blob = bytearray(); recs = []
    for h, n, d in nodes:
        a = aligns.get(n, 4)
        while (data_off + len(blob)) % a: blob += b'\0'
        recs.append((len(blob), len(blob) + len(d))); blob += d
    out = bytearray(b'SARC' + struct.pack('>HHIIHH', 0x14, 0xFEFF, data_off + len(blob), data_off, version, 0))
    out += b'SFAT' + struct.pack('>HHI', 0xC, cnt, 0x65)
    for (h, n, d), no, (a, b) in zip(nodes, noff, recs): out += struct.pack('>IIII', h, 0x01000000 | (no // 4), a, b)
    out += b'SFNT' + struct.pack('>HH', 8, 0) + names
    out += b'\0' * (data_off - len(out)) + blob
    return bytes(out)


def sarc_aligns(s, cap=0x2000):
    """largest power-of-two alignment (<= cap) of every file's absolute start offset, to reproduce the layout when rewriting"""
    out = {}
    for n, d, h, start in sarc_info(s)[0]:
        a = 4
        while a < cap and start % (a * 2) == 0: a *= 2
        out[n] = a
    return out
