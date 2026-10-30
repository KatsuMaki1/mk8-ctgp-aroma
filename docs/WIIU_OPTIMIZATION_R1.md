# Wii U course optimization R1

Based on the user's console measurements, the content-only patch targets
seven older custom courses. It does not replace course versions or change
the new Boltthunder4 cups. Output ZIPs are in the chat workspace's `outputs/`:
`WiiU_CTGP_Optimization_R1.zip` and `Cemu_CTGP_Optimization_R1.zip`.
Each is approximately 192 MB and contains ten game files.

| Course directory | Triangles before → after | Texture data before → after (MiB) |
| --- | ---: | ---: |
| Gu_SkyArena | 492,693 → 421,240 | 74.3 → 53.0 |
| Gu_DivBowser | 321,262 → 298,226 | 70.7 → 55.9 |
| Gu_PacMountain | 244,564 → 229,326 | 71.2 → 46.8 |
| Gu_BoulderCanyon | 139,909 → 120,909 | 61.8 → 43.9 |
| Gu_GhostValley3 | 87,070 → 75,672 | 58.8 → 28.9 |
| Gu_N64MarioRaceway2 | 189,926 → 171,646 | 44.1 → 28.9 |
| Gu_DelfinoIsle | 13,060 → 12,904 | 5.9 → 3.9 |

These are resource counts, not measured Wii U frame-rate improvements.
Delfino Isle was already geometrically light, so its reduction is modest.

`tools/model_optimizer/Program.cs` exports static, single-LOD, single-submesh
triangle meshes and their normals/UV attributes using the existing local
BfresLibrary. `simplify.mjs` uses meshoptimizer with locked borders and a
maximum absolute error of two model units. Named road, floor, boundary and
other protected meshes are excluded. Ghost Valley's wooden surfaces are
also excluded. Vertex buffers themselves remain byte-identical.

Large textures use lower levels from their original mip chains. Oversized
single-level lighting atlases are resized and recompressed in the same BC
format; roundtrip PSNR exceeds 28 dB against the resized source. Fine
texture/lighting detail is reduced. Every swizzled output mip is decoded
and compared with the expected source blocks.

`patch.py` modifies the original BFRES in place: index counts/buffers and
explicit FTEX header/data ranges only. Unused buffer space is zeroed, and
every byte outside those ranges is asserted identical to the original.
The complete BFRES is reloaded with BfresLibrary and every vertex buffer,
protected index buffer and texture is checked. Native Yaz0 compression is
independently decompressed and compared byte-for-byte with the result.
KCL, object placement, paths, checkpoints, laps and minimaps are untouched.

Choco Island 1's normal/final-lap BFSTM files have six channels, but their
last stereo pair had RMS near 0.000062, versus about 0.09 on the first pair.
The clean primary stereo is repeated into all three pairs, resampled to
32 kHz, and matching prefetch data is rebuilt. This addresses the quiet
layer selected while driving; the in-game result still needs validation.

The local Cemu installation was authorized by the user and completed with
ten original files backed up in the chat workspace:
`work/wiiu_optimization/cemu_backup`. `state.json` records before/after
hashes. `restore_cemu.py` verifies both current files and backups before
restoring. No RPX, plugin or CUP0 file was changed. Cemu was relaunched and
observed running; all seven optimized races and Wii U FPS remain untested.

The previous Cemu process (PID 7004) was unresponsive after the user closed
it. Its closure was completed before replacing any files. The new debug
test process is PID 37952, with the existing read-only crash observer.

The two ZIPs have passed CRC checks:

* Wii U SHA-256: `6472b0d346556df882985d486f465d6a721d0dc240e4d790c9749f8d0637fe45`
* Cemu SHA-256: `ae5925e5ef0bd25829ce25a35808e96d5267cbdcaf6f6fd10d7697648a8e34bd`

The original source packs warned about Grand Prix crashes; begin with VS
Race. Older smooth tracks, Rainbow Road 9 and Daisy Circuit's missing
minimap are retained. The previous online disconnect remains unresolved.
