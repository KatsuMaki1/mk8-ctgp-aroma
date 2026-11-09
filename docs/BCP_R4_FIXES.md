# Booster R4 / Aroma v0.28 â€” 2026-11-03

This is an incremental patch project. The immutable full v0.26 ZIP remains the required base. Main Cemu content, RPX and saves have not been installed over. Tests use work/bcp_r4_test in the C: workspace, with independent content files for every change and a copied save.

## Verified changes

The internal Cnsw IDs do NOT follow release cup order. tools/booster_mapping.py now uses an explicit 48-ID permutation. The 44 supplied previews were independently decoded and compared against the owned Switch RomFS DLC01..48 BNTX images; corrected ordering matches, maximum RGB MSE125.48 (BC1 versus BC7 encoding). R4 existing-directory metadata and donor music are staged by work/fix_booster_r4.py. Both CUP0 copies also retain Bolt one-page consolidation.

44 models were optimized using the prior R2 texture profile. Every BFRES was reloaded and verified for unchanged vertices, indices and material/resource keys, and exact prepared mip data. Geometry/collision/routes are unchanged. Aggregate texture byte reduction1608.1MiB (72%). This is NOT a Wii U FPS measurement or a claim that 3DS Rainbow Road graphics are fixed. Separate optional model ZIP907580200bytes, SHA256 bba4c08b422ba2d3fae07d1835171617756afe10c16e4a287d8733c601711711, CRC passed.

FS policy now includes exact locally-present base mapobj paths and resolves raw BCP mapobj paths into the existing private overlay even when an indexed AOC path bypassed earlier native routers. Only16 content layers; no AOC directory layers or ownership rewrites. Both native final-path logic and plugin have host tests. Native outer formatter normalizes original SafeString before passing it through older Dark Sanctuary/Bolt routers, preventing BufferedSafeString vtables on eight-byte temporaries. R20 ROB audio-group adapter is retained; VS result pending.

## Maple crash and Wiggler validation

Cemu reproduced the console PC02863E4C null animation-controller crash. Actor vtable1004B40C belongs to DL_WdBird. Global ObjId1170 retains legacy ResName Bird; BCP requires DL_WdBird. tools/booster_object_alias.py allocates unused ObjId9050 with MgrId1170 and the correct resource, preserving the legacy definition. Only BCP Maple 150/200 object IDs and MapObjIdList change. User confirmed the race starts.

The two Wiggler groups use separate head/body actors1192/9018/9019 and routes18..27. Source loops diverged in their phases, and the second group shared identical body start points. tools/maple_wigglers.py resamples each head loop into256 equally spaced points, then rotates the identical closed point sequence for each segment using the original actor offsets. All actors share speed, and control points remain in world coordinates (source path18 had inconsistent Y). User confirmed BOTH groups work correctly over the loop in Cemu. Candidate files were promoted to R4 stage, not main content.

## Race intro banner

Native call sites026273E4 and02627404 call025367E8 for course and series labels. tools/course_intro.py appends a wrapper which matches the loaded directory against CUP0 records (0x54stride, dirs+34, name message IDs+14, tag IDs+24). These are registered message IDs, NOT UTF16 pointers. Loaded directory is tracked by the final native formatter at dlc_current_course. Stock/unmatched courses preserve original messages. Host tests and guarded build pass; user visual confirmation pending.

Final candidate: workspace/work/booster_pass_20261031/r4/Turbo_BCP_R4_Intro.rpx, SHA25619d36c918c07b66e65c036d6dbdd4c6852223358ce395dcb5da35dfe9d11fc62. Export has156 paired patches/verify sites and10275 protected FNV words. Both const-table regions are excluded from instruction discovery. work/export_bcp_r4.py is the current exporter invocation.

## Open Sky-High Sundae test

After missing base-object fallback was repaired, a different Cemu crash occurs at024E5F20 (PPC block024E5E44), LR024E7234, DAR10, while opening private DL_CmnAnimalC1.bfres. The resource/cache lookup returns null. The source archive contains main and *1 BFRES files declaring identical root/model names for AnimalA/B/C. The final file gets statted then closed without a data read. Duplicated registry identity / memory pressure is under investigation; do NOT assert ROB is the cause.

A TEST candidate replaces ONLY the three redundant *1 files with valid140-byte empty BFRES resources, each with its own unused name. Primary models remain unchanged. This supports drag/drop updates without requiring deletion of existing SD files. Candidate is under r4/duplicate_candidate and installed ONLY in isolated Cemu; not promoted to r4/content yet. User retry pending. Original crash JSON/log preserved as sundae_crash_before_duplicates.*. Other duplicated source files were audited but NOT changed (AnimalBalloon, NkGate, Tambourin, VR26/44/68). No general null bypass was added.

## Cemu DLC test setup

Original main DLC folder exists as 1010ed00.backup. Initial isolated MLC had no DLC. Mounting the backup exposed an existing title.tik whose AOC rights still locked courses. Isolated test DLC now has copied code/meta and a read-only-use content junction, without copying that ticket. Cemu native no-ticket fallback enables local tests. Original ticket is untouched. NO ticket/account/key/save/DLC-ownership workaround is included in console packages. Current cleanup restores all test cache paths after owned process exit; original save hashes are checked. Earlier cleanup jobs may only restore update entry, so ensure final cleanup runs when the last owned Cemu session ends.

## Packaging

work/package_bcp_r4.py models produced the optional907.6MB ZIP in outputs/WiiU/Mises_a_jour. core has NOT been packaged yet: wait for Sundae/ROB and banner results, promote only confirmed candidate files, update runtime_validation.json, then run core. Core compares staged content against unchanged main content and includes only differing files, the six CafeLoader files and v0.28 plugin. No full pack or Cemu RPX. Other console crashes (Merry/TicketGate etc.) remain unconfirmed on the new routing; do not claim all48 tracks certified.


### Follow-up: Sundae reached actor creation, then missing manager1140

The three140-byte duplicate candidates got past the previous resource-loading failure. A later user crash occurred after the debugger600s window expired; normal Cemu log preserved it: IP021FE800, LR021FE9F8, r3=0, stack0228B2EC/0230FB34/022C705C. Native021FE9C4 asks GetManager(1140), then uses the shared transform pool. Sky's normal muunt has AnimalA/B/C1137/1138/1139 but omits1140; the200cc muunt instead uses CmnSit spectators1203/1204/1205 and needs no Animal dependency change.

Native manager constructor021FF1B0 explicitly sums actor counts in managers1137/1138/1139/1140 and allocates the shared transform pool. Therefore declaring1140 with zero visible D actors is appropriate; no new visible spectators are spawned. Its resource is already present in the private overlay. tools/animal_dependencies.py adds1140 to MapObjIdList and DL_CmnAnimalD to MapObjResList only when needed.

Important: source Sky has version1 A1 opaque path references. Never serialize the entire file with byml_dump.build. New tools/byml_edit.py preserves original root/key/path data and patches root array pointers in place, appending arrays plus an index-preserving string table. Three tests cover dependency, idempotence and an opaque A1 reference. Preparation passes on actual normal/200 files. Candidate lives r4/animal_manager_candidate; installed ONLY in isolated Cemu. Neither this nor duplicate candidates promoted to the distributable stage yet; await user race result.

Two failed preparation commands accidentally launched unpatched test processes; these agent-started boot sessions were closed immediately, and the user was explicitly told those closures were ours. Main Sky150/200 content verified byte-identical to the immutable full v026 ZIP; original save unchanged. Future shell launch steps must stop on Python failure. Latest successfully prepared session PID34296, debugger executable Python314, cleanup job active. It includes current Intro RPX, validated Wiggler paths, duplicate candidates and the normal-muunt1140 dependency. User has been asked to repeat Sky with ROB. User confirmation of intro names remains pending. Core ZIP still NOT produced.

### Nov 3 follow-up: null Coin manager after malformed table relocation
The latest Mario and stock-Jugem tests both crash at022B2DBC through020F9640. Correction to earlier interpretation: actor+1C4 is NOT Countdown. Native020F8C14 copies global10188534+5C, which022C569C initializes from GetManager(1018), the Coin manager. Logs show zero mapobj resources opened after the modified muunt. animal_dependencies had appended a new string table after the root, violating native layout assumptions. Python structural parsing alone did not detect it. Removed unnecessary DL_CmnAnimalD resource insertion: only MapObjIdList1140 is patched now; all header key/string/path/root pointers remain byte-identical, opaque A1 refs intact. Three tests pass with header preservation assertion. Installed from original main Sky files into isolated copy, restored original modded Jugem (stock experiment ruled out that file), launched PID10060 with cleanup/debugger. Await Mario Sky VS validation. No distributable stage promotion yet.

Header-preserving test restored mapobj loading (confirmed Coin/Patapata/Animal resources) but still crashes021FE800: declaring1140 without actors does not create its manager. animal_dependencies alone is NOT a complete fix. New isolated diagnostic removes only11 incompatible AnimalA/B/C spectators from normal Sky, preserving all other actors/opaque paths/table pointers. 200 file retains its204 actors (uses different CmnSit spectator types). tools/sundae_spectators.py filters raw Obj pointer array, validates full parsed equality against expected, header preservation, and idempotence on real files. TestPID40660, cleanup running; awaiting Mario retry. No stage/coreZIP promotion.

USER CONFIRMED Sky-High Sundae now works after the11 incompatible Animal Crossing spectators were removed (normal muunt193 remaining actors;200 retains204). Promoted isolated normal/200 muunt plus three required empty duplicate BFRES replacements to r4/content. Cemu Mario confirmation only; ROB VS and console still need validation. runtime_validation.json updated. Keep this workaround explicit: spectators removed, not their native manager fixed. Do not promote animal_dependencies-only candidate.


## Wii U incremental test ZIP, Nov3
Current CountryP1 RPX5fa6d45b881a9fb82c505473ba29364939a02892ada10b3ee69e148590b4995a exported by work/export_wiiu_options_r4.py:160 paired hooks,10275 protected hashes, options constants excluded from CFG.13 country table IDs/name pointers, speedometer default and Addr header checked. Plugin v028 contains DSI capture. FooterR5 menu included.
Archive CTGP_WiiU_MAJ_R4_Options_Pays_TEST_2026-11-03.zip:37015603bytes; SHA256883ad67d5cba1039d2e8cd33e4ee368047f37a2ae621c1fc86833f7b3a531b13;57files; CRC and manifest hashes verified. Only sd root. No accounts/network XML/keys/saves/tickets/RPX. Requires existing full v026. Optional optimized models separate. README labels console and country online validation pending, session-only country, TT records not separated; DSI retained.
