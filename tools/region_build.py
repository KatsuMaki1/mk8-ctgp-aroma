"""Build per-language Region.msbt: the modder's layout (country + sub-region messages) with each language's own texts.

Texts: ids already in the game's Region.msbt keep that language's text; new country names come from CLDR in the
language; new sub-region names are copied from the supplied (French) file.
"""
import re, struct, sys
from pathlib import Path
import msbt_edit as m

ISO_EXTRA = {219: 'MA', 151: 'TL', 152: 'ID', 168: 'AE', 169: 'IN', 170: 'EG', 171: 'OM', 172: 'QA', 173: 'KW', 174: 'SA', 175: 'SY', 176: 'BH', 177: 'JO', 184: 'SM', 185: 'VA', 186: 'BM'}
# Country ids that the supplied file does not name: their name message is appended (id = 50000 + country*100 + 1).
EXTRA_NEW = {219: 'MA'}
LANG = {'ee': 'en', 'ef': 'fr', 'ed': 'nl', 'eg': 'de', 'es': 'es', 'ei': 'it', 'ep': 'pt', 'er': 'ru'}

def iso_table(country_txt):
    table = {}
    for i, line in enumerate(Path(country_txt).read_text().splitlines()):
        mm = re.fullmatch(r'"([A-Z]{2})",?', line.strip())
        if mm: table[i] = mm.group(1)
    table.update(ISO_EXTRA); return table

def rebuild(supplied_raw, base_raw, language, iso, keep_supplied=False):
    from babel import Locale
    e, secs = m.parse(supplied_raw); smsgs, sids, enc = m.messages(e, secs)
    be, bsecs = m.parse(base_raw); bmsgs, bids, _ = m.messages(be, bsecs)
    names = Locale(language).territories; out = []
    for ident, index in sorted(sids.items(), key=lambda kv: kv[1]):
        if keep_supplied: text = smsgs[index]
        elif ident in bids: text = bmsgs[bids[ident]]
        elif ident % 100 == 1 and (ident - 50000) // 100 in iso and iso[(ident - 50000) // 100] in names:
            text = names[iso[(ident - 50000) // 100]] + '\x00'
        else: text = smsgs[index]
        out.append((index, text))
    out.sort(); texts = [t for _, t in out]; assert len(texts) == len(smsgs)
    all_ids = dict(sids)
    for cid, code in EXTRA_NEW.items():
        ident = 50000 + cid * 100 + 1
        if ident in all_ids: continue
        all_ids[ident] = len(texts); texts.append(names[code] + chr(0))
    n = len(texts); strings = [t.encode(enc) for t in texts]; offs = []; pos = 4 + 4 * n
    for s in strings: offs.append(pos); pos += len(s)
    new_txt = struct.pack(e + 'I', n) + struct.pack(e + '%dI' % n, *offs) + b''.join(strings)
    result = bytearray(supplied_raw[:0x20])
    for tag, data, hdr in secs:
        if tag == b'TXT2': data = new_txt
        if tag == b'NLI1': data = struct.pack(e + 'I', len(all_ids)) + b''.join(struct.pack(e + 'II', k, v) for k, v in sorted(all_ids.items()))
        result += tag + struct.pack(e + 'I', len(data)) + hdr[4:] + data + b'\xab' * (-len(data) % 16)
    struct.pack_into(e + 'I', result, 0x12, len(result))
    e2, s2 = m.parse(bytes(result)); m2, i2, _ = m.messages(e2, s2); assert i2 == all_ids and len(m2) == n
    return bytes(result)

if __name__ == '__main__':
    supplied = Path(sys.argv[1]).read_bytes(); base_dir = Path(sys.argv[2]); out_dir = Path(sys.argv[3]); iso = iso_table(sys.argv[4])
    for d, lang in LANG.items():
        raw = rebuild(supplied, (base_dir / d / 'Region.msbt').read_bytes(), lang, iso, keep_supplied=(d == 'ef'))
        (out_dir / d).mkdir(parents=True, exist_ok=True); (out_dir / d / 'Region.msbt').write_bytes(raw)
        _, s = m.parse(raw); msgs, ids, _ = m.messages(*m.parse(raw)[:1], m.parse(raw)[1])
        print(d, lang, len(raw), 'syria:', ascii(msgs[ids[67501]].strip('\x00')), 'china:', ascii(msgs[ids[66001]].strip('\x00')))
