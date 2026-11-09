# Wii U optimization R3 / cumulative update R7 (2026-11-04)

User baseline: CTGP_WiiU_MINI_Pays_P2_MusiqueMenu_2026-11-04.zip on existing full EUR v81 pack.

124 selectable custom courses audited. 122 safely reducible course models rebuilt and reloaded; DS Rainbow Road Gu_Bolt42 (nonstandard signatures) and SMW Raceway Gu_Bolt47 preserved. Course texture data reduced by 950646784 bytes; ordinary scenery pass removed 974750 triangles. Additional dense scenery pass neutralized 533522 nondegenerate triangles across 15 courses, retaining draw counts, offsets, submesh bounds and lower LODs. All 122 rebuilt course models were checked again with the stronger lower-LOD verifier; no inputs rejected. These are static asset savings, not measured GPU workload or FPS gains.

106/110 unique large private objects/sky models texture-optimized, saving 491641344 bytes across unique files; their vertices and indices are untouched. General/detail cap256, readable road/sign/lightmap cap512; formats retained. Collisions/checkpoints/route files are not changed by this optimization pass. Cumulative fixes still include the previously confirmed Maple Wiggler route fix.

Aroma export uses Options P6 RPX, 167 hooks, 8880 UTF16 arrays checked byte-identical during relocation. Code1021632 and Data128744 bytes fit the current1MiB loader limits. Existing v0.28 plugin preserves DSI diagnostics. Cumulative package includes prior R4 fixes, current native Options layout and user menu music.

No comprehensive Wii U performance measurements. 60FPS is a target and cannot be guaranteed. Console validation pending. Country flag in online lobbies remains unresolved; ROB VS and language refresh are not console-certified. TT150/200 records and ghosts remain shared. Nintendo base circuits were not rewritten. Only the124 selectable custom course models were audited in this pass.

Cemu isolated sample launched with Paris/Coconut course models and optimized private objects; user test requested, awaiting response. Source main content and saves untouched by this optimization deployment.

Tools: optimization_r3.py, optimization_objects_r3.py, optimization_dense_r3.py, package_r7_update.py; BFRES helper and meshopt scripts under tools/model_optimizer. Reports in the workspace work/optimization_{r3,objects_r3,dense_r3} directories. ZIP creation and verification recorded in optimization_r3/zip_verification.json once completed.

User confirmed Paris Promenade and Coconut Mall both run in Cemu VS with correct scenery (2026-11-04). This sample does not certify Wii U performance or every track.
