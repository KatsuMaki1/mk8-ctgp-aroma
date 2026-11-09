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

## 2026-11-01: restore a single twelve-cup page
User reports full WiiU bundle regressed to the original 8+4 layout. Current
CUP0 confirmed8 type3 +4 type4. tools/bolt_pages.py consolidates all12 into
(type3,icon0..11), preservescupIDs36..47/all48trackidentities and19othercups.
Renderer02B13A54 explicitly iterates12 nativebuttons; trackpreview02B137EC
acceptspositions0..11. Removingtype4 also lowersmaxpage4->3 (no blankpage).
Importerplacesnowuses12 type3 positions forfutureimports. Icontextures are
alreadyin ctgp.szs underBolt36..47; noUI/model/code/pluginupdate required.
Patch outputs/WiiU/Mises_a_jour/WiiU_Boltthunder_One_Page.zip8734bytes,
onlypaireddata.cup0/custom/cup0+readme. CRCverified; payloadSHA256
8cad03636ef798612322ab6f7bac24666a349850f25e991b5d8e6cb2647acbd2.
SourcefullP4/currentCemuCUP0SHA446d4a6a30558a71ed2ee6c1bfb66960995c2f2ae171cf91df856c586db01e19.
NOTinstalledinCemu (no user closure requested/needed forWiiUpatch). Nextfull
WiiUbundle MUSTapplybolt_pages.consolidate tosourceCUP0 or useworkspace
work/bolt_one_page/data.cup0, otherwise it will regress again. Keepv026plugin
andv024CafeLoadercode; hostdata/iconchecks passed, consolemenu testpending.

Full v026 bundle builder: work/package_aroma_full_v026.py uses current content,
work/dlc_paths v024 CafeLoader code, exact user-confirmedv026 plugin and
bolt_pages.consolidate(CUP0) applied at packaging time. Thus both CUP0 aliases
in the new fullZIP have the single-page layout even though Cemu source content
was notinstalled/modified. Output CTGP_Aroma_COMPLET_SD_v026_Bolt_1page_2026-11-01.zip.
Latest plugin matches smallv026ZIP byteforbyte;v022mustnotbereintroduced.
