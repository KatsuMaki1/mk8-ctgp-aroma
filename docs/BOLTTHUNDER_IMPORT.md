# Boltthunder4 additional cups

Source: the user's `Boltthunder4's CT Pack.zip`, SHA-256
`9667d7eacc8687718a34175538876a8bb17c427302c9da472affbf43462ac498`.
The user expressly authorized importing the tracks and icons.

`tools/bolt_pack.py` plans and stages 48 entries as `Gu_Bolt00` through
`Gu_Bolt47`. Twelve additional cups use IDs 36–47, page 3 positions 0–7 and
page 4 positions 0–3. The prior 19 CUP0 records are preserved, resulting in
31 records. The four Animal Crossing seasonal folders have identical course
geometry; only one is represented in the new cups. Two of the source's 48
entries are texture variants.

Cup icons are original BFLIM files, preserved byte for byte. Track previews
come from the source menu archive. The existing CTGP UI archive is retained,
with the additional icons and extended cup animation mapping.

`tools/bolt_assets.py` builds scoped routing for twelve shared map-object
resources. These files live under `custom/bolt_assets/mapobj/`; their source
names and BFRES internals are retained. The router activates on the new
course paths and deactivates on other courses. The Cemu build chains the
existing GameOptions format hooks; the console build wraps the three native
format helpers. It does not include the experimental speedometer toggle.

`work/bolt_pack/prepare_audio.py` gives the 96 main music streams unique
fixed-length names. `tools/console_music.py` normalizes custom audio to
32 kHz and each native donor's channel count, duplicates primary stereo
into the required stereo layers, encodes DSP ADPCM, and verifies decoded
channel RMS. Prefetch data is regenerated from the exact full streams.
Native Ocean/Cloud music is inherited without changing its special layers.
All 105 BFSTM names found in the finalized banks resolve to existing files.

The import does not apply the source's network patch, full menus, global
effects, item skins or Common.msbt. Its README and credits are retained.
The source warns about possible console Grand Prix crashes; start with VS.

Build artifacts are in the chat workspace's `outputs/` directory:

* `WiiU_Boltthunder4_Cups_Addon.zip`: merge `sd/` contents into the existing
  working v0.20 Aroma installation. Code pack has 80 matched patch/verify
  sites. Content belongs under `cafeloader/vol/<title>/content`, separately
  from the code pack at `cafeloader/<title>`.
* `Cemu_Boltthunder4_Cups_Addon.zip`: merge the supplied `mlc01/` tree into
  the actual MLC directory with Cemu closed.

Both include the aligned Golden Dash R4 resources from Online Sync Test 4,
then the new CUP0/UI data. The previous online communication timeout is
still unresolved; this import is not evidence of an online fix.

Local installation changed 596 files, backing up the four existing files
under the chat workspace's `work/bolt_cemu_backup`. `install.json` records
every old/new hash and each newly introduced path. Cemu boot, the new cup
icons and a race have been observed running. All 48 races and real-console
behavior remain unverified.
