"""Allocate append-only NEX ghost slots from stable CTGP track/revision IDs.

Never use cup order, donor slot, Python hash(), or a truncated hash as an ID.
The generated JSON and C header are a single client/server contract.
"""
import argparse
import json
import re
from pathlib import Path

BASE, LIMIT = 128, 1024


def build(catalog, previous=None):
    old = previous or {"protocol": 1, "tracks": []}
    if old.get("protocol") != 1:
        raise ValueError("Unknown wire registry protocol")
    rows = [dict(row) for row in old["tracks"]]
    keys, slots = set(), set()
    for row in rows:
        key = (row["id"], row["revision"])
        base = row["base_slot"]
        if key in keys or not isinstance(base, int) or base < BASE or base % 4 or base + 3 >= LIMIT:
            raise ValueError("Invalid or duplicate registry entry")
        if any(n in slots for n in range(base, base + 4)):
            raise ValueError("Overlapping wire slots")
        keys.add(key)
        slots.update(range(base, base + 4))
    seen = set()
    for track in sorted(catalog["tracks"], key=lambda row: (row["id"], row["revision"])):
        key = (track["id"], track["revision"])
        if key in seen or not re.fullmatch(r"[a-z0-9_.-]+", key[0]) or not re.fullmatch(r"[0-9a-f]{64}", key[1]):
            raise ValueError("Invalid/duplicate catalog identity")
        seen.add(key)
        if key in keys:
            continue
        base = max(slots, default=BASE - 1) + 1
        if base + 3 >= LIMIT:
            raise ValueError("NEX persistence namespace exhausted; refusing to reuse IDs")
        rows.append(dict(id=key[0], revision=key[1], base_slot=base,
                         directory=track["directory"], name=track["name"]))
        keys.add(key)
        slots.update(range(base, base + 4))
    return {"protocol": 1, "base": BASE, "limit": LIMIT,
            "category_offset": 16,
            "variants": ["150-native", "200-native", "150-pink-v1", "200-pink-v1"],
            "tracks": sorted(rows, key=lambda row: row["base_slot"])}


def header(registry):
    lines = ["/* Generated append-only wire IDs; retain historical registry entries. */",
             "struct CtgpTTWireTrack {const char *id,*revision;unsigned base;};",
             "static const struct CtgpTTWireTrack ctgp_tt_wire_tracks[]={"]
    for row in registry["tracks"]:
        lines.append(" {" + json.dumps(row["id"]) + "," + json.dumps(row["revision"]) + "," + str(row["base_slot"]) + "},")
    lines += ["};", "#define CTGP_TT_WIRE_COUNT (sizeof(ctgp_tt_wire_tracks)/sizeof(ctgp_tt_wire_tracks[0]))", ""]
    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--header", type=Path, required=True)
    args = parser.parse_args()
    result = build(json.loads(args.catalog.read_text(encoding="utf-8")),
                   json.loads(args.registry.read_text(encoding="utf-8")) if args.registry.exists() else None)
    args.registry.parent.mkdir(parents=True, exist_ok=True)
    args.header.parent.mkdir(parents=True, exist_ok=True)
    args.registry.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    args.header.write_text(header(result), encoding="utf-8")
    print(f"{len(result['tracks'])} track revisions, four independent categories each")
