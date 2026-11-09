# Worldwide: CT courses in the vote (analysis in progress, 2026-11-06)

Goal: in a CTGP room, the Worldwide vote (3 course cards + Random) must offer CTGP custom courses, identically for every player.

## Status of the platform (verified)
- Worldwide matchmaking works against our server (VPS, UDP 29500/29501) from Cemu: login, ticket, Register, Ranking.UploadCommonData,
  MatchmakeExtension (0x6D/0x0F), NAT traversal, vote screen reached. Token routing: only PID 1768140980 goes to our server.
- **The NEX dispatcher trace hooks (nex_trace.h, P41-P44) made Worldwide hang on "Searching for players"; disabled in sources (P45).**
  The sandbox RPX with no hook at all, and P45 without the trace, both reach the vote screen.

## Code map (EUR v81 RPX, Ghidra project `work/costumes/mk8costumes`, outputs in `work/mk8_vote/`)
- `mn_WifiCourseSlct_00.bflyt` page: create `0x025FD2C0` (vtable 0x100E2878): 3 course buttons at page+0x170..+0x178
  (each gets an index 0..2 through `*(ctrl)=idx`), the Random button at page+0x17C (id 1000). Sibling method `0x025FD914`.
- `mn_WifiCourseRoulette_00.bflyt` page: create `0x025FF038`: 12 roulette slots in a vector at page+0x214 (count) /+0x218 (cap) /+0x21C (data).
  Update/state machine `0x025FFB84` (states 0, 1000, 0x3E9...), reads shared race state through the manager list at `_1018A18C+0xC`
  (+0x28 data: +0x1414 mode==6, +0x1425 selected course byte, +0x1426 flag).
- Vote reception handler `0x025FC140(page, {entry, slot, flag})`: course id = `*(entry+0x10)`, flag byte `entry+0x16`;
  sets the roulette slot (`025A9870`) and plays `SE_SYS_CRS_VOTE` (0x100E2440).
- Strings: `WiFi_Course`, `WiFi_CourseRandom`, `WiFi_Roulette`, `nncs1/2.app.nintendowifi.net` (hard-coded NAT check hosts).

## Open questions (not yet answered)
1. Where the 3 candidate courses are drawn (local RNG? from the course pool/cups?). Not found yet.
2. How the vote travels between peers (P2P, size of the course id on the wire; `*(entry+0x10)` is a 32-bit field but the wire size is unknown).
3. How a course id maps to the loaded course files; CT courses share donor ids, so a donor id alone is ambiguous.

## Constraint to design around
Two players in a CTGP room must resolve the same course id to the same CT. Options: (a) rooms keyed by pack hash so
every player has the identical donor-id -> CT mapping for the round; (b) widen the id on the wire (needs P2P message analysis).
Option (a) needs only the draw hook and the admission string `ctgp:1:<hash>:<rules>`; it does NOT solve two CTs on one donor.

## Findings, round 2 (Ghidra dumps in `work/mk8_vote/{page,mgr}.c`)
- **Vote manager** = entry 0x36 of the manager list at `*(0x1018A18C)+0x10` (`{count,data*}`), obtained by `025682E4()`.
  Live (Cemu, vote done): `+0xCC` = state machine (0x18 = finished), `+0xD4` = chosen course value (0x3E = Random, 0x3F/0x40/0x46 other specials),
  `+0xD0` flag, `+0xDC` counter. State handlers: `025F950C` (state 5 -> 0xF/0x12/0x13/0x14/0x18), `025FA150`, `025F9C44` (switch on +0xCC), `025FB7A4` (page state at page+0xBC).
- **Course ids on the vote are small** (specials start at 0x3E): a native id space of ~0..0x3D. A CT id >= 0x1000 cannot travel in this field.
- Other players' votes live in their player entry (list `ctx+0x2C0`, see nameplates): `+0x1D8` int vote course (-1 = none), `+0x1EC/+0x1F0` vote record,
  `+0x254`, `+0x260` flags. Handler `025FC20C` (per-slot state machine) copies it to the roulette slot via `025FC140`.
- **Not found yet**: the draw of the 3 candidates (not in the page create/state functions read so far).

## Recommended design (Option A, low risk)
Keep the vote and the wire ids native. In a CTGP room every client maps `native course id -> CT` through the pack table (same pack hash = same table),
and shows the CT name/preview on the card and loads the CT files when the roulette result is a mapped slot. No wire change; limited to one CT per native slot
for the pack's Worldwide rotation. Needs: draw/label hook + course load hook (course loading by donor already exists for offline cups), plus admission string.

## Room separation without touching matchmaking (2026-11-06)
The game builds its NEX game server id (0x1010EB00) with `lis 0x1011 ; addi -0x1500` at two sites (0x023D5628, 0x023E8C58, EUR v81).
`tools/ctgp_server_id.py` changes the immediate to 0xEB01 (build P46). A CTGP client therefore asks the account service for
`game_server_id=1010EB01`; that id is routed to the CTGP-only NEX pool (same Protarium NEX server, own token route), vanilla clients keep 1010EB00.
Server side needed (VPS, needs explicit go): `PN_GAME_SERVERS` gets `1010eb01=<host>:29500` in mk8-token, nginx map gets `1010eb01 127.0.0.1:8158;`.
Pack-wide consequence: every CTGP player uses the same pack table, so native slot N means the same CT for all of them in that pool.
Not done: card names/thumbnails for CT slots in the vote; real two-client test.

## Native ghost flow (verified on Cemu, 2026-11-06, build P47 = no TT hooks, no nex trace) - see also Pretendo `mario-kart-8-python` + `mk8-nex-protocols-common-python`
- Upload (after a TT run, "send ghost"): DataStore.PreparePostObject (0x18) -> HTTPS POST to S3 -> CompletePostObject (0x1A) -> DataStore.ChangeMeta (0x26)
  -> Ranking.UploadScore (0x70/1, category = slot + 16, score = time in ms, ASC). `persistence_slot_id` = native course slot (39 for Ice Ice Outpost), one ghost per (owner, slot).
- "Get more ghosts": Ranking.GetRanking (0x70/9: mode 0, category, offset 0, length 10) -> DataStore.GetMetasMultipleParam (0x73/0x24: one {owner, persistence slot} per row,
  result option 4) -> on A: DataStore.PrepareGetObject (0x73/0x19) -> GET presigned S3 URL. The list does not show the caller's own ghosts.
- The MK8 client never answers the PRUDP silence PING: server must use a long `MaxSilenceTime` (set to 30 min) or idle sessions die after 20 s.
- Course identity problem: category/slot come from the native donor slot (CT "Daisy Circuit" = `Du_IcePark` = Ice Ice Outpost). 150/200 cc and pink share them.
- Correction verified 2026-11-06: `ghostRecord+8` and job+0x148 are replay PAYLOAD SIZE, never a course slot. Do not overwrite them. Generic job parameter blocks are heterogeneous and must not be remapped by their first word.
- Typed wire adapter: `02406260` prepares a ranking query, `02405E7C` publishes a ranking score, `0241ECE0` converts a category to a persistence slot, and `023F4F48` prepares upload metadata. The first three are required together; metadata alone does not remap the uploaded score.
- See `TT_WIRE_IDS.md` for the append-only shared registry and verified P57 upload.

## Vote candidates found in memory (2026-11-07, Cemu live, P68 build)
- Course ids are the indices of the 80-entry directory table at `0x103028E8` (in the pack's own data section): 16-31 base courses, 32-47 retro, 48-66 DLC (`Du_*`, `Dgc_*`, `Dwii_*`...), 2-15 `ReservedNN` and 67-79 `UnderConstructionNN` are unused slots.
  Ice Ice Outpost = 55 (`Du_IcePark`), Sherbet Land = 37, Yoshi Circuit (DLC) = 56, Animal Crossing = 52 (`Du_Animal_Summer`) / 64-66 (other seasons).
  Ranking category = course id, DataStore persistence slot = course id - 16 (confirmed with the ghost uploads: category 55 / slot 39).
- At the vote screen with cards {Sherbet Land, Animal Crossing, Yoshi Circuit}, memory contains the u32 triple `[37, 52, 56, 31]` twice:
  (a) at `+0x10` of an event/message object (vtable `0x100AC85C`, callback `0x023DD9C0` builds a session/criteria message), (b) at the start of a larger
  vote record: `[ids x4][0x07000604][0x11111126]` followed by twelve `0x000000FD` entries at stride 12 (one per player slot).
- DLC courses ALREADY appear in the pool (Animal Crossing, Yoshi Circuit). The generator that draws the three ids has NOT been located (no RNG in the page/manager code read so far).
- The `0x103028E8` table has no `lis/addi` cross references in native code (it sits in the pack's own data region), so the native loader reaches it another way.
