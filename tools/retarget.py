"""Retarget the CTGP-Cafe console blob (Code.bin/Data.bin) to a new layout.

Console layout (what the blob was linked for):
  blob code  0x0F800000      blob data 0x10400020
  game text  rpx + 0x0C180000   game data rpx + 0x00502200   (both are console loader shifts)
Target layout (Cemu, unshifted RPX): game text/data at their RPX addresses, blob at T (code) / D (data).
T must be 64 KiB aligned and D % 0x10000 == 0x20, so all blob-internal lo16 halves stay valid and only the
hi16 of `lis` changes; game-data references (shift 0x502200) are rewritten pair by pair (hi and lo).
"""
import struct
from capstone import Cs, CS_ARCH_PPC, CS_MODE_32, CS_MODE_BIG_ENDIAN, CS_OPT_DETAIL
from capstone import ppc_const as P

CB, DB = 0x0F800000, 0x10400020
GT_SHIFT, GD_SHIFT = 0x0C180000, 0x00502200
GT_LO, GT_HI = 0x0E180000, 0x0EC90000           # console game text range
GD_LO, GD_HI = 0x10502200, 0x10800000           # console game data range

md = Cs(CS_ARCH_PPC, CS_MODE_32 | CS_MODE_BIG_ENDIAN)
md.detail = True


def sx16(v): return v - 0x10000 if v & 0x8000 else v
def u32(b, o): return struct.unpack('>I', b[o:o+4])[0]


def reg_name(insn, rid):
    return insn.reg_name(rid)


READ_ALL = ('st', 'cmp', 'mt', 'tw', 'td', 'dcb', 'icb', 'sync', 'eieio', 'isync', 'b', 'fcmp', 'cr', 'ps_st')


def rw(ins):
    """(reads, writes) of general registers 'rN' for one instruction (capstone has no regs_access for PPC)."""
    reads, writes = set(), set()
    first = True
    all_read = ins.mnemonic.startswith(READ_ALL) and not ins.mnemonic.startswith(('mtfs',))
    for op in ins.operands:
        if op.type == P.PPC_OP_REG:
            n = ins.reg_name(op.reg)
            if n.startswith('r') and n[1:].isdigit():
                (reads if (all_read or not first) else writes).add(n)
            first = False if n.startswith(('r', 'f')) else first
        elif op.type == P.PPC_OP_MEM:
            b = ins.reg_name(op.mem.base) if op.mem.base else None
            if b and b.startswith('r') and b[1:].isdigit():
                reads.add(b)
                if ins.mnemonic.endswith('u') or ins.mnemonic.endswith('ux'):   # update forms write the base
                    writes.add(b)
    return reads, writes


def encode_branch(word, pc_new, target_new):
    """Re-encode relative b/bl so it lands on target_new when located at pc_new."""
    off = target_new - pc_new
    if not -0x2000000 <= off < 0x2000000 or off & 3:
        raise ValueError('branch out of range %08X -> %08X' % (pc_new, target_new))
    return (word & 0xFC000003) | (off & 0x03FFFFFC)


class Blob:
    def __init__(self, code, data):
        self.gd_new = []
        self.code = bytearray(code)
        self.data = bytearray(data)
        self.n = len(code) // 4
        self.W = [u32(code, i*4) for i in range(self.n)]
        self.ins = {}
        for i in range(self.n):
            d = list(md.disasm(code[i*4:i*4+4], CB + i*4))
            self.ins[i] = d[0] if d else None

    # ---- category of an address in the console layout
    def cat(self, a):
        if CB <= a < CB + len(self.code): return 'bcode'
        if 0x10400000 <= a < 0x10500000: return 'bdata'
        if GT_LO <= a < GT_HI: return 'gtext'
        if GD_LO <= a < GD_HI: return 'gdata'
        return None

    # ---- consumers of a `lis` (hi half) via CFG walk; returns list of (index, kind) or raises on odd use
    def consumers(self, i):
        w = self.W[i]
        reg = (w >> 21) & 31
        out, seen, stack = [], set(), [i + 1]
        while stack:
            j = stack.pop()
            while 0 <= j < self.n and j not in seen:
                seen.add(j)
                v = self.W[j]; op = v >> 26; ins = self.ins[j]
                if ins is None:
                    break
                rt, ra = (v >> 21) & 31, (v >> 16) & 31
                # --- reads of reg that carry the address
                if op in (14, 12, 13) and ra == reg:                  # addi / addic: lo16 consumer
                    out.append((j, 'signed'))
                    if rt == reg: break                               # overwritten with full address
                elif op in range(32, 56) and ra == reg:              # load/store D-form with base reg
                    out.append((j, 'signed'))
                    if op in (32, 34, 40, 42, 48, 50) and rt == reg: break   # load into reg itself
                    if op in (33, 35, 41, 43, 49, 51, 37, 39, 45, 47, 53, 55) and True:  # update forms write RA
                        break
                elif op == 24 and rt == reg:                          # ori ra, rs=reg, imm
                    out.append((j, 'ori'))
                    if ra == reg: break
                elif op == 15 and rt == reg:                          # lis overwrites
                    break
                else:
                    # any other instruction reading/writing reg?
                    rd, wr = rw(ins)
                    rn = 'r%d' % reg
                    if rn in wr:
                        break
                    if rn in rd and op not in (18, 16, 19):
                        raise ValueError('unsupported use of r%d at %08X: %s %s' % (reg, CB + j*4, ins.mnemonic, ins.op_str))
                # --- control flow
                if op == 18:                                          # b / bl
                    aa, lk = (v >> 1) & 1, v & 1
                    if lk:
                        if reg in (0,) + tuple(range(3, 13)): break   # call clobbers volatile regs
                    else:
                        off = v & 0x03FFFFFC
                        if off & 0x02000000: off -= 0x04000000
                        t = off if aa else (CB + j*4 + off)
                        if CB <= t < CB + len(self.code): j = (t - CB) // 4; continue
                        break
                elif op == 16:                                        # bc
                    off = v & 0xFFFC
                    if off & 0x8000: off -= 0x10000
                    t = off if (v >> 1) & 1 else CB + j*4 + off
                    if (v & 1) and reg in (0,) + tuple(range(3, 13)): break
                    if CB <= t < CB + len(self.code): stack.append((t - CB) // 4)
                elif op == 19:
                    if v in (0x4E800020,): break                     # blr
                    if (v & 0x7FF) in (0x420, 0x421) or (v >> 1 & 0x3FF) == 528:   # bctr/bcctr(l)
                        if v & 1 and reg in (0,) + tuple(range(3, 13)): break
                        if not (v & 1): break
                    elif (v >> 1 & 0x3FF) == 16:                    # bclr cond
                        pass
                j += 1
        return out

    # ---- main transform
    def retarget(self, T, D, gt=None, gd=None):
        """gt/gd map a console game text/data address to the output address (default: plain unshifted v64 RPX layout).
        For another game build (v81) they go through vmap.Maps; they may return None for unknown addresses (error)."""
        assert T % 0x10000 == 0 and D % 0x10000 == 0x20, 'T 64K aligned, D%0x10000==0x20'
        def _gt(c):
            r = (gt or (lambda c: c - GT_SHIFT))(c)
            if r is None: raise ValueError('no mapping for game text address %08X' % c)
            return r
        def _gd(c):
            r = (gd or (lambda c: c - GD_SHIFT))(c)
            if r is None: raise ValueError('no mapping for game data address %08X' % c)
            return r
        dC, dD = T - CB, D - DB
        assert dC % 0x10000 == 0 and dD % 0x10000 == 0
        W = list(self.W)
        stats = dict(lis_bcode=0, lis_bdata=0, lis_gtext=0, lis_gdata=0, pairs_gdata=0, br_gtext=0, br_blob=0, bc_blob=0, data_ptrs=0)
        # 1. lis rewrites
        for i, w in enumerate(self.W):
            if not (w >> 26 == 15 and (w >> 16) & 31 == 0):
                continue
            hi = w & 0xFFFF
            if hi == 0x1040:
                W[i] = (w & 0xFFFF0000) | ((hi + (dD >> 16)) & 0xFFFF); stats['lis_bdata'] += 1
            elif hi == 0x0F80:
                W[i] = (w & 0xFFFF0000) | ((hi + (dC >> 16)) & 0xFFFF); stats['lis_bcode'] += 1
            elif 0x0E18 <= hi <= 0x0EC9 or GD_LO >> 16 <= hi <= GD_HI >> 16:
                is_text = hi < 0x1000
                cons = self.consumers(i)
                if not cons: raise ValueError('game-address lis without consumer at %08X' % (CB + i*4))
                news, hi_set = [], set()
                for j, kind in cons:
                    lo = self.W[j] & 0xFFFF
                    a = (hi << 16) | lo if kind == 'ori' else (hi << 16) + sx16(lo)
                    lo_r, hi_r = (GT_LO, GT_HI) if is_text else (GD_LO, GD_HI)
                    if not lo_r <= a < hi_r: raise ValueError('game consumer out of range at %08X: %08X' % (CB + j*4, a))
                    n = (_gt if is_text else _gd)(a)
                    nhi = (n >> 16) & 0xFFFF if kind == 'ori' else ((n + 0x8000) >> 16) & 0xFFFF
                    news.append((j, n & 0xFFFF)); hi_set.add(nhi)
                    if not is_text: self.gd_new.append((CB + j*4, n))
                if len(hi_set) != 1:
                    raise ValueError('game-address hi conflict at %08X: %s' % (CB + i*4, [hex(x) for x in hi_set]))
                W[i] = (w & 0xFFFF0000) | hi_set.pop()
                for j, nlo in news: W[j] = (W[j] & 0xFFFF0000) | nlo
                stats['lis_gtext' if is_text else 'lis_gdata'] += 1
                if not is_text: stats['pairs_gdata'] += len(news)
        # 2. branches out of the blob
        for i, w in enumerate(self.W):
            pc_old, pc_new = CB + i*4, T + i*4
            op = w >> 26
            if op == 18:
                aa = (w >> 1) & 1
                off = w & 0x03FFFFFC
                if off & 0x02000000: off -= 0x04000000
                t = off if aa else (pc_old + off)
                if aa: raise ValueError('absolute branch at %08X' % pc_old)
                c = self.cat(t)
                if c == 'bcode': stats['br_blob'] += 1; continue
                if c == 'gtext': W[i] = encode_branch(w, pc_new, _gt(t)); stats['br_gtext'] += 1; continue
                raise ValueError('branch to unknown %08X at %08X' % (t, pc_old))
            elif op == 16:
                off = w & 0xFFFC
                if off & 0x8000: off -= 0x10000
                t = pc_old + off
                if self.cat(t) != 'bcode': raise ValueError('bc leaves blob at %08X -> %08X' % (pc_old, t))
                stats['bc_blob'] += 1
        # 3. data words that are pointers
        data = bytearray(self.data)
        for o in range(0, len(data) - 3, 4):
            v = u32(data, o)
            c = self.cat(v)
            if c == 'bcode': nv = v + dC
            elif c == 'bdata': nv = v + dD
            elif c == 'gtext': nv = _gt(v)
            elif c == 'gdata': nv = _gd(v)
            else: continue
            struct.pack_into('>I', data, o, nv); stats['data_ptrs'] += 1
        code = b''.join(struct.pack('>I', w) for w in W)
        return code, bytes(data), stats
