# Whole-pack optimization R2

The user requested further optimization across the entire pack. R2 audits
all 80 playable custom-course directories, including the 48 Boltthunder4
entries, against the locally installed R1 content.

Final result: 74 courses changed; 5 already-light courses retained; DS
Rainbow Road (`Gu_Bolt42`) retained because it uses non-standard model and
texture signatures. No unverified conversion of that resource is shipped.
The five unchanged light courses are Canyon Run, Desert Hills, the Bolt
Cloudtop-based Rainbow Road variant, Bone Piranha Byways, and SMW Raceway.

Across changed courses R2 removes 674,126 additional triangles and
1,914,762,240 bytes of texture data compared with R1. This is a sum across
courses, not simultaneous RAM savings or a measured frame-rate improvement.

The R2 texture profile uses 512-pixel caps for identified normal/specular
detail and ordinary scenery textures; 1024 for readable road/sign/marking
textures and identifiable lighting atlases. Existing author mip levels are
preferred. Supported single-level BC1/BC3 UNorm images are resized with
Lanczos and recompressed in the same format; candidates below 28 dB PSNR
against the resized source are rejected. Fine texture detail is visibly
reduced in exchange for lower bandwidth/storage requirements.

Geometry simplification is limited to identifiable scenery. Road/floor,
boundary, ramp, boost, start-line and similar names are protected. Animated,
multi-LOD and multi-submesh geometry is excluded. Meshoptimizer uses locked
borders, normals, both UV channels and vertex-color attributes, a 50% target
index count, and a maximum 3-model-unit error relative to the R1 input.
R1-modified geometry already had its separate 2-unit bound. Vertex positions
are not rewritten; neither are KCL, object placement, paths or checkpoints.

The in-place BFRES patcher asserts exact diff coverage. Every vertex buffer,
protected index buffer and texture mip is independently verified after
reloading. Every compressed published model has been decompressed and
compared byte-for-byte with the intended container. All 79 supported models
also passed a second verification run with the final verifier.

The original verifier assumed dictionary keys always equal embedded model
and shape names. Coconut Mall and one other source resource violate that
assumption. The verifier now follows actual dictionary keys; identity tests
(original versus original) on both cases passed before retrying candidates.
The optimized Coconut variants then passed without discarding geometry.
Shared-buffer protection also has a conservative texture-only fallback if
geometry verification fails; no failed candidate is packaged.

Tools: `tools/optimization_r2.py`, `tools/model_optimizer/`,
`tools/package_optimization_r2.py`, `tools/install_optimization_r2.py`.
The three build workers write disjoint course ranges and per-course caches;
the final aggregator accounts for all 80 directories. Output metadata lives
under the organized outputs/Documentation folder, outside the SD-only ZIP.

Packages merge verified models over the October 28 complete R1 archive.
Unchanged SD files are checked against that archive's SHA-256 manifest.
The plugin, runtime code, cups, icons, costumes, vehicles and music are
retained. Wii U experimental speedometer toggle/pink drift remain excluded.
The earlier multiplayer communication timeout remains unresolved.

R2 is a test candidate. Actual Wii U FPS and all 74 race visuals still need
hardware testing; file integrity checks do not establish those results.

The 74 changed models were installed into Cemu with verified backups under
the chat workspace's `work/optimization_r2/cemu_backup`. No RPX or UI file
was replaced. An initial emulator launch (PID 8444) terminated with native
fail-fast 0xC0000409 and no identified guest instruction. A later process
(PID 4344) was observed at MK8's mode-selection menu. Do not attribute that
initial host crash to course geometry without further evidence. R2 race
tests remain pending; an asynchronous request asks the user to check
Coconut Mall, Sky Arena and one Bolt course.

The final SD-only full archive is in organized outputs/WiiU:
`CTGP_Aroma_COMPLET_SD_R2_2026-10-30.zip`, 2,927,216,512 bytes, 1,756 SD files.
SHA-256: `7987dddaede17e3cbc800dee1153866723955770a32addf06b15a95f04586ac4`.
CRC checks passed. Smaller Wii U and Cemu R2 update ZIPs are also available
under WiiU/Mises_a_jour and Cemu, respectively. Their metadata and the
per-course accounting are in outputs/Documentation/Optimization_R2-*.
