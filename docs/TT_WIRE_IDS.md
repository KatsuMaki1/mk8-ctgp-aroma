# CTGP TT wire contract, 2026-11-06

The NEX game_server_id is **1010EB01**, distinct from vanilla **1010EB00**. It selects the service route; it is not a per-track ID and does not by itself authenticate an unmodified client or isolate worldwide sessions.

`tools/tt_wire_catalog.py` emits the same append-only registry for client and server. Source identities/revisions come from the 172-entry `ctgp-catalog-next.json`. The authoritative allocated registry is `E:/claude-code/mk8-nex/ctgp/wire_catalog.json`; retain it when regenerating, never renumber it from cup positions. Generated C table: `work/tt_categories/wire_catalog.h`.

Each track revision receives four slots starting at 128: 150 native, 200 native, 150 pink-v1, 200 pink-v1. Category = persistence slot + 16. Slots stay below 1024. Removed tracks retain their IDs; a changed content revision gets new IDs. Unknown revisions and exhausted capacity are errors. Standard Nintendo 150cc/pink-OFF records retain their native categories.

## Runtime evidence

- P55: user confirmed normal stick and Luigi / Mario Circuit 3 / TT 200cc race starts. Country manager writes disabled, but the two legacy getter hooks remained.
- P56: accepted click captures `ct.gu_bcp10`, revision `2a6b158353199fb6a07054b79a9eddee2c00755482b1cae35b918dafdb99c326`, donor course29. Server received category191 (200cc/pink ON). Ghost uploaded to slot175; SCORE still erroneously uploaded to category29.
- P57: separate `02405E7C` score hook added. User re-uploaded existing 1:13.488 replay. VPS confirmed category191, score73488, replay object8 at slot175. Existing category29 rows deliberately untouched. Download/replay on another player remains unverified.
- VPS deployment includes registry lookup and reserved-category validation. Backup: `/opt/mk8-nex/backups/typed-wire-20261106/` (source archive, previous image ID, PostgreSQL dump). Auth/secure UDP29500/29501 verified running. No firewall/token-service configuration changed.

## Controller and country correction

The old `country_get` / `country_local_get` names are misleading. Hooks at 024CB344 and 024CC5BC affect steering-use information; 024D47C4 stores the latter in entry+9C8 and 0245A28C consumes the former in driving statistics. Never return selected country IDs there. P58 builder restores both original entry instructions. Source wrappers now pass through.

Country profile copy at **024DD0F0** copies a verified 0xD4-byte player profile. For own-Mii copies only, the new hook changes profile+74/+75 (country/region), +78/+79 (repeated country/region). This corresponds to native ghost offsets2A4/2A8 with profile base230. All other profile bytes and controller state remain unchanged. P58 installed and launched (PID28724); memory readback confirms both restored native accessor instructions. Selected country is219 (Morocco). Online profile publication validation pending; last probe profile-copy counter was0. Keep these checks distinct from a claim that the flag renders correctly.

An existing 1:13.488 recording really contains flags0x200000 at payload+378 and a wheel marker in its filename. It is not merely a server rendering invention. Do not clear historical replay flags just to hide an icon.

## Pending client UI and ghosts

P57 intentionally contains no scoped ghost/UI hooks: donor staff ghost, title and thumbnail still appear. P59 is a separate compiled candidate adding scoped personal/staff directories, footer preview/title and native online-title overrides. It keeps native NEX list states/sounds/B handling; no obsolete local HTTP bridge. Standard Nintendo150/pink-OFF personal ghosts remain native. P59 is not installed or runtime verified yet.

`staff_ghosts.py` now checks native payload/filename course consistency and converts a downloaded dg cache slot into the correct sg staff slot without editing payload inputs. A test staff replay based on the verified Mario Circuit3 200/pink run is staged under the workspace `work/staff_validation/content`, not distributed or playback validated.

The server formerly guessed CTGP from CTG0. This is wrong: CTG0 is the native Wii U SAVE wrapper, while actual native NEX uploads can be raw even from CTGP. Local source now logs transport format and declared board separately; tests pass. This follow-up logging/validation correction is NOT deployed yet.

Worldwide custom voting, real cross-client ghost retrieval, missing flags rendering, graph behavior, actual pink particle effects, and final Aroma/Cemu distribution still require implementation or validation. Do not describe them as complete.

Read-only PTCL inventory is now available via `tools/ptcl_inventory.py`. Original common.ptcl SHA256 `6eeedda335124278cb12fa5355b6568eab7dae9b849a71436c74921fcd516387`, EFTF0x41, 279 effects. The regular blue and orange drift effects each contain multiple emitters with separate HDR color0/color1 tables. No particle resource was modified/installed in P58/P59. Workspace report: `work/pink_drift_p2/common_ptcl_inventory.json`.
