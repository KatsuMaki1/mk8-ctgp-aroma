# MK8DX 4.0.1 executable research and TT200 Cemu prototype

Work started 2026-11-01 from the user's readable exefs_patch.zip. No Nintendo
container decryption or console keys were used. Original main, main.npdm,
rtld, sdk, subsdk0 remain untouched in the Downloads archive. NSO segments
were decompressed and their declared segment hashes checked.

Private analysis root:
`C:/Users/evant/Documents/Codex/2026-10-25/files-mentioned-by-the-user-handoff/work/mk8dx_401`

Main build ID:158c0c7399aabd7bf83795c2ef3484c7 (remaining NSO build-ID bytes0).
Main text11,885,296 bytes; rodata6,645,134; data1,481,840.
The analysis-only ELF uses base7100000000, applies146,853 relative pointer
relocations, and includes BSS. Original executable bytes are not modified.
NSO/header/string/segment findings are in exefs_analysis/inspection.json.

The old local Ghidra installation was missing its launch files/application
metadata. A portable official12.1.2 archive was obtained and its GitHub release
SHA256 b62e81a0390618466c019c60d8c2f796ced2509c4c1aea4a37644a77272cf99d checked.
It lives under workspace work/analysis_tools. The existing RPX language plugin
was copied there; the previous Ghidra installation/project was not rewritten.
No installed tool or source code was uploaded.

## Confirmed executable/data findings

Key strings RouteChange, RouteChange_Obj, RouteChangeIdx, RouteChangeType and
RouteChangePtParam exist. A manual ADRP/ADD reference scan was necessary:
initial automatic string references were missing. Initial inferred function
boundaries were unreliable; the MOD0 eh_frame_hdr contains56,238 boundaries.
Use exefs_analysis/unwind_targets.tsv and dx_verified_functions.c, not the
earlier dx_manual_decompiled.c/dx_unwind_decompiled.c outputs.

Relevant verified ARM64 entry addresses:

| Address | Finding |
| --- | --- |
|710010AD8C|Parses RouteChange_Obj into a uint16 object-link array.|
|7100113248|Constructs/loads RouteChange groups and invokes object binding.|
|71008005B4|Reads RouteChangeType into a boolean at object+28.|
|71007E2354|Parses RouteChangeIdx data.|
|710080414C,7100806930|Read RouteChangePtParam.|
|7100389168|Uses distinct150/200 staff-ghost and time-attack progress keys.|
|71004CA81C|Creates the single-player mode buttons.|
|71004CC194|Creates cylinder-class selection including200cc.|
|710051D2E4|Binds TimeTrialChange UI animation.|

The supplied Wii U ports still contain RouteChange arrays in13 course folders,
plus route-index/path-point data. Inventory and example links are retained in
ported_route_fields.json and route_groups_inventory.json. Presence of a group
does not prove it is lap-triggered: lap/checkpoint transition logic, collision
state, object visibility, AI/item paths, respawns and multiplayer consistency
still need implementing/verification. Supplied Paris has no RouteChange array;
relevant readable RomFS course data would help restore missing source data.
No dynamic-route runtime patch has been installed.

## Wii U TT selector research

Native EUR81 code was read using the existing text.bin project. Native
references were located by PPC lis/addi pairs; Ghidra's old project did not
have useful direct string references.

| Address | Role |
| --- | --- |
|025E8114|ModeS event handler; confirmed TT event has index1/type2 and normally sets page+CC to37 (CharaS).|
|025E9EAC|Class page onIn.|
|025EA994|Class event handler; choices0/1/2/3/4 map50/100/150/Mirror/200.|
|global101D6944 ->+14C ->+180|Native engine class:0/1/2/3;200cc is3. Mirror is separate byte+184.|
|024F0A04|Loads personal ghost headers; uses prefixes gs/dg after initialization.|
|024F3B58|Builds gs/dg ghost filenames using course/driver/parts/time data.|
|024EECF8|Underlying ghost-list loader.|

These ghost/save findings are research only. Separate persistent200cc record
and ghost handling has NOT been implemented. Do not install the prototype
into the user's main game or ship an Aroma version yet.

## Sandbox prototype and state

tools/tt200.py appends three guarded hooks to the installed R3 RPX, preserving
existing modules. tools/native/tt200.c routes TT to native Class selection,
keeps only150/200 controls visible, then forwards native class-setting events.
It does not use speed multipliers. It has no confirmed race physics test yet.
Native host fixture tests mode routing, invalid choice rejection, native enum
selection and button visibility call arguments. RPX sections roundtrip checked.

Private prototype root is workspace work/tt200. It contains Turbo_TT200_P1.rpx,
sandbox.json, latest_state.json, debug_process.json, exception reports and mlc/.
The test MLC has copies of all MK8 saves and of update code/meta; its content
is a junction to existing content. No main RPX/content installation revision
was made. The original save hashes and original R3 RPX were checked unchanged.

Prototype first launch did not show the requested choice to the user. A
subsequent attempt reached Class but crashed: code passed a button to
02530D10, an animator API. Crash PC02530D10, LR02B32170 is saved as
first_class_page_crash.json. The call now uses02531BDC(control,pane,visible)
with button+50's pane instead. The native fixture checks these three args.

Current corrected candidate SHA256:
736e2ff863f94acad8521c8a26104ce588b6eb8c1f09bcf15caea576c18f4ef3

Corrected debug launch PID39808, executable Xapfish2.6, --mlc work/tt200/mlc.
Read-only guest marker inspection confirmed the prototype in memory; native
class initially2, selection counters initially0. No subsequent crash had been
captured when last checked. User confirmation of the class screen and race
remains pending. The choice is BEFORE characters, not in the ghost menu.
Computer Use showed a black fullscreen capture and could not activate it;
do not infer a freeze/crash from that capture alone (process/FPS remained live).

IMPORTANT cache cleanup: Cemu writes its global title_list_cache.xml even with
--mlc. Work/tt200_cleanup.py is running hidden as PID35016, waiting for the
owned test process39808 to exit. It then restores only the MK8 update cache
entry if it points into the sandbox, clears a sandbox-only mlc_path if saved,
restores the sandbox RPX to the original R3, and verifies original save hashes.
Report will be work/tt200/cleanup_report.json. This prevents a future normal
Cemu launch accidentally selecting the prototype with the main save.
Do not kill the user's Cemu session. Reinstall the candidate into the sandbox
only while Cemu is closed before another test; cleanup restores its RPX.

Next work: confirm selector/captured native engine class3 in an actual race;
finish a persistent200cc ghost/record namespace with correct cache refresh and
async-save behavior, then verify150cc data across mode switches and restart.
Only after that can this be treated as a main-profile feature. Dynamic routes
remain a separate port based on the analyzed data/control flow.

## 2026-11-01 follow-up
The corrected sandbox actually loaded after explicitly setting the MK8 update
entry in Cemu's title cache before launch. Clicking TT then crashed during
recursive UI animation traversal (guest frames 02698024/02697F60; invalid
virtual table pointer 0103A6D4). The visibility prototype incorrectly treated
UIControl+50 as a pane; writing pane+44 can corrupt unrelated UI structures.
Removed those visibility calls. Native host tests pass; candidate SHA256
ad6346823c3356d973b0673f27dd5ec51619b4608882f8efbdee544137914315.
Relaunched sandbox with this candidate, marker found in guest memory. The native
five-choice class UI remains visible for now; event filtering accepts only
150/200. Runtime confirmation still needed.

User supplied E:/mk8 Romfs.zip. Read-only ZIP inventory: 7719 entries,
12131696580 uncompressed bytes. Extracted only the 48 Cnsw course_muunt.byaml
files (29599948 bytes) to workspace work/mk8dx_romfs_routes. All48 little-endian
BYAML v1 metadata files parsed. Paris Cnsw_11 has RouteChangeType=1 and FIVE
RouteChange groups, unlike the supplied Wii U port's missing array. Full Paris
JSON and per-course inventory saved there. Source object indices must be mapped
to port objects; do not copy raw RouteChange_Obj indices into Wii U metadata.

## P2 staged, awaiting user closure
User confirmed selector works but all native classes show and 200 selection
races at150. Read-only state confirmed selected_class=3, native_engine_class=2,
game_mode=1. New candidate Turbo_TT200_P2.rpx is staged, NOT installed.
Adds guarded 024F9F0C race-settings-copy wrapper (mflr original verified),
post-copy class override only when choosing_tt and destination+17C==1.
Runtime hit counter tt200_race_copy_count records whether this path was used;
this is a hypothesis to verify, NOT a confirmed fix to the resetting caller.
UI root pane is control+50 -> layout+0C (confirmed native02531718), not+50
itself. P2 applies visibility to that actual pane and restores visibility when
outside TT. Host tests verify both class filtering and mode-gated copies.

Toad Harbor missing ramp: native Gu_City course data/object5276 definition is
unchanged, but global mapobj/CiJump model AND collision differ from base:
base BFRES412928 bytes vs installed229632; base KCL516 vs installed44420.
Cemu log confirms this modified global asset is loaded in Gu_City.
P2 chains tools/toad_harbor_assets.py native formatter wrapper, redirects only
Gu_City's CiJump directory/files to custom/vanilla/mapobj/CiJump. Original
model/collision staged in tt200/toad_harbor_stage; global modified assets stay
intact for CTs. Host test verifies directory/file routes and course isolation.
P2 combined RPX SHA256:
59d2bf4be5a3cc05877ae7a1e0f8201ac7dbbf8b6b81a95fcffb5c4a7aa541dd
TT symbols are in P2_core.rpx.json, scope symbols in P2.rpx.json. Update the
P1 candidate/manifest compatibility files for debug/read/cleanup scripts only
AFTER Cemu closes and previous cleanup exits. Last running PID24216.
Do not use P2 global main save: TT namespace separation still unimplemented.

## P3 exact TT setup store
P2 still raced150; selected_class3/nativeclass2/copycounter0 confirmed in memory.
Decompiled0261687C TT setup: hardcoded150 store at02616A78 is
stw r31,0x164(r26), where r26=config+1C andr31=2. P3 replaces this guarded
instruction with an assembly gateway, usesselected_class only whenchoosing_tt,
preserves r0,r12,CR,LR/XER and stack, returns02616A7C. A hit flag
(tt200_rule_store_count) proves execution. Verified emitted PPC instructions,
branch target and RPX roundtrip. Installed P3 in sandbox only after closure.
Combined RPX SHA1b000f21ab9729b719954d66cc33fc31e26506d33f8aa9222d448d0fe37416ea.
No actual200physics confirmation yet; persistent records remain unseparated.

## P4 menu polish staged
User confirmed actual200cc works withP3. Preserve exact TT engine-store fix.
Live UI inspection revealed Mirror reappears because native animations restore
visibility after onIn. Read-only Class page located at UI page list index30;
button+50 -> layout+0C root pane -> parent+0C per-choice anchor. NW pane
translationY is+20 (X+1C), native+44 isvisibility. P4 adds classonCalc025EA5B0
(mflr verified), reapplies visibility to roots AND unique choice parents each
frame. Moves150/200 parentY by+60/+140 nativeUIunits; caches/restores original
coordinates to prevent drift across repeated entry/GP. Originalpositions are
restored before onIn, and all class panes shown for GP;200unlock override now
restricted toTT only (earlier code unintentionally applied inGP).
Cursor hover on hidden0/1/3 skips to opposite visible choice, retaining native
150/200 indexes and help preview behavior. Back/reentry retains selectedclass.
Host tests cover repeatedentry no coordinate accumulation, hiddenhover skip,
GPvisibility restoration and native class selection. Built/roundtrip verified:
Turbo_TT200_P4.rpx SHA256
c477afd7ba55398ac1b1d8c15a81e6e02670ad1fccb18325371314fb09d9987f.
NOT INSTALLED: waiting for user's Cemu closure confirmation. Need inspect visual
result after install. P4core.json holdsTTsymbols; combinedRPXincludesToadscope.

## Aroma full experimental port 2026-11-01
User requested full Wii U ZIP including Aroma/CafeLoader and retaining DSI.
New tools/rpx_to_aroma.py exports full P4 Cemu payload to console codeF800000,
data10400020. Maps all153 native text/rodata modifications against stockRPX,
rebases function/constant table pointers, lis consumers and CFG branch targets.
CFG follows conditional LR fallthrough, seeds native prologues, pointer tables
and address-loading thunks; ASCII string seeds excluded. Strict ambiguous-lis
and unknown executable-branch checks stop generation. Audit is in Features.json.
Compared original CTGP first7800bytes to previous known-console SD pack: exact
match except4 intentional later runtime hook branches (3F1C/5758/5F48/6A00).
All153 Patches/Verify addresses paired; privatecup0 path checked. TT assembly
return resolves to console0E796A7C (02616A7C+0C180000). Plugin compiled using
EXTRA_CFLAGS=-DCTGP_CRASH_CAPTURE; ELF confirms v0.20 resource-trace/DSI strings.
This is static validation, NOT real console success. User must test realWiiU.

Full content ZIP built by work/package_aroma_tt200.py, onlysd/ atZIProot;
2981files before manifest,8070597490bytes uncompressed. Includes currentCemu
content (not accounts/saves/RPX), allBooster48R3/ROB19 andP4/Toadscope. Source
content data.cup0 copied also as custom/cup0. DSIfullscreen remainsenabled.
Readme explicitly says150/200 persistent ghosts/records are not separated,
backupsave first, dynamicDXroutes andROB-CPU remain unimplemented, online
issue unresolved. No claim of console-tested P4. Output verification report
will be outputs/WiiU/CTGP_Aroma_TT200_P4_verification.json afterZIPCRC/hash.

## First console crash: Wii Rainbow Road 200cc
User reports launchcrash onBoosterWiiRainbowRoad (Gu_Bcp48), only200tested.
DSI PC0E8C7660 LR0E64D1DC DAR4 DSISR40000000; R18/R25zero R281F6AFB18.
CALL0E5BE0CC/0E641324/0E8C124/0E8CCFCC. Correct GT rebasing:
PC02747660,LR024CD1DC,caller0243E0CC,then024C1324 (do not miscalculatePC).
PCis lwz r3,4(r3) inside02747644 dispatch helper, R3null. Caller024CD1B0
receives heap/resource pointer asarg3, calls helper forsize thenheapallocate.
Its caller0243DFD8 passes resource-holder+3D28, which isnull. Need determine
why underlying resourceheap creationfailed; OOM is hypothesis, NOT proven.
course_muunt_200 exists628084bytes/179objects;150samecount butdiffdata. Model
Yaz0 expands55,108,184bytes; archive21,707,698. Not unusuallylargest Booster.
Decompilation notes work/wiiu_rainbow_heap_crash.c/resources.c/resource_names.c.
User pending test: WiiRainbow150 andofficialChampidrome200 to isolate trackvsTT.

Built diagnostic-only Aroma v0.21-heap-trace, retainsDSI andaddsR3-R6/R27/R30,
validated guardedreadonly holder+3D1C/+3D28 for this exactPC. No allocatorcalls
inexceptionhandler. ZIP outputs/WiiU/Mises_a_jour/WiiU_DSI_Heap_Diagnostic_v021.zip
87739bytes CRCpassed. NOT a crashfix, noCafeLoaderchanges, noCemuinstallation.
Original fullP4ZIP remains immutable withv0.20; pluginbuilddirectory nowv0.21.

## Aroma v0.22 DLC slot redirection fix
User reports all imported tracks backed by native WiiU DLC slots crash, same
PC0E8C7660 witholdv0.20 plugin. Found concrete plugin omission: addLayers only
registered /vol/content/<dir>; no /vol/aoc0005000c1010ed00 layers. DLC course
requests can therefore miss SD custom content. Patched addLayers to register
MERGE_DIRECTORY for BOTH content and region-derivedAOC path, sameSDdirectory.
No root/singlefile layer and no license/unlock logic added. g_layers enlarged
from17 to33; all16 directories nowhaveup to32 layers; skipflagsapplyboth.
Read only existingSDdir via nativeexists; absentSDfilesfall backtonativeAOC.
Plugin v0.22-dlc-layers keeps DSI/ISI/PROGRAM andv0.21 extraheapregistertrace.
Host harness work/plugin_layers_host.cpp tests actual extracted addLayers
function withmockAPI: EUR/USA/JPN expected32target/sourcepairs, handlebounds,
skip_audio suppressesboth=>30. Passed. WiiU pluginbuildpassed.
ZIP outputs/WiiU/Mises_a_jour/WiiU_DLC_Slots_Fix_v022.zip 88207bytes,
SHA256dd6a9cfae9e446f9e38fd99599936e1bd9f8ffd29f4cf4a4a4a61bc19addcbea,
CRCpassed/embeddedpluginbyteexact. ContainsONLYsd/plugin+readme; overlaysfullP4.
Full6GBP4ZIP remainsimmutablewitholdv0.20. Do notclaimconsolecrashfixed until
usertestsV022, ideallyWiiRainbow150/200. Newexpectedstage layers32 ifallSDdirs.

## v0.22 REGRESSION - WITHDRAWN
User confirms previously unlocked owned DLC relocked specifically afterv0.22.
Do NOT recommend v0.22 or put it in a new fullpack. AOC-wide directory merging
was too broad and regressed DLC detection. Exact detection failure unproven.
Reverted addLayers to16content-only merges; removedAOC construction, original
17handlearray restored. v0.23-aoc-rollback retainsDSI and extraheaptrace.
Build passed; hostharness confirms16 /vol/contenttargets, zeroAOCtargets,
skip_audio=>15. ZIP WiiU_DLC_Restore_v023.zip87975bytes CRC/bytecheckpassed,
SHA256618707bb630e986ff5543ff52a4f5e41565a4e7791133e6f4214625117d8a6c3.
Requiresfullpowercycle to discardoldlayers. Does NOT changeanytickets/saves/DLC
installation. This rollsbackregression; originalDLC-slot CT crash NOT fixed.
Awaituserconfirmation purchasedDLCvisibleagain. Nextfix must preserve native
AOC detection and scope runtime customfileloading; do notoverlaysharedAOCdirs.

## v0.24 scoped custom paths, awaiting console test
User confirms v0.23 restored ownedDLC. Keep content-only16layers, noAOC overlays.
Newnative dlc_custom_paths.c chains3existing formatters and postprocesses their
mutable BufferedSafeString output. Exact /vol/aoc0005000c1010e[bcd]00/ prefix
changes to shorter /vol/content/ only for3712allowlisted paths fromcurrentSD.
124CUP0customcoursefolders, no base-folder overlap; course/privatecustom paths
alwayseligible, sharedmapobj/audio onlywhile listedcustomcourseactive. A
subsequent nativecoursepath clearsactive flag. No data/UI/license pathrewrite.
Native formatters confirmed0272C02C buildsdevice+54/root +relativepath;
0272C8FC copiesintoBufferedSafeString capacity+8. Rewrites shorteninplace.
Hosttests tests/dlc_custom_paths_host.c coverthree regions, WiiRainbow200 path,
privateVRCnsw68, nativeDu_BigBlue passthrough, data/UI unchanged, traversal
rejection, sharedaudio gated bycustomcourse. Passed with generated3712header.

Candidatework/dlc_paths/Turbo_Custom_AOC.rpx chainsfromP4; notinstalledinCemu.
Console exportstill153nativepatches; additionalmodulecodeappended. Exporter
acceptsexplicitnoncode rangefrommodule_restgpr31end throughconsttables, avoids
interpretingFNVtablehashes/stringpointer targets asinstructions. Also adds
nonpointer_words: preserveallFNVhashwords(1502Booster+4Toad+3712new=5218), while
rebasingonlytheir stringpointers. Verifiedallsamehashbytesafterport; generic
word-pointer heuristic must NOT retarget numericFNV hashes inlegacyP4export.
NewfullP4zip remainsimmutable; v024codepackfixespreservedhashes too.

Pluginv0.24-custom-paths has v023FS logic unchanged, updatedDSIversionlabel.
SmallZIP outputs/WiiU/Mises_a_jour/WiiU_Custom_DLC_Paths_v024.zip244066bytes,
SHA256f2f917f2791b766270fa6ebd3f35d103579d0d1e5c9b79e80cc17e113b18f206.
Containsall6CafeLoadercodefiles+plugin+readme, noassets. CRC/hashesvalidated.
RequiresfullP4content; fullpowercycle. No mainprofilechanges. Console outcome
NOTconfirmed: testownedDLCstillavailable, thenWiiRainbow150/200. Ifnotfixed,
v024DSIheapregisters helpidentifylower-level path/deviceboundrouting issue.

## v024 unchanged crash, v025 direct FS routing + trace
User screenshotv024: samePC0E8C7660 LR0E64D1DC DAR4. R3=0,R4=12E942E4,
R5=0,R6=00021BBA,R27=1F6ABC48,R30=1F6AFD28. Holder+3D1C=1F6E4794,
+3D28=0. So holder'sheap exists but resource pointer null; not proof ofOOM.
Formatter-onlyrewrite didnotresolve. Need actualFSrequest/failedresource trace.

Pluginv025 adds dlc_fs.cpp with6WUPS coreinit FS hooks: OpenFile,GetStat,OpenDir
andAsync counterparts. Same3712allowlist fromv024 compilednativelyintoWPS
(no rawhashrelocation). Prefix rewriteonlyAOCcustompaths to/content, shared
mapobj/audio gatedbycustomcourse. NoAOC layers,16contentlayersunchanged.
EnabledONLYafterloadCode success, resetonappstart/offonappend. NoFS/heap/log
callsfromhooks, noformatloggingrecursion; stack512pathbuffer shrinksroots.
AsyncSDK call marshalscommandpathduringcall; no customasynccompletionwrapper.
Tracks lasteligiblepath, lastimmediatenegativestatus/path, redirects counter.
DSIprintsFSredirects/status/last/failed. Failedprobe mayoptional; asyncstatus
is submission status, notcompletion. Hostharnesswork/plugin_fs_paths_host.cpp
usesactualnamespacelogic, checksdisabledgate,custom200route,privateassets,
nativeDLCcourse/data/UIpassthrough, sharedassetgate, errorrecord. Passed.
BuildpassedwithDSIenabled. MakefileINCLUDES now source include. Generated
plugin/include/dlc_asset_list.h contains pathlist, no credentials or secrets.
ZIP WiiU_Custom_DLC_FS_v025.zip containsplugin+readmeONLY;keepv024CafeLoader.
Consolefixstillunconfirmed; needuserreproduce/completev025DSIifstillfails.

## v025 precise failure -> v026 content-index handling
Userv025DSI samePC; FSredirects=0,FSstatusFFFFFFFA=-6=FS_STATUS_NOT_FOUND.
FSlast andFSfailed EXACT /vol/aoc0005000c1010ed00/0019/course/Gu_Bcp48/course.bglpbd.
This explains failedallowlisting: previousrelativepath included0019/ prefix.
FullP4ZIP verifiedcontains course/Gu_Bcp48/course.bglpbd8321344bytes.
Pluginv026 strips optionalONE fourhex-digit content-index segment before
allowlistlookup, redirectsindexedcustomcoursepath to /vol/content/course/...
NoAOC layers/no ticketedits. Samefix in native/dlc_custom_paths.c forfuturebuild;
CafeLoaderv024needNOTchange becauseFSpluginseesfinalpath andrewrites.
Hosttests exact0019path, indexnativeDu_BigBluepass, indexeddataunchanged,
shortstringbounds, unindexedpaths allpassed. WiiUplugincompilepassed.
ZIP WiiU_Custom_DLC_Index_Fix_v026.zip150855bytes,
SHA2565d9b43f1276e18cc730614c728cc5960d978e0fccac71f5f1763a7ace1b74639,
CRC/embeddedpluginverified. Consoleconfirmationstillpending. Versionlabelv026,
DSI+FS tracesretained. RequiresP4fullcontent+v024CafeLoadercode, replacesplugin.

## New v026 Worldwide vanilla-track crash
User playing Worldwide vanilla tracks withOnlineCTGPON; ONdoesnotexposeCTs inWW.
NewDSI PC0E9D2BC0 LR0E3D61E0 DAR20 DSISR40000000; calls0E3D61E0,
0E40B2EC,0E48FB34,0E3D81D8,0E447050,0E5A7D0C,0E5A7B88,0E67A8A8.
FSredirects45(0x45), FSstatus-6; lastfailed/UI ef/a_race/timg/tc_RT_Finish_ef^h.bflim.
Do NOTattributecause tothisoptionaltextureprobe withoutproof.
CorrectPCrebasing02852BC0: lwz r0,20(r3),r3null, model-group lookup02852BB0.
Caller022561A4 loadsactor+224 andlooksfor'DL_TicketGateBar', thenBarLeft_root/
BarRight_root. ThisisnativeTicketGate actor associatedwithDu_Metro/SuperBell.
BothoriginalDLCBFRES andprivateBCPBFRES have two models Gate+GateBar; no proof
filemissing. NativeDu_Metro has4 object4106 andMapObjResListDL_TicketGate.
Currentobjflow4106fromBooster source ResNameGate; originalbaseobjflowlacksDLC
IDs, no pristineupdateobjflowfound. Do NOTblindlychangeResName/nullguard.
Artifacts work/ww_v026_crash.c, work/ticket_gate_load.c (proper022561A4 entry;
earlier022561BC decomp waswrongmidfunction),originalDLCbackup0019 accessible.

Online_sync.c explicitlyprivate-room implementation; ONalone isnot aWorldwide
custom-course vote/compatibilityimplementation. WWsessiongating notyetfinished.
Possible staleper-course assetrouting (routers recognizecourse/ butindexedDLC
paths maynotresetactive) remainsHYPOTHESIS, notverified. User pendingmapname.

DIAGNOSTIC pluginv027 preservesv026routing/all16contentlayers; adds lastobserved
course andTicketGateBFRES paths +actorMainModel/GateBar pointers onexactPC.
FS policyhosttests rerunpass/buildpass. NoCafeLoaderchanges orruntimefixclaimed.
ZIP WiiU_WW_Object_Diagnostic_v027.zip152886bytes SHA256
f1fb8e1b455080fd50720650bb213e72385b56f2689b104345392df5c691ccc2 CRCpassed.
Requestsuserfullv027capture andcomparison samevanillatrack offline/WWtoggleOFF.
Pluginbuildfolder NOWv027diagnostic, NOTnewstable. Fullv026ZIPunchanged; future
fullpackmustuseexactknownv026unlessv027requested orvalidated. Do notpackage
anunverifieddiagnosticbyaccident. Userstillneedsactualcrashfix.

## Friend's v026 crash: native character sound-group table
Newimage PC0E7F6E30 LR0E7F6E2C DAR0; CALL0E1AC5FC,0E7982B4,0E73A374,
0E73C2EC,0E6BF250,0F804C50,0E6BA984,0E6B9DE8. LastFSnotfoundWing_Std_A_Spm
is OPTIONAL AOC probe; originalbasefileexists137476bytes, notprovenrootcause.
PC02676E30 lbz r5,0(r6), whereSafeStringtextnull. Caller0202C438 has37-entry
native driver sound-group loop andselectedIDlookup allows0..36. ID37 gives
null label. Native stringtable10180B58 listsInvalid,Mario,...Morton,...AnimalGirlA
with38stringsinclInvalid. CurrentROB37 remains outside. Decompwork/online_audio_null.c.
Pendinguserfriendcharacter/mode clarification; ID37 plausible butnotconfirmed
by registers/selection inthisphoto. Do not claim sameTicketGate crash.

Added tools/rob_audio_groups.py +native/rob_audio_groups.c. Guarded hook0202C438
originalmflr7C0802A6, callsoriginal withlocaldonor28 ONLYifselectedID37. Native
37soundgroups staywithinbounds; actualROB ID/model/stats/privatebank notchanged.
Hosttestall37originalIDs pass unchanged,ROB aliases28 andcallerIDremains37,
returnvaluepreserved. Built candidate work/rob_audio_groups/Turbo_Audio_Groups.rpx
fromv024dlc_custom_paths candidate; noCemuinstallation. Export154pairedhooks,
retainsallv024routing/P4/Toad/ROB hooks;explicitFNVhashwordprotection/noncodeconst
range ends atoldmoduleend so appendedaudiohook iscorrectlyrelocated.

ZIP WiiU_ROB_Audio_Group_Fix_R20.zip156771bytes SHA256
a1b62ede79d36d350b6110995c73c432254a09d23e096f1d0019b23819a95026.
Only6CafeLoadercodefiles+readme, preserveuserworkingv026orv027diagnosticplugin
andone-pageCUP0. ZIPCRC/codehashchecks passed; console/runtimeconfirmationpending.
This fixesanidentifiedunsupportedIDpath, NOTconfirmedfriendcause untilretest.
OriginalfullZIPimmutable; nextfullpack must consciously includeR20aftervalidation.
