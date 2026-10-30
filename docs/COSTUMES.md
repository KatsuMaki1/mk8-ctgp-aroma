# Character costumes: prototype status

The first asset is the user's `mario_sunshine_v1_1.zip`, specifically its **over Mario** branch. The Metal Mario and Tanooki versions are unused. Do not redistribute the supplied assets as part of this toolkit.

## Current implementation

`tools/costumes.py` validates and stages Sunshine under `custom/costumes/Mario/Sunshine`. It checks the Wii U BFRES version, internal model names and original skeletal animation names. The supplied model retains `Mario`, `Pupil`, and all 64 original skeletal animation names. These are static checks, not an in-game compatibility result.

```powershell
python tools/costumes.py inspect-sunshine --archive <zip> --base-game <base-content>
python tools/costumes.py stage-sunshine --archive <zip> --base-game <base-content> --content <update-content>
```

The selection voice is staged separately. No global voice archive or native menu is changed.

## Reversible model test

With Cemu closed:

```powershell
python tools/costumes.py activate-sunshine-test --content <update-content>
python tools/costumes.py restore-sunshine-test --content <update-content>
```

Activation temporarily overrides **all uses of Mario** with Sunshine. It installs no runtime selector, custom voice or per-player costume choice. No RPX, ticket or save is edited.

Rollback state and any prior update override are saved outside content in `<content>_backups/costumes/MarioSunshineTest`. If no override existed, restoration removes only the test model so the untouched base model loads again. The tool refuses to overwrite externally changed resources. Staging and test operations are idempotent for the same files.

The user confirmed the supplied model appears correctly in the character preview and subsequently confirmed the in-game model test passed (2026-10-25).

## Experimental selector: awaiting in-game validation

**Race HUD dependency (2026-10-25):** the user confirmed the submenu works and original Mario races successfully, but Sunshine alone crashed on race loading. The preserved log shows the missing file `ui/cmn/a_race/timg/ym_HornEmblemMario_01^h.bflim`, followed by a null texture in `GX2SetPixelTexture` (`LR 0x026a51fc`). Sunshine's model file had opened successfully. Unlike the standard character-icon name formatter (which adds color suffixes only for Yoshi/Maskass), the race horn-emblem path also requests Mario variant 1.

`costumes.prepare_sunshine_hud` now stages and installs an exact copy of the base Mario `_00` emblem under that `_01` name. It preserves differing existing files and verifies the staged dependency hash. `stage-sunshine` prepares this dependency automatically, and the RPX installer checks/installs it from the staged dependency manifest. The alias is installed in the user's content folder; the RPX was unchanged for this fix. Three dependency/conflict regression tests pass. The corrected Sunshine race still awaits user confirmation.

For an already staged installation:

```powershell
python tools/costumes.py prepare-sunshine-hud --base-game <base-content> --content <update-content>
```

The alias is copied from the user's own base game, not distributed as a toolkit asset. A future pack builder must also include the active alias from `hud_alias.json` when packaging the selector; the existing general distribution builder does not yet collect this new UI dependency automatically.

**Boot crash corrected (2026-10-25):** the first candidate's prefix hooks replaced `addi` instructions at `0x0242e0ac` and `0x0242e1dc`, but `R_PPC_ADDR16_LO` relocations write their immediate fields at instruction `+2`. The loader rewrote the branch low halves and redirected execution into CTGP import-resolution code. The initial equality-only relocation guard missed these writes.

The corrected candidate hooks non-relocated calls at `0x0242e0b0` and `0x0242e1e0`: `bl` enters a stub that tail-calls the original prefix routine at `0x0242bcd0`, preserving LR. Build/audit reject any relocation starting inside a patched instruction. Six regression tests reproduce the bad destination, exercise the emitted prefix stubs for Mario and other characters, and check writable-state placement.

Automatic Cemu boot isolation: baseline, repack-only, payload-without-hooks and menu-hooks-only survived; original prefix-hooks-only reproduced the crash. The corrected full candidate survived 45 seconds and loaded title-menu resources. **`Turbo_costume_selector_fixed.rpx` is installed.** Do not use the earlier `Turbo_costume_selector_test.rpx`. Actual submenu and race behavior remain unverified; the visual check was blocked by the Windows lock screen.

`tools/native/costume_selector.c` and `tools/costume_patch.py` now build a separate candidate RPX with a two-choice Mario submenu. They use a custom list mode, four independent in-memory selections, and Mario's original character ID. The resource builder selects the staged Sunshine directory for Mario variant 1; variant 0 uses the original `driver/` path.

The first prototype uses Mario's native icon for both cells. Hovering should display `Mario` or `Mario Sunshine`. No custom voice is enabled. Selections reset on game restart. The menu hook is limited to local character pages; network modes, replays, ghosts and simultaneous different Mario models are not validated.

Build and audit without changing the installed game:

```powershell
python tools/costume_patch.py build --rpx <current-CTGP-Turbo.rpx> --out <candidate.rpx>
python tools/costume_patch.py audit --rpx <current-CTGP-Turbo.rpx> --out <candidate.rpx>
```

The adjacent JSON manifest records hashes and all eight guarded patch sites. Build requires devkitPPC, expects the current CTGP code/data sections and refuses an already patched input. It appends code and writable state, preserves existing CTGP payload bytes and relocation sections, and rebuilds section offsets and CRCs.

With Cemu closed:

```powershell
python tools/costume_patch.py install --candidate <candidate.rpx> --content <update-content>
python tools/costume_patch.py restore --content <update-content>
```

Install saves the exact current RPX under the update's `code_backups/MarioCostumeSelector`, then restores the earlier model-only override so both choices can use distinct resources. Restore returns the exact RPX baseline with base Mario active. External RPX edits are preserved. Both operations reject a running `Cemu.exe` or `Xapfish.exe`.

First test one player: two choices, original Mario, Sunshine, cancellation, switching back, and racing with both choices. Then check Yoshi/Maskass and finally two players using different Mario costumes.

`tests/costume_selector_host.c` compiles the actual wrapper source against fake game services:

```powershell
gcc -std=c99 -O2 -Wall -Wextra -Wno-int-to-pointer-cast tests/costume_selector_host.c -o <host-test.exe>
```

It checks per-player choices, delegation, hover/cancel/confirm, cursor bounds and restoration, native Mario icon lookup and preview reload requests. Temporary-install tests also verified model-test removal, byte-exact RPX rollback and external-edit protection. These tests do not execute MK8 or prove its native interfaces correct.

## New reverse engineering findings

The Ghidra MCP backend was unavailable, but an existing local Ghidra 12.1.2 installation was used headlessly on copies of the clean v81 RPX sections. No downloads were needed. Analysis projects and generated decompilation remain scratch files outside the repository.

These are **RPX virtual addresses in clean EUR v81**, not Aroma runtime addresses. They are research points, not a validated patch list.

| Address | Observed behavior |
| --- | --- |
| `0x025dbd58` | Main character event handler. Reads character identity from a button's `+0xf8`, and event fields at `+0x14` and `+0x18`. Assigns a per-player list mode and transitions into its state. |
| `0x025d25dc` | Retrieves the character-list page at page index `33 + player`. |
| `0x025d4b04` | Character-list input handler. Modes 3 and 4 handle Maskass/Yoshi colors; mode 5 handles Villager variants. |
| `0x025d3f10` | Character-list entry animation/setup; calls `0x025a1064`. |
| `0x025a1064` | Sets up the list control and invokes a grid builder. |
| `0x025a0d68` | Builds the native nine-choice color grid. |
| `0x025a0be8` | Builds a native two-choice grid, useful as reference; identity and cell rendering still need custom handling. |
| `0x025669a8` | Applies the selected character for a local player. Uses the native stored color for Yoshi/Maskass; ordinary characters receive color zero. |
| `0x0256684c` | Stores character ID and variant byte at player-data offsets `+0x1c0` and `+0x1c4` and updates another selection representation. Later consumers have not all been traced. |
| `0x0242bddc` | Builds resource names from parameters whose first two words are character identity and variant. |
| `0x0242e0ac`, `0x0242e1dc` | Prefix construction for `driver/` inside that builder. |
| `0x0242e0b0`, `0x0242e1e0` | Non-relocated calls to the prefix routine; corrected prototype hooks these calls with `bl` and a tail call. |

The native user-data structure has separate four-player color arrays for Yoshi (`+0x147c`), Maskass (`+0x148c`) and Villager (`+0x14ac`). These are existing fields, not spare Mario storage. Do not repurpose them.

## Original implementation checklist

The prototype now implements the paths below, but actual native transitions, race variant retention and cache separation still require in-game validation. Custom icons and Aroma support remain follow-up work.

1. Add a custom list mode and two valid entries, preserving Mario's character identity.
2. Handle selection, cancellation, icons, preview/name updates and repeated entry independently for each player.
3. Pass the chosen costume through preview and race loading; check variant normalization.
4. Choose distinct resource paths and verify model-cache separation when two players choose different Mario costumes.
5. Validate the supplied model in game, then test multiplayer, replays and ghosts before claiming support.

Resources under `custom/` fit the plugin's existing redirection and distribution builder. A design using new top-level `driver` and `driver_tex` layers would instead require packaging, plugin and layer-handle capacity changes.

## Verification performed

- Compared the actual user archive's model and animation names with base Mario.
- Exercised staging, activation and restoration in temporary folders with and without an existing override.
- Checked repeat operations, conflicting resources and external edits are preserved.
- Rejected invalid signatures and excessive decoded-size headers.
- After the user confirmed Cemu was closed, activated the model-only test and verified the installed SHA-256 and unchanged base Mario SHA-256.
- The user confirmed the Sunshine model test passed. The selector itself is still awaiting an in-game result.

DK costumes use tools/dk_costumes.py to stage the two supplied ZIPs. They appear as three choices under Donkey Kong. Custom voices and kart skins are not activated because those shared assets would affect original DK too. Snorlax's authored internal model name is Link; menu and race testing is necessary. The selector installer supports upgrading a known, hash-verified previous selector while retaining the original CTGP baseline and a snapshot of the previous RPX.
