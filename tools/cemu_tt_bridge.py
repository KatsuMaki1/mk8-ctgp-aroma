"""Local Cemu development adapter. Reads only the owned debugger process.

This is NOT NEX authentication: --dev-pid identifies a local test player only.
It never edits guest RAM or production network settings. New runs stay pending.
"""
import argparse
import base64
import ctypes
import hashlib
import json
from pathlib import Path
import re
import struct
import time
import urllib.parse
import urllib.request

from staff_ghosts import payload, RULES

NAME = re.compile(r'gs(?:[0-9a-fA-F]{98}|[0-9a-fA-F]{100}|[0-9a-fA-F]{112})\.dat')


def ghost_time(name):
    if not NAME.fullmatch(name):
        raise ValueError('Not an original personal ghost filename')
    minutes, seconds, millis = int(name[18], 16), int(name[19:21], 16), int(name[21:24], 16)
    if seconds >= 60 or millis >= 1000:
        raise ValueError('Invalid native ghost time')
    return (minutes * 60 + seconds) * 1000 + millis


def downloaded_name(source, slot):
    if not re.fullmatch(r'(gs|dg|sg)(?:[0-9a-fA-F]{98}|[0-9a-fA-F]{100}|[0-9a-fA-F]{112})\.dat', source) or not 0 <= slot < 16:
        raise ValueError('Unsafe native ghost filename')
    stem = source[:-4]
    if len(stem) == 100:
        stem += '00'  # Native downloaded ghosts require the longer padding.
    return 'dg' + f'{slot:02x}' + stem[4:] + '.dat'


def request(url, body=None, key=None, binary=False):
    data = json.dumps(body).encode() if body is not None else None
    headers = {'Content-Type': 'application/json'}
    if key:
        headers['Authorization'] = 'Bearer ' + key
    with urllib.request.urlopen(urllib.request.Request(url, data, headers), timeout=5) as response:
        raw = response.read(3 << 20)
    return raw if binary else json.loads(raw)


def board_snapshot(board, leaderboard, manifest, sequence, mii=None):
    data = bytearray(4352)
    rows = leaderboard[:16]
    struct.pack_into('>6I', data, 0, 0x5454424c, 1, board['cc'], int(board['rules'] == RULES[1]), len(rows), sequence & 0xffffffff)
    identity, revision = board['track'].encode('ascii'), board['revision'].encode('ascii')
    if len(identity) >= 96 or len(revision) != 64:
        raise ValueError('Unsafe board identity')
    data[32:32+len(identity)] = identity
    data[128:192] = revision
    filenames = {row['id']: row['filename'] for row in manifest}
    for index, row in enumerate(rows):
        if any(row[key] != board[key] for key in board):
            raise ValueError('Leaderboard category mismatch')
        offset = 256 + index * 256
        struct.pack_into('>4I', data, offset, row['pid'], row['time_ms'], index + 1, int(row['id'] in filenames))
        name = f"Player {row['pid']}"
        filename = filenames.get(row['id'])
        if filename:
            downloaded_name(filename, 0)  # Strict syntax before decoding Mii name.
            name = bytes.fromhex(filename[54:94]).decode('utf-16-be', errors='replace').split('\0', 1)[0] or name
        encoded = name.encode('utf-16-be')[:40]
        data[offset+32:offset+32+len(encoded)] = encoded
        if mii:  # 96-byte Mii store data of the local development account, shown as the row icon
            if len(mii) != 0x60: raise ValueError('Mii data must be 96 bytes')
            data[offset+80:offset+80+0x60] = mii
    checksum = 2166136261
    for index, value in enumerate(data):
        if not 24 <= index < 28:
            checksum = ((checksum ^ value) * 16777619) & 0xffffffff
    struct.pack_into('>I', data, 24, checksum)
    return bytes(data)


class Guest:
    def __init__(self, pid, base):
        self.kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        self.kernel.OpenProcess.argtypes = [ctypes.c_uint, ctypes.c_bool, ctypes.c_uint]
        self.kernel.OpenProcess.restype = ctypes.c_void_p
        self.kernel.ReadProcessMemory.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
        self.kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint]
        self.kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        self.handle = self.kernel.OpenProcess(0x10 | 0x1000 | 0x100000, False, pid)
        if not self.handle:
            raise ctypes.WinError(ctypes.get_last_error())
        self.base = base

    def read(self, address, count):
        out = ctypes.create_string_buffer(count)
        got = ctypes.c_size_t()
        if not self.kernel.ReadProcessMemory(self.handle, self.base + address, out, count, ctypes.byref(got)) or got.value != count:
            raise OSError(f'Guest read failed: {address:x}')
        return out.raw

    def word(self, address):
        return struct.unpack('>I', self.read(address, 4))[0]

    def string(self, address, count):
        return self.read(address, count).split(b'\0', 1)[0].decode('ascii')

    def alive(self):
        return self.kernel.WaitForSingleObject(self.handle, 0) == 258

    def close(self):
        self.kernel.CloseHandle(self.handle)


def sync_board(url, board, account, category_path, key, dev_pid, pack_hash, uploaded):
    query = urllib.parse.urlencode(board)
    leaderboard = request(url + '/v1/leaderboard?' + query)
    staff = request(url + '/v1/staff?' + query)
    manifest = request(url + '/v1/ghost-manifest?' + query)
    destination = account / category_path
    destination.mkdir(parents=True, exist_ok=True)
    downloaded = 0
    for slot, row in enumerate(manifest[:16]):
        if any(row[k] != board[k] for k in board):
            raise ValueError('Server returned another category')
        raw = request(url + f"/v1/ghost/{int(row['id'])}", binary=True)
        if hashlib.sha256(raw).hexdigest() != row['ghost_hash']:
            raise ValueError('Ghost download checksum mismatch')
        payload(raw)  # Validate the native CTG0 container, never rewrite inputs.
        name = downloaded_name(row['filename'], slot)
        target = destination / name
        if target.exists() and target.read_bytes() != raw:
            # Do not overwrite recordings the adapter did not create.
            continue
        if not target.exists():
            temporary = target.with_suffix('.download.tmp')
            with temporary.open('xb') as stream:
                stream.write(raw)
            temporary.rename(target)
        downloaded += 1
    submitted = []
    if key:
        for path in destination.glob('gs*.dat'):
            raw = path.read_bytes()
            payload(raw)
            marker = (str(path), hashlib.sha256(raw).hexdigest())
            if marker in uploaded:
                continue
            run = request(url + '/internal/v1/runs', dict(pid=dev_pid, board=board, time_ms=ghost_time(path.name), ghost=base64.b64encode(raw).decode(), pack_hash=pack_hash), key)
            request(url + '/internal/v1/native-ghost-name', dict(id=run['id'], filename=path.name), key)
            uploaded.add(marker)
            submitted.append(run['id'])
    return dict(leaderboard=leaderboard, staff=staff, downloaded=downloaded, submitted_pending=submitted, native_manifest=manifest)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('session', 'artifact', 'log', 'catalog', 'account', 'status'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--url', default='http://127.0.0.1:3090')
    p.add_argument('--key-file', type=Path)
    p.add_argument('--sd', type=Path)
    p.add_argument('--dev-pid', type=int, default=1)
    p.add_argument('--act-account', type=Path, help='private account.dat of the development account (its MiiData becomes the row icon)')
    args = p.parse_args()
    parsed = urllib.parse.urlsplit(args.url)
    if parsed.scheme != 'http' or parsed.hostname != '127.0.0.1' or parsed.username or parsed.password:
        raise ValueError('Local adapter requires http://127.0.0.1')
    catalog = json.loads(args.catalog.read_text())
    remote = request(args.url + '/v1/catalog')
    sort_tracks = lambda c: sorted(c['tracks'], key=lambda t: t['id'])
    if catalog['protocol'] != remote['catalog']['protocol'] or sort_tracks(catalog) != sort_tracks(remote['catalog']):
        raise ValueError('Local and server catalogs differ')
    artifact = json.loads(Path(str(args.artifact) + '.json').read_text())
    if hashlib.sha256(args.artifact.read_bytes()).hexdigest() != artifact['output_sha256']:
        raise ValueError('Build hash differs from symbol map')
    symbols = artifact['symbols']
    tracks = {t['id']: t for t in catalog['tracks']}
    session = json.loads(args.session.read_text())
    match = re.search(r'Init Wii U memory space \(base: 0x([0-9a-fA-F]+)', args.log.read_text(errors='replace'))
    if not match or args.log.stat().st_mtime < session['started']:
        raise ValueError('Current Cemu log is not ready')
    guest = Guest(session['pid'], int(match[1], 16))
    key = args.key_file.read_text().strip() if args.key_file else None
    mii = None
    if args.act_account:
        for line in args.act_account.read_text(errors='replace').splitlines():
            if line.startswith('MiiData='): mii = bytes.fromhex(line.split('=', 1)[1].strip())
        if mii is not None and len(mii) != 0x60: raise ValueError('Unexpected MiiData size')
    last = None
    uploaded = set()
    last_sync = 0
    try:
        while guest.alive():
            try:
                if not guest.word(symbols['tt_selected_valid']) or not guest.word(0x1030c010):
                    time.sleep(.25)
                    continue
                # This configured isolated account is the sandbox's slot 1.
                # Never export another selected account under the local test PID.
                slot = guest.word(symbols['tt_scope_slot'])
                if slot != 1:
                    time.sleep(.25)
                    continue
                generation = guest.word(symbols['tt_selected_count'])
                identity = guest.string(symbols['tt_selected_identity'], 96)
                revision = guest.string(symbols['tt_selected_revision'], 65)
                path = guest.string(symbols['tt_selected_path'], 256)
                cc, pink = struct.unpack('>II', guest.read(symbols['tt_selected_category'] + 4, 8))
                token = (generation, guest.word(symbols['tt_online_requests']))
                if token == last and time.monotonic() - last_sync < 10:
                    time.sleep(.25)
                    continue
                track = tracks[identity]
                if track['revision'] != revision or cc not in (150, 200) or pink not in (0, 1):
                    raise ValueError('Selected category mismatch')
                expected = f"custom/tt/v1/{identity}/{revision[:8]}/{cc}/{'p1' if pink else 'n1'}/"
                if path != expected:
                    raise ValueError('Selected private path mismatch')
                board = dict(track=identity, revision=revision, cc=cc, rules=RULES[pink], client='ctgp-cafe')
                result = sync_board(args.url, board, args.account.resolve(), path, key, args.dev_pid, remote['pack_hash'], uploaded)
                if args.sd:
                    args.sd.mkdir(parents=True, exist_ok=True)
                    target = args.sd / 'ctgp-local-board.bin'
                    temporary = args.sd / 'ctgp-local-board.bin.tmp'
                    temporary.write_bytes(board_snapshot(board, result['leaderboard'], result['native_manifest'], int(time.time()*1000), mii))
                    temporary.replace(target)
                status = dict(connected=True, transport='local-cemu-development-adapter', authenticated_nex=False, pid=session['pid'], name=track['name'], board=board, pack_hash=remote['pack_hash'], **result)
                args.status.write_text(json.dumps(status, indent=2))
                print(json.dumps(dict(name=track['name'], cc=cc, rules=board['rules'], records=len(result['leaderboard']), downloaded=result['downloaded'], submitted_pending=result['submitted_pending'])), flush=True)
                last, last_sync = token, time.monotonic()
            except (OSError, ValueError, KeyError) as error:
                args.status.write_text(json.dumps(dict(connected=False, error=str(error))))
                print(type(error).__name__ + ': ' + str(error), flush=True)
                time.sleep(1)
    finally:
        guest.close()


if __name__ == '__main__':
    main()
