# NEX study: ghost upload and "I am a CTGP client" (2026-11-06)

Goal: make a real Wii U (Aroma plugin) and Cemu (patched RPX) identify themselves as CTGP to the Protarium server over the
game's own authenticated NEX session, and send/receive TT ghosts that way. Everything below is from static analysis of the
v81 EUR RPX and from the local server sources. Nothing was captured on the wire yet.

## 1. What the game contains (verified in the RPX)
The RPX embeds the complete NEX client (RTTI type names). Relevant parts:
- DataStore: `DataStoreProtocolClient`, `DataStoreLogicServerClient`, `DataStorePreparePostParam`, `DataStoreCompletePostParam`,
  `DataStorePrepareGetParam(V1)`, `DataStoreReqPostInfo/GetInfo`, `DataStoreMetaInfo`, `DataStoreSearchParam/Result`,
  `DataStoreRateObjectParam`, jobs `JobDataStorePostObject`, `JobDataStoreGetObject`, `JobDataStoreUpdateObject`
  (post = Prepare, HTTP upload to a file server, Complete; get = Prepare, HTTP download).
- Ranking: `RankingProtocolClient`, `RankingRankData`, `RankingScoreData`, `RankingResult`, `RankingOrderParam`.
- Matchmaking: `MatchmakeExtensionProtocolClient`, `MatchMakingProtocolClient(Ext)`, `MatchmakeSession`,
  `MatchmakeSessionSearchCriteria`, `JoinSessionOperation`, `SimplePlayingSession`.
- Plumbing: `CallProtocolMethodOperation`, `ProtocolCallContext`, `RMCContext`, `ClientProtocolRequestBroker`,
  `TicketGrantingProtocolClient`, `JobTicketManagerAcquireTicket/Login` (the authenticated secure-ticket path), `NATTraversal*`.

## 2. What the native "send ghost" does
- The UI state machine `025C8CA0` (our `tt_upload_sequence` hook) drives the dialogs. When the user confirms it calls
  `024F25E8(ghostManager, {courseId:u32, flag:u8})` with `ghostManager = ctx+0x2C8`, then `024F5F00` (wait loop).
- `024F25E8` -> `024F22AC(manager, {taskType=5}, params, 8)`: stores task type 5 (upload) in `manager+0x98`, copies the 8 parameter bytes,
  and starts the manager's state machine through virtual slot `+0x1C` of the object at `manager+0xC`.
- **The only identity sent is the native course id** (the donor of a CTGP track). CTGP tracks that share a donor are indistinguishable
  to a stock server. The NEX calls themselves are issued deeper, inside that state machine (not decompiled yet).
- The error the user saw on "send ghost", 106-1203, is `DataStore::PermissionDenied` (module 106 = DataStore): the DataStore path
  reached a server and was refused. So the Protarium side that answered is not only this fork.

## 3. What our server (fork of mario-kart-8-secure, nex-go v1) implements
Registered: Ranking `UploadCommonData` (acknowledge only), MatchmakeExtension `AutoMatchmakeWithSearchCriteria_Postpone`, MatchMaking
`GetSessionURLs`/`UpdateSessionHostV1`, MatchMakingExt `EndParticipation`, NAT traversal, secure connection (`Register`,
`ReplaceURL`, `SendReport`). **No DataStore at all, no Ranking lists.** The `Data` hook only prints protocol and method ids of every
request, which is exactly what a first capture needs. The server sets NEX 3.5.4.
`ctgp` package (HTTP): boards by (client, track, revision, cc, rules), CTG0 validation, quota, auto-approve, remove/block.

## 4. The "I am CTGP" signal
Already implemented server side: `ctgp:1:<catalog hash>:<rules>` read from the message of `AutoMatchmakeWithSearchCriteria_Postpone`
(mixed mode `CTGP_ALLOW_VANILLA=1` treats a missing envelope as vanilla). The game never sends it. Needed game side: write that
string into the `strMessage` parameter when the game builds the matchmaking request (find the call; the argument is currently empty
or a native message).
Because it rides the authenticated NEX session, the server also learns the real PID from the secure ticket. It remains a *claim*:
a modified client can lie, so moderation (remove/block) stays necessary.

## 5. Plan
1. **RMC logger (no server needed).** Find the function that serialises and sends an RMC request (start from the vtables of
   `ProtocolCallContext` / `ClientProtocolRequestBroker` / `CallProtocolMethodOperation` in Ghidra), hook it in the Options module
   and keep a ring of (protocol id, method id, parameter size) in guest memory; read it with the existing read-only tooling while
   doing a native ghost upload, a ghost download and a matchmaking. This tells us exactly which DataStore/Ranking methods the game
   uses for TT. (Cemu only; the same hook can later be shipped to Aroma.)
2. **Decompile the ghost manager state machine** (virtual slot `+0x1C` of `manager+0xC`) to see how the DataStore/Ranking parameters
   are filled (name, data type, tags, meta binary, rating slot).
3. **Server:** implement the DataStore (PreparePostObject, CompletePostObject, PrepareGetObject, GetMeta/Search) and the Ranking
   methods the logger shows, backed by the existing `ctgp` store; reuse `CTG0` validation and auto-approve.
4. **Category identity:** CTGP tracks need a global course identity on the wire. Proposal: the module replaces the donor course id
   by a reserved id (>= 0x1000, from the catalog) in the upload/download parameters for CTGP tracks, and sends the 200 cc / pink rules
   in a field the server can read; vanilla tracks stay untouched.
5. **Admission:** the module fills the matchmaking message with the envelope (Cemu RPX first, then the Aroma plugin).
6. Only after 1-5 work against a local NEX server and Cemu: review with the user, then deploy.

## 6. Open questions
- Which server answers the production DataStore calls (the fork has none)? Reading its logs needs the user's go-ahead.
- Does the native ghost download (rows with the Mii icon) expect Mii data in DataStore meta (icon buffer of 0x2582C bytes, see `handoff.md`)?
