"""Point the CTGP build at its own NEX game server id (0x1010EB01 instead of the stock 0x1010EB00).

The game stores its NEX game server id with `lis rX,0x1011 ; addi rX,rX,-0x1500` at two places (EUR v81). Changing the addi immediate
to 0xEB01 makes the nex_token request ask for game_server_id=1010EB01, which Protarium routes to the CTGP-only NEX server, so CTGP
clients never share rooms with vanilla players (no change to the matchmaking messages needed).
Usage: python ctgp_server_id.py IN.rpx OUT.rpx
"""
import struct, sys, json, hashlib
from pathlib import Path
import rpxlib, costume_patch as patch

SITES = {0x23d5628: (0x38e7eb00, 0x38e7eb01), 0x23e8c58: (0x38a5eb00, 0x38a5eb01)}


def apply(source, output):
    raw, ss = rpxlib.load(source)
    for addr, (old, new) in SITES.items():
        if rpxlib.word_at(ss, addr) != old:
            raise ValueError('Unexpected word at %x (already patched or other game version)' % addr)
        s = next(s for s in ss if s['addr'] <= addr < s['addr'] + len(s['data']))
        b = bytearray(s['data']); struct.pack_into('>I', b, addr - s['addr'], new); s['data'] = bytes(b)
    result = patch.repack(raw, ss)
    Path(output).write_bytes(result)
    _, check = rpxlib.load(output)
    for addr, (old, new) in SITES.items():
        assert rpxlib.word_at(check, addr) == new
    src_meta = Path(str(source) + '.json')
    meta = json.loads(src_meta.read_text()) if src_meta.exists() else {}
    meta['output_sha256'] = hashlib.sha256(result).hexdigest()
    meta['note'] = (meta.get('note', '') + ' + CTGP game server id 1010EB01').strip()
    Path(str(output) + '.json').write_text(json.dumps(meta, indent=2))
    return output


if __name__ == '__main__':
    apply(sys.argv[1], sys.argv[2])
    print('patched', sys.argv[2])
