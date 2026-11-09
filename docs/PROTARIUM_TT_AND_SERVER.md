# Protarium TT and dedicated matchmaking work

## Local server source

`E:/claude-code/protarium-mk8-server` contains the public Pretendo MK8 secure
server source plus the new `ctgp` package and `cmd/ctgp-local` integration service.
See its `PROTARIUM_CTGP.md` for exact endpoints, tests and remaining work.
The local service is not yet connected to the game. Docker Desktop was started,
with a dedicated MongoDB8.0 container on loopback27028 and a separate named volume.
The upstream NEX server was subsequently started via Start-NexLocal.ps1 and logged
PRUDP listening on127.0.0.1:60013. Its databases use the ctgp_*_local namespace.
Production accounts/configuration remain untouched. This does NOT prove a playable
NEX authenticated race; account/auth transport integration remains pending.

124 custom courses were exported from the isolated test pack by
`tools/server_catalog.py`. Moving a course between cup pages preserves its ID.
Updating its course/private objects changes its revision. Board identity is
`(track ID, revision, 150/200 cc, physics rules)`, shared by records and staff ghosts.
The next catalog now adds48 native courses (172 total). Their revision_basis is
game-version, explicitly a WiiU-v81 category identity rather than an asset checksum.
The active initial catalog remains124 until coordinated client/server activation.

`tools/native/tt_category.h` defines the client category/path contract, with host
tests separating two custom identities, 150/200 and pink/native physics, rejecting
unknown donors and preventing truncated paths. It is not hooked into record or
ranking lookups yet. server_catalog.py can generate the corresponding C table.

Public matchmaking admission is implemented in the local NEX source when
CTGP_CATALOG is set: it validates ctgp:1:<hash>:<rules> before database access and
partitions rooms by both hash/rules. Vanilla queries exclude modpack room records.
The game does not send that envelope yet, and private participation remains pending.
Next server sources support mixed mode CTGP_ALLOW_VANILLA=1, treating non-CTGP
requests as vanilla and rejecting malformed/mismatched CTGP requests. Public room
queries isolate both directions. Schema v2 boards include client family, with
transactional one-time migration preserving v1 source tables and staff links.
The authenticated adapter must select family; an untrusted claimed family is not
an anticheat. Native ranking handlers and game TT loaders are still not wired.

2026-11-06 P15: native ghost-menu bars are 10 mn_L_GhostVolume_00 controls, pic1
P_GhostVolume_00, original vertexRGBA0028B4FF. Runtime inspection verified Picture
vtable+44 points02696054, a bounded byte setter for pane+a8+index. P15 changes only
RGB through that native API during TT200, caches/restores originalRGB for150/off,
preservesalpha and size/UV/animation. Host test covers all10 and toggling/restoration.
Built/section-roundtrip checked; installed only in sandbox after user closedCemu,
PID33212 launched and cleanup helper registered. User later confirmed closing it
themselves; no new debugger exception. Visual confirmation of redbars is pending.

Red background P14 was initially absent because CTGP overrides mn_Background_00
from ctgp.szs, not just menu.szs. Both now contain the hidden redpane. User screenshot
confirms the background recolor is visible; request is to also recolor graphbars.

## Game-side status: not implemented yet

The native TT record tables, upload categories, downloaded ghosts and staff ghost
lookup still use donor official-course IDs. They must all be redirected together.
Do not claim the new server fixes those client lookups by itself. Existing personal
and Nintendo staff ghosts must remain intact, with vanilla categories unchanged.

The shared catalog needs an in-game lookup for the selected CUP0 course BEFORE
the course is loaded; relying on the last loaded `dlc_current_course` would use a
stale track on the ghost-selection screen. Track selection, race setup and replay
playback must retain the same category, including the physics option chosen when
the recording was made. Never replay a 150cc recording as a 200cc staff ghost.

Private-room page metadata is in `tools/native/online_sync.c`; worldwide native
selection still needs a global course identity and an identical catalog on peers.
An opaque per-race server selection alone does not update peer-to-peer race data.

## Staff ghost preparation

`tools/staff_ghosts.py` validates a player CTG0 header size/CRC32, removes only that
header for staff data and preserves all remaining recorded bytes. It stages a
manifest and private category directory; the game loader does not consume these
yet. Native course ID at payload+0x17c is recorded for diagnostics, not overwritten.
Category is asserted by the importer, not yet verified through native replay.

Example after recording an actual run in the intended category:

```
python tools/staff_ghosts.py --catalog E:/claude-code/protarium-mk8-server/config/ctgp-catalog.json --track ct.gu_bcp20 --cc 200 --name Friend --ghost ORIGINAL_GHOST.dat --content STAGING_CONTENT
```

Use the exact catalog ID and original `gs...dat` file. Do not use the example ID
without checking the catalog. The tool never edits a source save or game file.

File format research: https://github.com/Dinostraw/MK8Leaderboards/wiki/Ghost-Data-(Wii-U)
and https://github.com/Scutlet/mk8-poltergust (read-only reference, not bundled).
No reference source code was copied into the importer.

## Options persistence and TT red background

P13 runtime confirmation: SD ready=1, settings_loaded=1, reads=1, errors=0,
last_result=32, pink_enabled=1 on an untouched fresh menu. User confirmed ON.
Cemu rejects FSGetMountSource with END_ITERATION (-2) unless cos.xml filesystem
group 11 includes bit19 SDCARD_MOUNT. `tools/cemu_sd_permission.py` adds only that
bit in the isolated UPDATE cos.xml, backing up and replacing the directory entry
to avoid altering hardlinked originals. The main/base manifest was not edited.
Native SD write-after-change/restart still needs a full user roundtrip test.
Console-side Options persistence is not certified by this Cemu permission fix.

P14 adds a hidden red-gradient picture to native mn_Background_00 using the same
texture and material configuration as its blue picture. Native background calc
toggles only those panes during TT200, and Solo calc clears the TT scope. Native
drift/dash effects remain untouched: the third-tier P12/P13 mechanics still use
ordinary orange particles; pink particle visuals are unfinished.
P14 built with RPX section verification, only one UI layout changed, red pane
defaults hidden. Installed only in isolated test, PID43832; runtime result pending.
Prior RPX/menu backed up in workspace/work/pink_drift_p2/before_P14_20261105_225745.

Server local HTTP initial PID29092 at127.0.0.1:3088 has the catalog, boards and
random-course service; later staff version compiled as bin/ctgp-local-next.exe.
Automatic review rejected the grouped Stop-Process/restart command, so the initial
service remains running. All package tests passed, including staff categories.

## P16 live capture and P18 private ghost prototype (2026-11-06)

P16 live readback matched the user's accepted RMX Mario Circuit selection:
`ct.gu_bolt32`, page 3, slot 0, native donor 56, 200 cc, pink physics enabled.
This happens before entering the native ghost submenu. The saved readback is
workspace/work/pink_drift_p2/P16_selection_live.json. Ten TT graph panes were
also captured with the red scope active.

P18 is installed ONLY in the isolated Cemu update and launched under debugger
PID19616. Native runtime ghost routing is pending user verification. The build
roundtrip and host routing test passed: private account paths, original staff
table restoration, other-account isolation, filename generation, enumeration,
reload and deletion redirects. The test uses mocked SDK calls, so it does not
certify the SAVE SDK ABI or successful on-disk saving in Cemu.

Personal paths: custom/tt/v1/<id>/<revision>/<cc>/<n1-or-p1>/.
Staff content paths: custom/tt_staff/<id>/<revision>/<cc>/<n1-or-p1>/.
Compact rule tokens keep native 256-byte filename buffers within bounds;
manifest/server rule IDs remain explicit. P18_save_baseline.json stores hashes
of 21 isolated save files before the prototype launch. The RPX was backed up
before installation. No Wii U release ZIP was changed.

Online ranking transport and client admission handshake remain unfinished;
P18 is a local ghost experiment, not a completed online leaderboard client.

## P19–P21 local native-list prototype (2026-11-06)

P18 crashed at 025CAE28 copying an empty record: 024F0994/024F08F4 reset
metadata only and do not construct the filename SafeString. P19 copy-constructs
all private records with native 025CACA0 before resetting metadata. User confirmed
the Nintendo ghost disappeared. P19 then crashed on View Ghost with zero rows
(025876F4 through 025C7604), captured in P19_crash_empty_ghost_view.json.

P20 adds empty-list DECIDE guards and scopes EVERY 025C6584 rebuild, rather than
only the initial onIn call. It also captures the selected message IDs and copies
the selected course picture's native texture map for the Ghost footer. This footer
change still needs explicit visual confirmation. More Ghosts and Upload were
blocked from accessing donor ranking categories while transport was unfinished.
User APPROVED hiding Nintendo ghosts with pink physics; do not remove that rule.
Nintendo staff remain available only for native tracks, 150cc, native physics.
No official ghost files were deleted.

Local API now runs PID17428 at http://127.0.0.1:3090 using the 172-track catalog
and data/ctgp-cemu-local.db. It is separate from earlier prototype databases.
ctgp/native_ghost.go adds trusted native filename metadata and approved-only
public ghost manifest/download endpoints. Pending recordings are never published.
Go category/HTTP/store tests and native manifest publication tests passed.

P20 local adapter read the owned Cemu process and fetched RMX Mario Circuit 200cc
pink and then Mario Kart Stadium when the user changed selection. No guest RAM
writes, production network_services.xml changes or NEX authentication were used.
The development PID is explicitly 1, not an authenticated online identity.

P21 is compiled and installed ONLY in the isolated Cemu update. It intercepts
GhostScrollList (47) onIn/calc/event/exit to use the native controls with the local
cache instead of executing donor NEX ranking request states. The adapter writes
an atomic 4352-byte TTBL snapshot to Cemu's virtual SD: ctgp-local-board.bin.
The snapshot includes exact identity, revision, cc, physics and a checksum.
A Python-generated snapshot passed the native C ABI test; mismatched category
and corruption were rejected. Native UI runtime result is pending.

Active P21 debugger PID30548 (exec88212), cleanup session66416, adapter session61497.
Artifact: workspace/work/pink_drift_p2/Turbo_Options_P21_TT_LocalBoards.rpx (+json).
Status file: P21_local_server_status.json. API key is read from the server's local
config file only; never ship it in the modpack. Snapshot scores are read-only;
replays in approved manifests synchronize to the private category's dg cache.
Returning with B marks the private ghost cache for reload. No complete time-trial
save/upload/approval/download/playback roundtrip has yet been validated.

NEX account/secure-ticket authentication, public/private multiplayer room
integration, authenticated ranking transport and Wii U port remain unfinished.
P21 is a local Cemu development adapter, not a complete production game server.

P21 user reached the native More Ghosts list but B did not react. Investigation
showed 0253F8C4 simulates a focused-control decision; it is NOT a generic Back.
The traced native GhostScrollList return is W(page,0x80)=0x19 followed by
0253F048(page,page+0xD8). P22 uses that flow and accepts the native B action
0x33 without filtering out non-DECIDE input kinds. The host input test covers
key/touch kinds, unpressed input and inactive/native fallback. User approved
keeping Nintendo ghosts hidden when pink mini-turbo is ON.

P22 installed in isolated update and launched debugger PID21028, exec96787;
cleanup session29175; adapter session3777. Artifact Turbo_Options_P22_TT_LocalBoardsBack.rpx.
Status P22_local_server_status.json. B runtime confirmation is pending.
The Cemu process from P21 exited without a fresh debugger crash trace; do not
attribute that closure to a crash. Native More Ghosts uses original controls,
local read-only score rows, and an SD cache; per-row NEX download actions remain
disabled. The adapter synchronizes approved replay manifests into private dg files.
No real user recording has completed the end-to-end upload/approval/playback test.

P22 USER VALIDATED: Back/B now returns from More Ghosts to the native ghost menu.
Local adapter status currently receives Sydney Sprint (ct.gu_bcp13), 200cc,
pink rules. Awaiting the user's first completed <5min TT to verify native private
save generation and trusted local pending submission. No native per-row replay
playback has yet been validated. Keep the approved Nintendo ghost suppression
rule for CT/200/pink categories; do not restore Nintendo ghosts merely because
pink mode hides them. Native official 150cc with pink OFF uses the original staff.

## P23 save/upload/title investigation

User reported error 106-1203 on sending a ghost, and Mario Kart Stadium shown
as the title on every CT's More Ghosts screen. Pretendo's error-code reference
maps 106-1203 to DataStore::PermissionDenied:
https://nintendo-wiki.pretendo.network/docs/wiiu/error-codes.html
This means a native remote DataStore request was still reached, not that the
loopback HTTP API rejected the run. The exact triggering bypass was not captured
in live RAM because Cemu had already exited before inspection. User confirms
finishing a fresh TT in <5min, but no new gs file exists in either sandbox account.
The original sandbox gs files remain dated Nov5 or earlier; userdata.dat updated.

P23 adds native GhostScrollList title assignment from the accepted course capture
(control+0xAC name and +0xB0 prefix), on entry and calc. It also lazily reconstructs
the category ghost view before personal getter, filename generation, save entry,
Ghost events and online-list entry/calc if UI readiness was cleared. The persistent
selected category is now distinguished from temporary UI cache readiness.

Save diagnostics: tt_save_record_calls, tt_save_record_finished,
tt_save_name_calls, tt_save_name_scoped. Save entry 024F41C8 guarded original
9421FEB8, signature (manager,properties,mode), calls original unchanged after
preparing the private category view. No new cc-gate patch was guessed/applied.
Ghost native upload dialog callback 025C8CA0 (9421FF70) is scoped by the selected
TT category, intercepts the native remote flow, increments tt_native_uploads_blocked
and local refresh requests, and closes via traced native 0253FE60. It does not
claim successful upload; the local adapter must see a saved file first. Private
file submission stays pending on the server. Scope, input/title and Python naming
tests pass; live save/upload result still pending.

P23 installed only in isolated update; debugger PID7888 session92601, cleanup
session77977, local adapter session1034. Artifact Turbo_Options_P23_TT_SaveUploadTitle.rpx.
Status P23_local_server_status.json. Previous log archived as
P22_before_upload_fix_log.txt. User asked to check title then complete a TT and
leave Cemu at results BEFORE trying another send, so counters can identify the
remaining save failure. No new Wii U ZIP was produced.
