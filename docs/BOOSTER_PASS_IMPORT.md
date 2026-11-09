# Booster Course Pass, 2026-10-31

**R1 below is superseded by the R2 correction at the end of this document.**
The source menu thumbnails did NOT reliably identify their associated models.

User supplied `C:/Users/evant/Downloads/Demo_BoosterCoursePass.rar` and requested
all the remaining Booster cups. The archive contains 48 replacement tracks
plus three duplicate Animal Crossing seasonal donors, rather than custom
course directories. All 48 thumbnails were decoded and inspected. The source
Spanish messages contain wrong/inconsistent names; the mapping in
`tools/booster_pass.py` follows the actual thumbnail assets and canonical cup
order. Runtime geometry still needs user verification.

The installed Cemu build fills the eleven remaining type-1 Booster cups with
44 independent folders, `Gu_Bcp05` through `Gu_Bcp48`. Existing Golden Dash
resources, all other 19 cups, original cup IDs/icons/page positions, the ROB
menu and character resources, extra vehicles and CTGP logos are preserved.
Both `data.cup0` and `custom/cup0` contain the same 31 cups. No type-4 conversion
or new page is used. The existing Booster gate already accepts complete cups.

Staging and backups are on C: because E: has limited free space:

`C:/Users/evant/Documents/Codex/2026-10-25/files-mentioned-by-the-user-handoff/work/booster_pass_20261031`

The root contains inventory, 48 decoded previews/contact sheets, source audit,
`staged/content`, `staged/manifest.json`, `Turbo_Booster48.rpx` and its manifest,
and `installation/state.json`. Source extraction is under `source/DLC 8DX Tracks`.
The builder requires the pre-install content baseline; do not rerun it against
the modified installation as if that were the original baseline.

## Music and objects

88 normal/final-lap BFSTM streams are unique to these new folders. They were
decoded, resampled to 32 kHz, normalized to the actual native menu-slot donor's
channel count, encoded with loops retained, then independently decoded to
check every channel has sound. FSTP prefetch data was regenerated from each
full stream, and all 88 pairs compared byte-for-byte. Labels and numeric IDs
follow the native slot, rather than the replacement archive's source slot.
Snow Mountain's extra music prefetch uses the imported normal music.

Three full music pairs are absent from the supplied archive: Mario Circuit 3,
DK Summit, Squeaky Clean Sprint. Those pairs come from their already installed
counterparts Gu_Bolt21, Gwii_KongSummit, Gu_Bolt37, respectively.

32 missing DLC normal/final music labels were appended to the installed BFSAR
as stream records cloned from the native Desert donor. All original sound
records, label IDs and FILE block samples were checked unchanged, including
ROB's voices and horn. No source pack BFSAR or driver bank is installed.

Course banks retain native slot environmental sounds where available. 148
unknown DLC ambient labels across the course banks were omitted rather than
binding unrecognized numeric IDs. Some DLC ambient effects therefore remain
unavailable; this build does not claim those effects are fully ported.
Private object sound banks similarly retain only recognized labels.

201 absent object definitions were merged using the existing canonical BYAML
writer; old definitions are unchanged and collision category counts match v81.
581 supplied changed/missing object resources live under `custom/bcp/mapobj`.
`tools/native/booster_assets.c` redirects only those exact paths, only after a
course path under Gu_Bcp05..48. It excludes Golden Dash's named folders, old
custom courses, vanilla courses, malformed IDs and unknown asset paths.
Three formatter wrappers chain the previous hooks by their actual branch
destinations. Code/data append at aligned free ends, with RPX allocation sizes
updated and every non-relocation section checked after repacking.

## Installation and checks

`work/install_booster_pass.py` verified all 1157 staged hashes/sizes, required
paths, 88 stream/prefetch pairs and recognized music labels, then required Cemu
to be closed. It copied 1153 previously absent assets with per-file hash checks.
The four control files and RPX were installed as IndependentROB revision
`booster_pass_48`, retaining the original rollback and prior ROB symbols.
Do not restore the entire original ROB installation just to undo Booster:
use this revision's saved preceding state/control files, then remove only the
new paths listed in `installation/state.json` after verifying their hashes.

Installed RPX SHA256:
6025f70bdca45919f14fbe29e88dc2d08a974ed93cc469c7d7005781873080e2

Staged content size: 4,169,847,077 bytes. Cemu PID9552 was launched with the
existing non-killing debugger. CTGP8 boot/title and vehicle selection were
observed without a new captured crash. User testing of new Booster races is
pending. The user appeared to be controlling Cemu, so automation stopped
sending inputs and requested representative race tests.

Validation: 21 existing character/archive tests, the new sound-bank filtering
test, and the native host routing fixture all pass. The fixture covers 05/48,
leading slashes, 04/49, malformed IDs, exact whitelist matching and reset on
old courses. No Wii U/Aroma package has been generated for this addition.
Do not distribute a mismatched console pack or claim 48 runtime-tested races.

## R2: actual model mapping and formatter crash (same day)

User reported wrong names, specifically a tree circuit under a Waluigi name,
and a crash selecting Maple Treeway. The debugger captured Gu_Bcp31 loading
MareM, followed by guest stack corruption: saved registers/backchain contained
the redirected pathname. The source object models were not the crash cause.

Disassembly established that BufferedSafeString's vtable100FFC14 calls
0272CBCC, which reads capacity at object+8 and writes text[capacity-1]=0.
Our redirected object has only two words. Copying the source buffered vtable
therefore read unrelated stack data as capacity and corrupted guest memory.
The replacement now explicitly uses the plain SafeString vtable100FFBCC,
whose terminator method0272CBC8 returns without touching memory. The native
host test now supplies a buffered source vtable and requires the plain output
vtable, so the original bug would fail the fixture.

All 48 course models were decompressed with wszst, their actual FMDL names
read, and the distinct Cnsw11..68 IDs checked for complete wave/slot coverage.
`model_audit.json` and `model_maps_0.png`/`model_maps_1.png` retain the evidence.
The source UI is a different mapping from the actual geometry. The new pure
`tools/booster_mapping.py` rejects missing, duplicate, invalid and ambiguous
model IDs. The importer now requires this model audit and uses thumbnails
only to select the picture, independently from geometry source folders.

R2 CUP0 records point to the existing appropriate imported directories; no
large model files were copied again. Maple Treeway now uses Gu_Bcp19/Cnsw34;
Waluigi Pinball Gu_Bcp45/Cnsw24; DK Mountain Gu_Bcp31/Cnsw62; Rosalina's Ice
World Gu_Bcp20/Cnsw66. Human labels remain the canonical English cup ordering.
All 44 music banks were rebuilt for their corrected native menu-slot donors,
with 16 replacement streams normalized where channel counts or fallback
sources changed. All 88 normal/final prefetch pairs were checked again.

Full supplied music is absent for Riverside Park and Vancouver Velocity.
Their source-slot native themes (Sherbet Land/Yoshi Valley) are temporary
fallbacks, not claimed as authentic track music. Mario Circuit3 retains its
existing Bolt counterpart theme. DLC ambient limitations from R1 remain.

Installed 63 files with guarded hashes and original-state backups, revision
`booster_pass_r2_model_mapping_and_string_vtable`. R2 artifact/root:
`work/booster_pass_20261031/r2` in the C: workspace. RPX SHA256:
f8ae6d6b666661e92b33bf4ca3acd7a0d0b7733f80fef2c3d4f544b64b98bc9e

The prior crash and log are saved as r2/crash_before_r2.json and
r2/log_before_r2.txt. Cemu debug launch PID29576. User race test requested for
Maple Treeway (Rock) and Waluigi Pinball (Turnip); results pending.

User also asked whether lap-dependent city routes could be reimplemented and
offered an owned MK8DX update ExeFS. No such dump has been supplied yet. The
archive's objflow includes RouteChangeArrow/Green/Path definitions, and track
data includes LapPath, EnemyPath, ItemPath, return/checkpoint data and an
extra SteerAssistPath. The supplied Paris list has no RouteChangeArrow objects.
These are clues, not proof that dynamic routing is implemented in the Wii U
ports. A port must account for barrier collision/visibility, checkpoint/lap
validation, AI/item routes, respawn and online consistency. No new dynamic
route code was installed. ExeFS version plus relevant RomFS course data would
be needed for further comparison; executable code alone is insufficient.

## R3: sky and object directory enumeration

User reported broken skies on the new tracks after R2. R2 log proves the
loader first calls FSOpenDir on mapobj/VRCnsw42 (and its FX variant), before
enumerating resource filenames. R1/R2 whitelisted files only. Missing private
directories thus prevented the files from being discovered at all.

R3 includes exact directory paths with/without trailing slash as well as file
paths in the scoped routing table. All 454 source directories are covered.
Their private contents now include unchanged stock resources and stock files
omitted from the replacement archive (base, then update, then supplied files
take precedence). This is a complete directory overlay, not a changed-file
diff. Empty source directories/optional missing FX retain their normal absence.
The builder tools/booster_pass.py has the same corrected preparation logic.

594 private files were verified. Only13 additional/changed files plus the RPX
needed writing; all other resources were already present. Installed revision
booster_pass_r3_directory_resources. Existing CUP0 mapping/music/objflow, ROB,
vehicle files and logos are unchanged. Source/current definitions used by
these44 tracks agree on resource/manager names except ID1170 DL_WdBird:
current ResName Bird vs source DL_WdBird. That single legacy bird resource
definition is retained to protect older tracks; a separate per-course
definition override is not part of this patch.

R3 outputs/manifest/installation report are under workspace
work/booster_pass_20261031/r3. RPX SHA256:
633ff6401835e94d8945e26a4e8e5640fbbeb7ca957ecc0e43571feef19f2e9e

Native host fixture now verifies directory enumeration paths, trailing slash,
unknown sibling rejection, exact files, buffered-source/plain-result vtable,
course scope and reset. It passes. Cemu launched with debugger PID3524;
visual sky/object validation pending. Do not claim all new tracks visually
verified. No Aroma/Wii U bundle update was generated.

User subsequently confirmed correct skies/scenery on the requested Riverside
Park and Maple Treeway tests. R3 installed.json records that limited runtime
validation; it does not imply all48 races were tested.

User supplied the MK8DX update NSP named v4.0.1, title0100152000022800,
version1507328. Read-only inspection found a PFS0 container with8 files.
Plaintext CNMT XML confirms Patch, version1507328, base0100152000022000 and
program content9b5ca1863da58ddfa3012591878ef670 (4,848,707,072 bytes).
NCA headers/content are encrypted; no ExeFS instructions or RomFS course data
have been read or analyzed from it. No keys/tickets were extracted or used.
Inventory and plaintext metadata only are under workspace work/mk8dx_401.
Further code analysis needs an already-readable personal ExeFS dump (main,
main.npdm, optional subsdk*) and relevant RomFS course data, preferably the
base/update merged view. Do not claim NSP reverse engineering is completed.
