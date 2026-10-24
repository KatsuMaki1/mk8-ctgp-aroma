# Notes

## The release targets MK8 v64, not v81
The CTGP-Café console release (`Code.bin`/`Patches.hax`) is built for the **v64** update (the CTGP sources' `build.py` asks for the v64 `Turbo.rpx`, md5 `1b8473fe24eeab27509923c78db51ec0`).
A v81 game has a different code layout: the console→RPX text shift is only uniform (`0x0C180000`) for v64 (77/77 call targets land on function starts); on v81 it varies by region of the code.
On a v81 console the release therefore never applied (a naive loader that checks a few words refuses to patch, or patches garbage).

Console layout of the release: blob code `0x0F800000`, blob data `0x10400020`, game text = RPX + `0x0C180000`, game data = RPX + `0x00502200`.

## Formats
- `Addr.bin`: two big-endian u32, code base and data base of the blob.
- `Patches.hax`: u16 count, then `{u16 len, u32 addr, u8 data[len]}` (all patches are 4 bytes: a `b`/`bl` into the blob, a `li`, a nop, or a vtable pointer).
- `Verify.hax` (ours): same format, holds the original bytes at every patched address of the build the pack was made for.
- The blob calls a function pointer stored at `dataBase-4` (the console loader put `log_printf` there). We point it at a `blr` stub appended to `Code.bin`.

## Cemu specifics (found the hard way)
- Never grow `.shstrtab` of the RPX: Cemu loads it at a fixed address in the "loader info" region and the game then crashes in its static constructors.
  New sections reuse existing name suffixes (`.text` of `.rela.text`).
- The release initialises the blob from a tiny virtual destructor in v64; in v64 the same function is hooked by `bl` at `0x02677548` (v81: `0x026776FC`), which is early enough.
- On console the blob decodes `bl OSDynLoad_*` words with a mask only; Cemu keeps its import trampolines *below* the code, so the offset is negative.
  `mkrpx.py` patches the two decoding instructions with a sign-extending stub (Cemu builds only).
- Pointer-table (vtable) patches: the pointers carry a load-time relocation (`sym1(.text base) + addend`); patch the addend, not just the word.
- Some Cemu builds never apply graphic-pack patches (`patches.txt`), hence the patched RPX.

## Porting method
See README. Validation done: 99.7 % of v64 instructions aligned to v81; ground-truth pairs from the CTGP sources
(`0x025B9480→0x025B9634`, `0x025E4750→0x025E4904`, `0x02677548→0x026776FC`) reproduced; all 21 text patch sites keep the same instruction skeleton;
all 27 vtable slots found uniquely; all 77 external call targets of the ported blob are function starts in v81; MK8 EUR boots and races in Cemu.
Not validated: the CTGP UI on screen, every CTGP feature, the Aroma plugin on a console, USA/JPN v81 builds (the pack is only generated and verified against the EUR v81 RPX; `Verify.hax` makes the plugin refuse other builds).

## Debugging trick
`tools/debug/dump_regs_probe.S`: a position-independent probe that copies registers and some memory onto the stack and then crashes on purpose, so Cemu's crash log prints them.
`mkrpx.py --probe-addr <console addr> --probe-bin <probe.bin>` overwrites an instruction of the blob with a branch to it.
