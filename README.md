# mk8-ctgp-aroma

Tools and an Aroma plugin to run **CTGP-Café** (custom tracks for Mario Kart 8, Wii U) on a **v81** game, on **Cemu** and on a console with **Aroma**.

CTGP-Café's public release is built for MK8 **v64**. A v81 game has a different code layout, so the release cannot be applied as is
(that is why it silently does nothing on a v81 console). This repository ports it: every address the release code uses is moved from the
v64 build to the v81 build by aligning the two executables, and the result is delivered two ways:

| Target | What you get |
|---|---|
| **Cemu** | a patched `Turbo.rpx` with the CTGP code baked in (`tools/mkrpx.py`, `cemu/install_cemu.py`) |
| **Wii U (Aroma)** | a v81 code pack + a WUPS plugin that patches the game at boot and merges the CTGP content (`tools/mkpack.py`, `plugin/`) |

> **Status.** Cemu: Mario Kart 8 EUR boots and races with the patched v81 RPX and with the v64 RPX (checked on Cemu 2.6 / Vulkan);
> the on-screen CTGP cup UI has not been confirmed visually yet. Aroma plugin: builds, **never run on a console yet**.
> Everything is static-checked by `tools/verify_rpx.py` (0 failures) but expect rough edges.

This repository contains **only our code**. It does not contain, and you must supply yourself:
- the CTGP-Café release (`ctgp_cafe_wiiu.zip`: `Code.bin`, `Data.bin`, `Patches.hax`, tracks, layouts) — © its authors, no licence is published for it;
- your own Mario Kart 8 `Turbo.rpx` files (v81, and v64 for the porting step) — © Nintendo.

## How it works (short)

1. `vmap.py` aligns the v64 and v81 `.text` sections on an instruction "skeleton" (branch offsets and address-like immediates dropped), anchored on
   windows that are unique in both builds. 99.7 % of the 2.9 M instructions align; three known v64↔v81 address pairs from the CTGP sources are reproduced exactly.
   Data addresses are mapped through the aligned code (same global referenced by aligned `lis`/`lo16` pairs) and through vtable slots.
2. `retarget.py` rewrites the CTGP blob for the new addresses: `lis`/`lo16` pairs (data-flow over the CFG with capstone), `bl` targets, pointer tables.
3. `mkrpx.py` adds the blob to the RPX as two sections, applies the 48 patches (vtable pointers by editing the load-time relocation addend) and fixes
   the file info / CRC table. `mkpack.py` instead writes a console pack in the original release layout (`Code.bin`, `Data.bin`, `Patches.hax`, `Addr.bin`) plus `Verify.hax`.
4. The plugin (`plugin/`) loads that pack at MK8 start, **after checking that every patched address still holds its original bytes** (`Verify.hax`), and
   adds ContentRedirection layers for `course`, `mapobj`, `ui`, `custom`, `charger` and `data.cup0`.

More detail and the things that went wrong on the way: [docs/NOTES.md](docs/NOTES.md).

## Usage

Requirements: Python 3, `pip install capstone pycryptodome`; devkitPro + WUPS + `libcontentredirection` + `libnotifications` for the plugin.

### 0. Get the executables
```
python tools/nus_fetch.py --title 0005000e1010ed00 --version 64 --path code/Turbo.rpx --otp <path to your otp.bin> --out Turbo_v64.rpx
```
(use the title id of your region: `…ed00` EUR, `…ec00` USA, `…eb00` JPN; the v81 one is your installed update's `code/Turbo.rpx`.)

### 1. Cemu
```
python cemu/install_cemu.py --update-dir "<Cemu>/mlc01/usr/title/0005000e/1010ed00" --v64-rpx Turbo_v64.rpx --zip ctgp_cafe_wiiu.zip
```
Backs up your `Turbo.rpx` to `Turbo.rpx.bak` (always rebuilt from that backup) and copies the CTGP content into the update's `content/`.
Note: CTGP's `mapobj` files replace same-named files of the update without a backup. `cemu/test_cemu.ps1` launches the game and reports crashes.
Cemu's graphic-pack patches are not used (some builds never apply them): the code is inside the RPX.

### 2. Wii U (Aroma)
```
python tools/mkpack.py --v64-rpx Turbo_v64.rpx --v81-rpx Turbo_v81.rpx --release "<zip>/cafeloader/000500001010EC00" --out sd/cafeloader/000500001010ed00
```
Copy the CTGP `cafeloader/vol/<TitleID>/content` folder next to it (`sd:/cafeloader/vol/000500001010ed00/content`), build `plugin/` (`make`) and put
`mk8-ct.wps` in `wiiu/environments/aroma/plugins/`. Needs the Aroma ContentRedirection module.
Debug switches (empty files in `sd:/wiiu/mk8-ct/`): `log_file`, `notif`, `no_code`, `no_content`, `skip_<dir>`.

## Credits
CTGP-Café by RamboGlaz and contributors · CafeLoader by aboood40091 / AboodXD · Wii U Plugin System by Maschell and contributors.
This project's own code is MIT licensed.
