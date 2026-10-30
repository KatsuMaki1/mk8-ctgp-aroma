# Additional vehicle slots: runtime and validation

## Actual status

An experimental runtime is installed in Cemu. The catalog now adds Speeder 8 (body 39, donor 7), Red Offroader (body 40, donor 30), Wildfire (body 41, donor 7), Silver Monster (tire 21, donor 12), and SNES Tires (tire 22, donor 11). `vehicle_catalog.py` supplies generated native definitions, labels and donor mappings. Every native choice remains in place. UI capacities are 43/24 including the original spare/locked entry; parameter-table counts are 42 bodies and 23 tires. MSBT labels are 0x7000..0x7004.

The user previously confirmed both original mod previews without a crash, a race with the mod models after the audio enum fix, and returned drift sparks after the particle constructor fix. Subsequently reported missing trick effects and engine sound were addressed by the complete-fix candidate, but that result has not yet been explicitly confirmed. The new five-choice catalog includes those corrections; do not conflate successful boot with complete race/audio/particle validation.

Adding three more RGBA8 menu icons caused a boot failure in BFLYT construction. A controlled test with the old menu and identical five-choice RPX booted; the user confirmed it worked. The three new icons were re-encoded in native BC3 format (32,808 bytes each instead of 131,112). Existing native and DK icons and the two previously added vehicle icons remain byte-identical. The compact menu boots and stays alive past the former crash. The exact heap/resource limit is not established; archive growth was isolated as the trigger. Await user confirmation of the three new icons/models.

`tools/vehicles.py` is still only the asset importer: its staging-only manifest describes that command, not the installed runtime. `vehicle_patch.py` builds/installs/upgrades/restores the executable and tables. `vehicle_icons.py` adds the icons to a tracked installation. Full rollback restores the previous costume selector, tables, MSBT overrides and menu archive; do not use costume-only rollback for a vehicle install.

Speeder 8 contains Blue, Flaming, Green, Holiday and Pink alternatives. Each contains BodyK_Wld.szs and a matching TireK_Slk.szs. The initial staging selects Blue. Silver Monster contains TireB_Zbi.szs, TireK_Zbi.szs and TireT_Zbi.szs, covering the game's vehicle categories. Neither archive contains a selection icon. Every selected asset has the same internal model name as its stock counterpart, and no original skeletal animation names are missing. These are static checks only.

Assets are stored under `<update-content>/custom/vehicles/`, including the separately staged Speeder slick tire. Stock `kart/body` and `kart/tire` are unchanged. Do not globally activate all supplied files: that would replace the original parts, contrary to the requested additional slots.

## Verified native EUR v81 functions

Recovered from the user's own binary using the existing local headless Ghidra project. The live Ghidra MCP endpoint is unavailable; headless analysis works.

- 0x025df218: builds the body/tire/glider controls; constructors 0x025a47b4, setup 0x025a4980.
- Control type 0 at +0x22c means body, type 1 tire, type 2 glider. Player is set at +0x1a0.
- 0x025a4980 allocates capacity 40 body entries, 22 tire entries, 15 glider entries, each 16 bytes. These are capacities including room for a locked/unknown item, not counts of real selectable parts. Native real IDs are body 0..38 and tire 0..20.
- +0x5c/+0x60 are allocation dimensions, +0x64 points to entries. +0x68/+0x6c are active dimensions. +0x6a8 counts filled entries; +0x6b0 holds a special selected unlock item.
- 0x025a514c populates bodies; 0x025a5c18 populates tires; 0x025a60f0 populates gliders. Tail entry points 0x025a5c14 / 0x025a60ec also exist. They filter unlock state and explicitly enumerate native IDs.
- 0x025a4ed8 appends an entry: word0 id, byte8 availability, word3 flag. It wraps to the first entry if capacity is exceeded, so capacity must be expanded BEFORE appending.
- 0x025a50c4 finds a selected ID and sets the roulette cursor at +0xa4/+0xac.
- 0x025a63ac selects which fill routine to run.
- 0x025a6574 and 0x025a6910 handle visible cells. Six pooled visual cells are separate from total selectable entries; do not increase visible-cell count when adding choices.
- 0x025a662c binds a cell icon. Calls 0x02557754 for body/tire/glider icon lookup; part type and enum ID determine the texture name.
- 0x02554b74 initializes shared parts-name and texture-name arrays with fixed native lengths. Additional IDs also need names/icons registration or explicit alias handling.
- 0x0242bddc builds model resource paths from a recipe. Recipe words 0 driver, 1 variant, 3 body, 4 glider, 5 physical tire (TIRP result), 6 logical tire. Existing Mario/DK hooks affect driver prefixes and must be preserved.
- 0x0242bcd0 prefixes a resource name with its folder. Body root `kart/body/` at 0x100b2a54, tire root `kart/tire/` at 0x100b2a6c. New part IDs must resolve both menu preview and race resources.
- Shared name strings identify BodyK_Wld as body ID 7 and T_Zbi as tire ID 12. Slick is tire ID 4.

## Parameter tables that must remain consistent

The update's `common/mush/Parts.bin` has PRTS magic, total size u32 at +4, section count u16 at +8, base offset u16 at +10, and relative section offsets from +16. Current count 14, base 0x48. Each section starts with tag, two u16 dimensions and a u32 auxiliary field, followed by records. Preserve auxiliary data: DRVR +8 is nonzero.

Relevant dimensions:

| Section | x | y | Meaning |
|---|---:|---:|---|
| BODY | 39 | 1 | 320-byte body records |
| TIRE | 21 | 1 | 144-byte tire records |
| BDDR | 37 | 39 | driver/body cross-table |
| BDTR | 21 | 39 | tire/body cross-table |
| BDWG | 14 | 39 | glider/body cross-table |
| TRBD | 39 | 21 | body/tire cross-table |
| TIRP | 21 | 1 | tire parameters |
| TIEF | 21 | 1 | tire effects |
| BDEF | 39 | 1 | body effects |

Performance.bin has base 0x54 and 17 sections. Only PTBD (39) and PTTR (21) are per-part stat tables to extend. The many PRxx sections also have dimension 21, but these are performance-level curves: DO NOT automatically extend every dimension matching 21.

A real implementation must either extend all relevant enum/table consumers coherently, or keep native IDs for gameplay and carry a separate per-player custom-part identity through preview, race loading and persistence. Simply increasing roulette capacity, using a global file replacement, or appending a model filename does not meet the request. Compiled matrix strides and fixed enum bounds remain to audit before installing such a patch.

## Reproducible staging

`python tools/vehicles.py stage --base <base-content> --content <update-content> --speeder <speeder_8.zip> --silver <silver_monster.rar> --color Blue`

The importer reads only known models from each archive, validates BFRES names/animations and resource hashes, refuses conflicting staged files, and does not execute archive contents. It requires the installed 7-Zip for RAR extraction. No redistribution of user-supplied assets is added to the repository.

Scratch decompilations, debugger captures and model-rendering tools are under the Codex workspace `work/vehicles/`.

## Race consumers and native leaf contracts

- 0x0242b660 builds a canonical resource recipe, returns its object in r3, and originally preserves r4-r8 plus special state. The assembly gateway preserves those registers, CTR, CR and XER. Recipe-pointer flags retain custom resource paths while internal BFRES names remain canonical.
- 0x0245d3e4 classifies bodies through a fixed enum string table: alias 39 to 7 before calling it. This fixed the roulette preview crash, including when a stock model was temporarily used in the extra slot.
- The race audio system has several inline body enum consumers. A crash captured at 0x02056590 was a null bank name from the caller at 0x02069050. The inline guard at 0x02069024 normalizes an out-of-range index to donor index 8. The race body accessor at 0x021941b4 also aliases 39 to 7 while preserving its leaf contract (r12 contains the state pointer; r0/CR/LR are retained).
- 0x021ae8f8 is the actual particle-constructor entry, beginning with mflr r0. Do not hook the following stwu at 0x021ae8fc: the constructor would save the wrapper's wrong r0/LR. Its two-word descriptor is body/tire. Canonicalizing it restores drift emitters, verified by the user.
- 0x024527b0 resolves the body resource name for banks such as audio/body/SNDG_K_Wld.bars. The new candidate aliases its body input to the donor.
- The unit constructor at 0x021bc28c copies selection fields into persistent race state. Source +8 is body, +0xc tire, +0x10 glider, +0x14 driver. State +0x50 is player, +0x54 body, +0x58 driver, +0x5c tire, +0x60 glider. Inline hooks at 0x021bc354 and 0x021bc390 normalize only the persistent body/tire fields. They preserve registers and CR set by the preceding addic.; the original source descriptor remains unchanged for selecting mod model resources. This candidate targets missing engine/trick effects and still needs user validation.

## Aroma

The v0.4 plugin supports common, driver, kart and other content directories as well as the original CTGP layers. Layer capacity derives from the directory list. Missing directories are skipped. Wrong-code verification fails before enabling content layers.

`tools/aroma_features.py` recompiles the same native sources with the console text/data shifts, appends them to a verified EUR v81 CTGP pack, preserves its code/data prefixes, and adds matching Patches/Verify guards. Optional `--cemu-baseline` carries the existing signed-field CTGP helpers and speedometer format with exact guards. Cemu RPX files are not console plugins.

`tools/aroma_bundle.py` creates a private SD snapshot from the user's local assets, adds the WPS and code pack, verifies copied hashes, and creates an archive if requested. Generated binaries and game assets stay outside Git. Compilation/static verification is not console validation: no real Wii U test has been performed.

`vehicle_batch.py` prepares and transactionally installs an expanded catalog on an existing tracked installation. It builds all table cross-products from the ORIGINAL backed-up tables, preserves every original MSBT label, validates BFRES names/animations, and retains full pre-vehicle rollback. A revision snapshot additionally preserves the previous active five-file/label/menu state. `vehicle_icons.py upgrade` replaces only owned icon members and verifies all other archive payloads unchanged. The temporary menu-isolation probe has been ended; do not restore its old menu over the current compact menu.
