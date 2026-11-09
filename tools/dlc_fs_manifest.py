"""Extend an exact-path FS allowlist with locally present base map objects.

These are eligible only during a custom course in dlc_fs.cpp. No AOC layers,
ownership directories or guessed resource names are added.
"""
from pathlib import Path
import argparse,json,re

def extend(header,base):
    names=set(re.findall(r'"([^"\n]+)"',Path(header).read_text()))
    base=Path(base)
    if not (base/'mapobj').is_dir():raise ValueError('Missing base mapobj folder')
    for path in (base/'mapobj').rglob('*'):
        name=path.relative_to(base).as_posix();names.add(name)
        if path.is_dir():names.add(name+'/')
    rows=['static const struct {unsigned int hash;const char *path;} bcp_assets[]={']
    for name in sorted(names):
        h=2166136261
        for value in name.encode():h=((h^value)*16777619)&0xffffffff
        rows.append('{0x%08xu,%s},'%(h,json.dumps(name)))
    return '\n'.join(rows+['};',''])

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--header',required=True);p.add_argument('--base',required=True)
    a=p.parse_args();Path(a.header).write_text(extend(a.header,a.base))
