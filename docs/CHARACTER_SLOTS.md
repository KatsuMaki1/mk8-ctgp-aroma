# Independent character slots: R.O.B. research and staging

This extension is separate from the existing Mario/DK costume selector. The
requested first independent driver is R.O.B. from `mk8_rob.rar`. The user's latest
instruction is to use **Morton's statistics**, superseding the earlier Mario
request. Morton must remain available and retain his own original resources.

## Current state

An experimental Cemu runtime is now installed, with reversible snapshots under
the update's `code_backups/IndependentROB`. It is not playable yet: hovering the
new slot still crashes. Do not include it in a public/full pack.

Current installed candidate: `work/rob/Turbo_ROB_grid_r3.rpx`, SHA256
`a04300d3a7198c349f65d792e19ec4fcd789ca71747532726965b6e1b97e6c15`.
The original pre-R.O.B. RPX is preserved byte-for-byte, SHA256
`174330d3e45115899a1d53548fa9ea96aff27199385df49c990791c4d0852358`.

`character_patch.py` adds private storage for 37 button pointers per page,
redirects nine audited native inline pointer readers, adjusts audited control
counts and five parameter strides, and appends a native module. The original
inline 36 pointers are mirrored for the existing costume wrapper. Main names,
icons, button availability and setup have scoped wrappers. The recipe hook is
inside the existing vehicle wrapper's original-function gateway, preserving
the recipe-pointer keyed custom vehicle flags; do not copy a descriptor before
that existing wrapper.

The first menu build exhausted the existing UI resource budget and failed to
load `mn_ModeSlct_00.bflyt`. Isolation using the original menu with the same RPX
booted. `character_menu.py` now repacks without obsolete payload copies, uses a
compact BC3 icon, extends only the two main layouts and patches their three
layout animations. The compact menu reached the character screen. The first
new part also inherited the hidden flag from the DLC part used as a template;
R2 explicitly enables the new part's visibility.

First hover failure: native `0242FB08`, inside ancillary-name construction
`0242F9F4`, reached after the model recipe in `0242FC74`. R2 wraps the full
synchronous `0242FC74` finalisation through resource donor 28, restores the
independent descriptor ID 37 afterward, and scopes private driver paths. User
still reports a hover crash. The latest crash is in the native interpreter
fetching PPC address zero, rather than the earlier JIT string-read fault.
`work/rob/debug_jit.py` was extended to read interpreter state from host RCX
and guest memory base from RDI when JIT R13/RSP are absent. That capture showed
PPC IP=LR=0, with return address `02431FBC` still in r27. Disassembly of the
caller shows `bl 0242FC70`: `0242FC70` is `mflr r0`, and `0242FC74` is the
following `stwu`. R2 incorrectly hooked after mflr, losing live r0 across the
C wrapper. R3 hooks the actual `0242FC70` entry. Builder validation now rejects
stwu hook entries preceded by mflr, and a regression reproduces the bad site.
All other new native hook entries were checked against their preceding words.
R3 was installed with a revision snapshot and Cemu relaunched under the debugger;
user has a pending hover/selection test. Do not claim the crash fixed yet.

Eight Python checks and a host execution of the native wrappers pass. The
inline gateway checks emulate a C callee clobbering volatile GPRs, LR, CTR, CR
and XER. These checks do not establish gameplay compatibility.

During testing the user renamed the DLC installation to `1010ed00.backup`.
Cemu's already-open test process retained the old title entry and showed an
unable-to-mount dialog. Restarting the old helper fixed mounting: fresh log
confirmed base + update loaded, DLC not present, running title EUR v81 at 60fps.
Do not regenerate/delete tickets or rename that user backup automatically.

`tools/character_catalog.py` reserves independent ID 37 after the 37 native
character IDs, with donor 28 (Morton). `character_assets.py` verifies donor 28's
short name `Mtn` in the actual Parts table, stages private resources under
`custom/characters/ROB`, and extracts only the character's three original icons.
It deliberately does not apply the author's replacement menu, common archive,
or Common.msbt over the existing CTGP UI.

The archive's authored internal model name is `Morton`. It contains selection
and race voice banks, four kart texture replacements, a kart emblem and a horn
emblem. Its skeletal animations omit `KartThrowK`, `MBikeThrowK`, `SBikeThrowK`
relative to the stock donor. A runtime fallback or a targeted test is necessary;
do not copy differently rigged stock animation data into the model blindly.

Archive SHA256: `35ea27d9cdefebe84a25d10f8ddd9895335ed563d6e21400bcd59806553e1396`.

## Parameter extension

`character_tables.py` appends the new character to DTOM, DRVR, BDDR, WDDR and
DREF in Parts.bin and PTDV in Performance.bin. It preserves the currently
expanded 42 bodies and 23 tires, including all donor cross combinations. The
new PTDV row is byte-identical to Morton. Every existing row/column is checked
against the input before the staged output is accepted.

DRVR has 500-byte records followed by a string pool; dividing the whole section
by its dimensions is incorrect. Its header at +8 is the relative string-pool
offset and must move when appending a record. The existing string offsets inside
each record remain unchanged. The pool itself is preserved byte-for-byte.

There are five native multiply-by-37 instructions relevant to further audit:
`0242BED0`, `0242BF3C`, `0242E4E0`, `02556588`, `02556DB8`.
The first two index the character axes of body and wing compatibility in the
resource recipe builder. They cannot retain a stride of 37 with the new files.
The remaining instructions require checking in their containing functions.

## Native selector findings (clean EUR81 RPX addresses)

* `025D623C` creates exactly 36 character controls, each 0x1E4 bytes, with part
  names `L_Chara_00` through `L_Chara_35`.
* Page control pointers occupy inline `[page+0x2FC, page+0x38C)`; immediately
  following are live page fields. Increasing the loop alone corrupts the page.
  A separate extended pointer array and all its readers are needed.
* `025D65F4` builds the six by six character layout, filters unlocks, merges
  Villager variants into one cell and registers navigation controls.
* `025D7884` and the later main-page update routines search those 36 pointers to
  restore cursor/preview state. `025DBD58` rejects button indices above 35.
* `025DE4D0` only understands 4x4, 5x5, 6x5, 6x6 layout animations. A seventh row
  needs its own positioning/scaling; passing 6x7 merely returns.
* Main selection layouts in current menu.szs have hashes `BB79D54B` (single) and
  `480A7CB8` (multi). Both include the existing 36 named parts. Other layouts
  containing `L_Chara` include unrelated submenus and must not be patched blindly.
* `0257C49C` configures the character button's identity and texture.
* `0255A668` indexes character icons at ID+1, but index 38 already begins Yoshi's
  color icons. Appending ID 37 without an explicit lookup would show Yoshi.
* `025D269C` sets the character name, with special paths for existing variants.
* `0256684C` writes character ID at native player+0x1C0, variant at +0x1C4, and
  updates the second race selection representation.
* `0242BDDC` builds character/vehicle resource recipes. It must preserve the
  independent race identity while resolving R.O.B.'s authored Morton resources
  privately, including when a real Morton and R.O.B. are both present.

The scratch decompilation/audit scripts and staged files live in `work/rob/`.
`grid_sites.txt` lists potential pointer/count sites. That list is an audit aid,
not a patch manifest: several 0x24 comparisons mean Villager's native ID rather
than a control count. Blindly replacing all 0x24 constants is incorrect.

## Remaining implementation and validation

R5 is installed: the user confirmed R.O.B. can race, with a screenshot showing
the model in Mario Kart Stadium. The minimap icon is white, and other screens
still use Morton icons; own voice is not active in R5.

R6 is installed, awaiting gameplay verification: explicit loose `ui/` texture paths, scoped private
kart emblem prefix, private race/menu voice archive paths and Audio.bin prefix
ROB. `character_voice.py` clones 78 voice events into a new BFSAR while preserving
all original sound IDs, records and the FILE payload. Renamed BARS retain the
authored waveforms. This needs runtime validation; host checks do not establish
working sound playback. After the user closed Xapfish, revision
`private_voice_explicit_icons` installed successfully. Debug helper PID 18112
booted without a new captured exception. Original rollback remains in
`code_backups/IndependentROB`.

The grid, independent identity, Morton stats and scoped model routing work in R5.
R6 user test: voice missing. Logs confirm both private ROB BARS open successfully.
R7 installed: audited native voice-prefix formatter `02067780` rejected ID37 at
`02067798` (`cmplwi r4,37`) before accessing DRSE. The private-voice build now
changes that bound to38; subsequent DRSE access already uses the table count.
Fourteen host/Python tests pass. Cemu debug helper PID10808 launched; menu and
race voice playback await user verification.
User confirmed R7 voice works only in menu. R8 diagnostic installed and booted;
the initial `02060FB8` label trace was empty (race voices use another lookup).
Read-only live inspection located ROB actor `45248C98`, prefix ROB at+230,
voice actor+1B8 nonzero. Its attached banks at+214 contain PackunFlower, Dokan1,
KartCommon, K_Wld and KT_200cc; no driver voice bank is attached.
R9 candidate explicitly attaches bank ROB after native `02068904` audio setup,
only for driver37. Moves the two unique ROB BARS to standard audio directories
to retain the native bank-name parsing convention. Host binding test verifies
Morton is unchanged and ROB gets an additional bank. Revision
`race_voice_bank_binding` installed after user confirmed Cemu closure. Debug
helper PID39576 launched; read-only inspection confirms the R9 module is mapped.
Runtime playback remains unverified, awaiting the user's race test.
R9 race test still mute. Live actor4554FC98 now has six banks, including ROB:
the bank-binding correction works. Race event resolver uses the separate
`audio/bin/turbo_random_id.bsis` table, not direct BFSAR labels. Its thirty
`VOICE_*_MOR` groups had no ROB counterparts. Revision
`rob_race_reaction_groups` appends thirty ROB groups with rebased absolute
pointers, preserving all original groups/weights and existing vehicle additions.
All 77 referenced ROB labels verified in the installed BFSAR. Authored BARS
omit CAN/CAN_END; new cannon group reuses ROB DSH/DSH_END. Fifteen tests pass.
Installed with Cemu closed, relaunched debug helper PID22988; awaiting voice test.
User subsequently reported voice present, but ROB selected with Morton model
(screenshot shows correct ROB icon/name). Mario-to-ROB reselection does not fix
it. Source/installed private Morton.szs hashes match. R10 explicit final BFRES
path still showed Morton. Live descriptor23383DFC has character37, private
BFRES path, Morton internal model name at+7EC, and own audio paths. Log never
opens the private model archive, only driver/Morton.szs. Resource cache/name
collision is a hypothesis, not yet established as the cause.
R11 revision `unique_rob_model_resource` installed: explicit path ends ROB.bfres,
new private ROB.szs with root FRES resource name ROB; model/texture/animation
dictionaries and all original payload bytes preserved (only file size/root name
pointer change, independent name appended). Tests pass; helper PID21868 launched.
Awaiting user preview/race verification. Morton base archive remains untouched.
R11 user reports Morton in both preview and race. The identity/cache hypothesis
is still unconfirmed. DTOM row37 was cloned from Morton as [32,32,0,0]; native
model indices0..40 are already assigned across original male/female forms.
Revision `independent_rob_model_identity` changes only row37's two model bytes
to41, preserving all rig/stat/vehicle data and the original37 DTOM rows.
Sixteen tests pass. Installed with Cemu closed; helper PID39724 launched.
This new internal model index requires runtime validation; do not claim success
or include this experiment in a distribution before the user confirms it.
User confirmed the model finally appears with DTOM model41. Reports Morton
voice specifically in the menu; race voice identity is not yet confirmed.
Authored race bank has76/78 waveforms different from base; authored selection
waveform also differs. Decoded source selection to `work/rob/rob_authored_menu.wav`
and native comparison `morton_native_menu.wav`; user comparison pending.
R13 built, NOT installed: routes the four supplied ROB body textures through
private `kart/body_tex/` only in ROB recipe scope; other vehicle colors unchanged.
Chains existing vehicle icon hook02557754 for ROB-only body IDs0,1,14,23 and
their supplied loose icons. Tests cover donor/non-ROB scope, unsupported body
fallback, preservation of existing modded-part choices. Sixteen Python tests
and native host fixture pass. Pending Cemu closure for installation.
User compared the authored selection WAV and confirms the game plays a different
Morton selection voice. After Cemu closure, installed R13 colors/icons revision,
then R14 `rob_menu_voice_identity`: selection-voice routine020CC99C temporarily
uses driver37 when the per-player character-name selection state is ROB, restores
the actor's original driver afterward. Existing native voice routine handles
playback; telemetry records player, previous/used driver ID and ROB flag.
Host regression verifies ROB-only override/restoration and native Morton fallback.
Sixteen Python tests and host fixture pass. R14 boot debug PID30444 launched;
voice and vehicle-color runtime verification pending. Model41 DTOM remains active.

## R18 prepared: numeric audio bindings and correct icon argument

R17 live horn lookup comparison confirms the unmodified K_SKL event resolves to
a native SLink record, while new ROBTON events do not exist there. The loaded
menu bank registry does contain M_ROB; the menu requests pVO_M_ROB_SELECT_CHAR.
The BARS parameter table still had explicit donor sound IDs: its single menu
record stored0x1283, while the installed BFSAR maps ROB's menu label to0x12F1.
Renaming the parameter's string did not update this numeric binding.

`character_voice.bind_bar_ids` now validates the v0x54 BARS directory and rebinds
the low24 sound ID at each84-byte record+0x24 using the installed BFSAR. R18
preparation updates81 records across the two private banks; every waveform
member/name remains byte-identical. Private horn labels use existing MORTON
sample IDs, while the ROB-only native horn scope requests the existing MOR SLink
events; the attached ROB bank supplies the authored replacement samples.
No native Morton bank or global SLink file is changed. Runtime isolation still
needs testing alongside a real Morton.

Native02557754 receives r6 as pointer-to-driver-ID (confirmed by lwz r11,0(r6)).
The independent icon wrapper had compared the pointer value to37 and never
selected the authored black icons. It now dereferences the driver pointer,
selects the four existing black assets for body IDs0,1,14,23, and uses a donor
driver pointer for the unsupported-body fallback. Existing extra vehicles still
chain through the prior vehicle hook. Menu play hook now preserves native r3.

R18 RPX SHA2567d25569bb578a436f0d9c1167e109e5828315d9053bdcb2e3e1659930c91b6cf.
Seventeen Python tests and expanded host regression pass (all four icons,
driver pointer fallback, horn event scope, return values, sample preservation).
Assets staged under work/rob/audio_r18. Installer work/rob/install_r18.py prepared;
Cemu was observed closed after the closure request; guarded installer succeeded.
R18 installed as revision `rob_audio_record_binding_and_black_icons`, preserving
the original rollback. Debug helper PID23280 launched and read-only telemetry
confirmed R18 mapped, with no new captured boot exception. Awaiting the user's
menu voice / black roulette icons / race reactions and horn test. No runtime
audio/icon success claimed yet.

## R19 prepared after R18 feedback

User confirmed voice/black-icon improvements, but normal horn sounds like Morton
and some kart/glider roulette icons disappear. R18 horn telemetry now resolves
MOR_ON/OFF/ON_SP to valid SLink records (rather than the prior zero results).
Comparison against the supplied mod archive shows its normal ON and OFF wave
payloads are byte-identical to base Morton; only ON_SP is different.
`authored_normal_horn` reuses the authored ON_SP waveform and its playback
settings for normal ON, retaining the correct sound ID and filename; OFF is a
valid silent FWAV release so it cannot play Morton's release sample. Other voice
waveforms remain untouched. The staged release was decoded and verified all-zero
PCM. No global Morton asset is modified. Source custom horn waveform SHA256
7eb98b094d0e02771f826cc4e471947f12481afea58f9788755737afa0bd03a4.

The ROB wrapper now tries validated native resource filenames directly for
unsupported body/glider icons, while the four authored black icons retain
priority. `tools/native/rob_vehicle_icons.h` contains36 available stock body and
all14 glider resources, verified against current menu archive/base/update loose
assets. Absent B_Zlb and reserved K_A00/K_A01 retain prior native resolution;
existing added-part IDs39+ still chain through the vehicle module. No source
asset is invented or replaced. Only ROB uses the direct native fallbacks.

Nineteen Python tests and native host regression pass, including preservation of
voice payloads/sound IDs, silent release format and standard kart/glider fallback.
R19 RPX SHA256bdff76dec5712397c615814f4dfa46363c3e2ddc10e7cbd8e028905ec0a514a1.
Staged audio under work/rob/audio_r19; installer work/rob/install_r19.py prepared.
After the user confirmed Cemu closure, R19 installed successfully as revision
`rob_authored_horn_and_native_icon_fallbacks`, with original rollback preserved.
Debug helper PID7244 launched; telemetry confirms the new module is mapped and
no new boot exception was captured. Awaiting the user's horn and missing-icon
test; runtime results are not yet established.
VS CPU roster inclusion remains unimplemented. Validate cancellation/reselection, preview, normal
and modded vehicles, player R.O.B. racing alongside CPU Morton, CPU R.O.B., HUD,
results, sounds and animation fallbacks. Existing costumes must remain functional.
Only then install a reversible test candidate with Cemu closed. No online or
Aroma support is established by staging or host tests.
