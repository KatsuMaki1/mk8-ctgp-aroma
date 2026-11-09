"""Build the Cemu overlay ZIP (merge into <Cemu>/mlc01) from the isolated test update directory.

  python build_cemu_zip.py --update <.../mlc/usr/title/0005000e/1010ed00> --files candidates.json --out OUT.zip --readme README.txt [--extra name=path ...]

Only the CTGP files (candidates.json = relative paths under content/), code/Turbo.rpx and code/cos.xml are packed.
Never packed: account.dat, MiiData, local databases, internal keys, backups (the script refuses names that look private).
"""
import argparse, json, os, sys, zipfile

FORBIDDEN = ('account.dat', 'persisid', '.db', '.sqlite', 'secret', 'kerberos', 'token', '_backups', '.bak', 'before_ctgp', '.env')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--update', required=True); ap.add_argument('--files', required=True)
    ap.add_argument('--out', required=True); ap.add_argument('--readme', required=True)
    ap.add_argument('--extra', action='append', default=[], help='zip_name=local_path (placed at the zip root)')
    a = ap.parse_args()
    rel = json.load(open(a.files, encoding='utf-8'))
    prefix = 'mlc01/usr/title/0005000e/1010ed00/'
    entries = [(prefix + 'code/Turbo.rpx', os.path.join(a.update, 'code', 'Turbo.rpx')),
               (prefix + 'code/cos.xml', os.path.join(a.update, 'code', 'cos.xml'))]
    entries += [(prefix + 'content/' + r, os.path.join(a.update, 'content', r)) for r in rel]
    for name, path in entries:
        low = name.lower()
        if any(f in low for f in FORBIDDEN):
            sys.exit('refusing private/backup looking file: ' + name)
        if not os.path.isfile(path):
            sys.exit('missing: ' + path)
    with zipfile.ZipFile(a.out, 'w', zipfile.ZIP_DEFLATED, compresslevel=1, allowZip64=True) as z:
        z.write(a.readme, 'LISEZ-MOI.txt')
        for spec in a.extra:
            n, p = spec.split('=', 1); z.write(p, n)
        for i, (name, path) in enumerate(entries):
            z.write(path, name)
            if i % 200 == 0: print(i, '/', len(entries), flush=True)
    print('done', a.out, os.path.getsize(a.out) // 2**20, 'MB')


if __name__ == '__main__':
    main()
