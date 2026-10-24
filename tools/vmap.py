"""Map addresses of MK8 v64 (the CTGP release target) to MK8 v81 by aligning the two .text sections.

Alignment works on a "skeleton" of each instruction (branch offsets and 16-bit immediates of address-like
forms are dropped), anchored on 8-word windows that are unique in both builds, chained monotonically and
filled in between anchors with difflib. Data addresses are mapped through the aligned code (the same global
referenced by aligned lis/lo16 pairs) and through vtables (pointer-to-aligned-function neighbours).
"""
import struct, difflib, bisect, pickle, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rpxlib

W = 8   # window size for anchors


def skeleton(w):
    op = w >> 26
    if op == 18: return w & 0xFC000003                       # b/bl: drop offset
    if op == 16: return w & 0xFFFF0003                       # bc: drop displacement
    if op in (15, 24, 25) or 32 <= op <= 55: return w & 0xFFFF0000   # lis/ori/oris/loads/stores: drop immediate
    if op == 14 and ((w >> 16) & 31) != 0: return w & 0xFFFF0000      # addi rD,rA!=0: drop immediate (li keeps it)
    return w


def words(sec):
    d = sec['data']; n = len(d) // 4
    return list(struct.unpack('>%dI' % n, d[:n * 4]))


def lis_chain(seq):
    """longest increasing subsequence on second coordinate, input sorted by first; returns kept pairs"""
    tails, idx, prev = [], [], [-1] * len(seq)
    for k, (a, b) in enumerate(seq):
        j = bisect.bisect_left(tails, b)
        if j == len(tails): tails.append(b); idx.append(k)
        else: tails[j] = b; idx[j] = k
        prev[k] = idx[j - 1] if j else -1
    out = []; k = idx[-1] if idx else -1
    while k >= 0: out.append(seq[k]); k = prev[k]
    return out[::-1]


class TextMap:
    def __init__(self, rpx64, rpx81):
        _, S64 = rpxlib.load(rpx64); _, S81 = rpxlib.load(rpx81)
        t64 = next(s for s in S64 if s['name'] == '.text'); t81 = next(s for s in S81 if s['name'] == '.text')
        self.base64, self.base81 = t64['addr'], t81['addr']
        self.w64, self.w81 = words(t64), words(t81)
        self.k64 = [skeleton(w) for w in self.w64]; self.k81 = [skeleton(w) for w in self.w81]
        self.m = [-1] * len(self.w64)
        self._align()

    def _windows(self, k):
        d = {}
        for i in range(len(k) - W + 1):
            h = hash(tuple(k[i:i + W])); d[h] = -1 if h in d else i      # -1 marks duplicates
        return d

    def _align(self):
        d64, d81 = self._windows(self.k64), self._windows(self.k81)
        anchors = sorted((i, d81[h]) for h, i in d64.items() if i >= 0 and d81.get(h, -1) >= 0)
        anchors = lis_chain(anchors)
        self.anchors = anchors
        # extend each anchor window to a block, then fill gaps with difflib
        prev64 = prev81 = 0
        blocks = []
        for i, j in anchors:
            blocks.append((i, j))
        # walk: for consecutive anchors (i0,j0) -> (i1,j1): window i0..i0+W matched 1:1; the span between is diffed
        pos64 = pos81 = 0
        def fill(a0, a1, b0, b1):
            if a1 <= a0 or b1 <= b0: return
            if a1 - a0 == b1 - b0 and self.k64[a0:a1] == self.k81[b0:b1]:
                for x in range(a1 - a0): self.m[a0 + x] = b0 + x
                return
            if (a1 - a0) * (b1 - b0) > 4_000_000_000: return
            sm = difflib.SequenceMatcher(None, self.k64[a0:a1], self.k81[b0:b1], autojunk=False)
            for blk in sm.get_matching_blocks():
                for x in range(blk.size): self.m[a0 + blk.a + x] = b0 + blk.b + x
        for (i, j) in anchors:
            fill(pos64, i, pos81, j)                       # gap before this anchor
            for x in range(W): self.m[i + x] = j + x       # the anchor window itself
            pos64, pos81 = i + W, j + W
        fill(pos64, len(self.k64), pos81, len(self.k81))

    # ---- queries (addresses are RPX addresses)
    def to81(self, a):
        i = (a - self.base64) // 4
        if not 0 <= i < len(self.m) or self.m[i] < 0: return None
        return self.base81 + self.m[i] * 4

    def exact(self, a):
        """True if the aligned instruction is bit-identical (not just same skeleton)"""
        i = (a - self.base64) // 4
        j = self.m[i] if 0 <= i < len(self.m) else -1
        return j >= 0 and self.w64[i] == self.w81[j]

    def stats(self):
        ok = sum(1 for x in self.m if x >= 0)
        return len(self.m), ok


if __name__ == '__main__':
    r64, r81 = sys.argv[1], sys.argv[2]
    tm = TextMap(r64, r81)
    n, ok = tm.stats(); print('words', n, 'aligned', ok, '%.1f%%' % (100 * ok / n), 'anchors', len(tm.anchors))
    # ground truth: release v64 patch sites vs upstream v81 addresses
    truth = [(0x025B9480, 0x025B9634), (0x025E4750, 0x025E4904), (0x02677548, 0x026776FC)]
    for a, want in truth:
        got = tm.to81(a); print('%08X -> %s (want %08X) %s' % (a, '%08X' % got if got else None, want, 'OK' if got == want else 'MISMATCH'))
    pickle.dump((tm.base64, tm.base81, tm.m), open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'textmap.pkl'), 'wb'))


# ---------------------------------------------------------------- data mapping
DFORM = set(list(range(32, 56)) + [14, 12, 13])
def sx16(v): return v - 0x10000 if v & 0x8000 else v


class Maps:
    """text(a64)->a81 via the code alignment; data(a64)->a81 via aligned lis/lo16 pairs; slot(a64)->a81 for vtable-like pointer tables."""
    def __init__(self, rpx64, rpx81):
        self.tm = TextMap(rpx64, rpx81)
        _, S64 = rpxlib.load(rpx64); _, S81 = rpxlib.load(rpx81)
        self.S64, self.S81 = S64, S81
        self._observe()
        self.ptr64 = self._ptrs(S64); self.ptr81 = self._ptrs(S81)
        self.by81 = {}
        for a, v in self.ptr81.items(): self.by81.setdefault(v, []).append(a)

    def text(self, a): return self.tm.to81(a)

    def _observe(self):
        from collections import Counter, defaultdict
        tm = self.tm; w64, w81, m = tm.w64, tm.w81, tm.m
        obs = defaultdict(Counter)
        n = len(w64)
        for i in range(n):
            w = w64[i]
            if w >> 26 != 15 or (w >> 16) & 31 != 0: continue
            hi = w & 0xFFFF
            if not 0x1000 <= hi < 0x1040: continue
            j = m[i]
            if j < 0: continue
            v = w81[j]
            if v >> 26 != 15 or (v >> 16) & 31 != 0 or ((v >> 21) & 31) != ((w >> 21) & 31): continue
            reg = (w >> 21) & 31; hi81 = v & 0xFFFF
            for k in range(1, 7):
                if i + k >= n or m[i + k] != j + k: break
                a, b = w64[i + k], w81[j + k]
                if a >> 26 != b >> 26: break
                op = a >> 26
                if op in DFORM and ((a >> 16) & 31) == reg and ((b >> 16) & 31) == reg:
                    obs[(hi << 16) + sx16(a & 0xFFFF)][(hi81 << 16) + sx16(b & 0xFFFF)] += 1
                    if ((a >> 21) & 31) == reg: break           # reg overwritten
                elif op == 24 and ((a >> 21) & 31) == reg and ((b >> 21) & 31) == reg:
                    obs[(hi << 16) | (a & 0xFFFF)][(hi81 << 16) | (b & 0xFFFF)] += 1
        self.obs = {A: c.most_common(1)[0][0] for A, c in obs.items()}
        self.obs_conf = {A: (c.most_common(1)[0][1], sum(c.values())) for A, c in obs.items()}
        self.obs_sorted = sorted(self.obs)

    def data(self, a):
        if a in self.obs: return self.obs[a]
        # between two observed neighbours with the same delta -> same delta
        k = bisect.bisect_left(self.obs_sorted, a)
        if 0 < k < len(self.obs_sorted):
            lo, hi = self.obs_sorted[k - 1], self.obs_sorted[k]
            d1, d2 = self.obs[lo] - lo, self.obs[hi] - hi
            if d1 == d2 and hi - lo < 0x4000: return a + d1
        return None

    def _ptrs(self, S):
        b = {s['name']: s for s in S}
        out = {}
        for rn in ('.rela.rodata', '.rela.data'):
            rel = b[rn]['data']
            for k in range(0, len(rel), 12):
                o, info, add = struct.unpack('>III', rel[k:k + 12])
                if info & 0xFF == 1 and (info >> 8) == 1: out[o] = 0x02000000 + add     # sym 1 = .text base
        return out

    def slot(self, x64):
        """map a pointer-table slot of v64 (holding a text pointer) to the matching slot of v81, or None"""
        f64 = self.ptr64.get(x64)
        if f64 is None: return None
        f81 = self.text(f64)
        cands = self.by81.get(f81, []) if f81 else []
        best, bestscore = None, -1
        for c in cands:
            score = 0
            for d in range(-5, 6):
                if d == 0: continue
                v64 = self.ptr64.get(x64 + 4 * d); v81 = self.ptr81.get(c + 4 * d)
                if v64 is not None and v81 is not None and self.text(v64) == v81: score += 1
                elif v64 is None and v81 is None: score += 0.25
            if score > bestscore: best, bestscore = c, score
        return (best, bestscore, len(cands)) if best is not None else None


def _delta_mode(self, a, win=0x1000):
    """most common (B-A) among observations near a; returns (delta, share) or (None, 0)"""
    from collections import Counter
    lo = bisect.bisect_left(self.obs_sorted, a - win); hi = bisect.bisect_right(self.obs_sorted, a + win)
    c = Counter()
    for A in self.obs_sorted[lo:hi]:
        c[self.obs[A] - A] += self.obs_conf[A][0]
    if not c: return None, 0
    d, n = c.most_common(1)[0]
    return d, n / sum(c.values())


def _data2(self, a):
    """map a v64 data address to v81: exact observation if backed by the local consensus, else the local consensus delta"""
    d, share = self._delta_mode(a)
    if a in self.obs and (self.obs_conf[a][0] >= 2 or self.obs[a] - a == d or share < 0.6): return self.obs[a]   # well-attested exact observation first
    return a + d if d is not None and share >= 0.6 else None


def _slot2(self, x64):
    r = self.slot(x64)
    if r is None: return None
    d = self.data(x64)
    d2 = _data2(self, x64)
    f81 = self.text(self.ptr64[x64]); cands = self.by81.get(f81, [])
    if d2 is not None and d2 in cands: return d2, 'delta', len(cands)
    return r[0], 'neighbours %s' % r[1], len(cands)


Maps._delta_mode = _delta_mode
Maps.data2 = _data2
Maps.slot2 = _slot2
