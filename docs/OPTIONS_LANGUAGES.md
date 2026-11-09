# Options localization prototype P1 (2026-11-04)

Built for EUR81, preserving R4 gameplay fixes and the existing native Options page.

- Country names, Automatic, Language and Speedometer use the game language.
- 119 non-null country/territory IDs from the owned Wii U country.txt, including Russia (100). Auto is an additional entry. Country IDs are not flag texture indices. Adding a country to this list does not create a missing flag or resolve the separate online flag propagation bug.
- Native horizontal UI repeat bits 0x80/0x100 cycle the focused country/language; these input bits include the native stick direction mapping. Simultaneous left+right does nothing. Vertical focus and Back remain native. A/touch also advance for compatibility.
- Third native row chooses Automatic or English, French, German, Spanish, Italian, Portuguese, Dutch, Russian. Only the eight complete installed EUR language directories are offered.
- Native language-code getter 02566024 is wrapped. Native message-manager lookup 0253D690 is wrapped: Auto forwards, unknown/missing messages forward, otherwise a binary search returns the selected language's existing UTF-16 message, retaining native control codes. The four archives have 983 unique IDs per language; the generator rejects conflicts.
- Existing main menu button messages are refreshed when selecting a language. Other cached text/picture resources update as their pages are rebuilt. No font/resource destruction during a live page. No system settings, accounts, tickets or saves are modified. Choices are session-only.
- `tools/options_localization.py` reads the active owned content MSBT files, preserving mod names. Babel/CLDR supplies localized country names; generated header is local build output under work/options_i18n. The JSON overrides interface accepts additional language directories and translations. Arabic shaping/RTL and any missing fonts are NOT implemented; Arabic, Vietnamese, Greek and full Chinese translations are not advertised as installed.

Build requires Babel on the generator Python path, then:

```
python tools/options_localization.py CONTENT SYSTEM_COUNTRY_TXT work/options_i18n
gcc -O2 -Iwork/options_i18n tests/options_submenu_host.c -o work/options_i18n/options_host.exe
```

Host checks cover all generated message lookups, Auto and missing-message fallback, country wrap in both directions, simultaneous directions, focus selection, native completion and local/remote country preservation. PPC compilation and RPX roundtrip passed. Cemu interaction and Wii U runtime are still pending; this is a test build, not a validated console release.

## Native VS rows P2

User requested actual VS-style selectors instead of arrow characters in the original Solo buttons. `tools/options_rows.py` adds three Parts instances of a private copy of `cm_L_Scroll_List_01` to the Options page. Original VS/common assets remain byte-identical. Native left/right arrow parts, touch regions and animation names are retained. Separate label/value text panes use bounded single-line display; long values get an ellipsis. Full country names stay in the catalog.

`tools/native/options_rows.h` binds native row constructor 0258AE5C and the VS row model interface (enabled/type/label/value/change). Native direction values 2/3 and native slide sound are reused. Native focus indexes are read from control+44, distinct from our event IDs14..16. Original Solo rows are hidden only during Options and restored outside it.

P1 rendered the native assets but retained default preview text: live reads confirmed that no row controls were allocated. P2 creates/binds them during native Single-page creation (025E79D8, first instruction9421FFC8), rather than during page entry/calc. Correct entry verified against the preceding return and full stack prologue. This avoids allocating after the native creation heap scope. Host row-model tests and PPC compile/roundtrip pass. P2 installed only in isolated Cemu; visual/interaction validation pending. Do not export as a validated Wii U release yet.

Artifacts: work/options_i18n/Turbo_Options_NativeRows_P2.rpx and menu_native_rows_p1.szs. Previous RPX/menu backed up under work/options_i18n/before_native_rows. Cemu helper PID12636, debugger active, cleanup attached. No original save changes or account files packaged.

## Compact rows P3

User screenshot confirmed that P2's type-5 native pattern selected a stacked competition layout: three touching blocks, hidden titles, value displayed above an empty box. P3 removes G_Ptn_00 bindings only in the private row copy, and limits its native InOut group to N_All_00. Stock common/VS files remain unchanged. The alternate N_All_01 branch is kept hidden, and both title/value text panes are explicitly visible. Original compact positions remain label-left/value-right. Row centers now175,0,-175 (175 spacing instead of120). Built and installed in isolated Cemu with P2 backup; host/model checks and RPX/archive roundtrips passed. Actual visual result remains pending.

## P4 layout / P5 behavior

User confirmed P3 labels are visible but arrows protrude beyond the screen; requested small centered selectors with titles above. Private row P4 centers the title at(0,65), moves N_Change_00 to(0,0), reduces B_List_00/N_All_00/L_Btn_LR bounds to440 and hides the880-wide divider. Centers145/0/-145. Native touch-arrow initialization uses the bound, so shrinking only the value picture was insufficient. Archive roundtrip and saved geometry/hidden-divider checks passed.

User also reported mixed language in first online menu, Battle button, GP/TT class selection, cups/courses; and invisible Options controls in Solo. P5:

- Records native numeric message assignments at025367AC,025367E8,02536848. At the generic live Page calc0253E744 (entry verified mflr, followed by own stack allocation), refreshes old language-epoch assignments only for controls enumerated in that live page's current control array and still using the captured layout. Saved page/control pointers are compared, not dereferenced as candidates. Cache has1024 binding slots,128 page epochs and an overflow counter. No per-frame rebuild when language is unchanged.
- Updates the game's RAM-only locale region/language pair at context+2D0 (+4 region,+8 language), using the verified1018A30C EUR matrix. Auto restores originals. This supplements the locale-prefix and message lookup hooks; no OS/account/save writes.
- Restores all FOUR ordinary Solo button messages, including Battle (previous loop covered only three).
- Removes appended Options rows from both page update/input and navigation lists outside Options; restores the lists on entry. Row callbacks additionally reject changes while Options is closed.
- The compiler's default4KiB state reservation stays unchanged; only Options opts into64KiB for the message-binding cache.

Host checks cover hidden-list removal, inactive callbacks, locale Auto restoration, once-per-epoch cached-message refresh and skipping replaced layouts. Host/PPC compile and archive/RPX roundtrips passed. P5 RPX + P4 menu installed only in isolated Cemu; prior files backed up under before_rows_p5. Runtime validation of all reported menus remains pending. No updated Wii U release produced.

## P6 focus regression

User could not select any ordinary Solo button after Options. Live P5 capture: options0, row_page_count4, row_page_end10, row_nav_count4, row_nav_end7; active counts4/4 but native controller0 focus index6. Ordinary controls still enabled (byte18=1, flags38=FFFFFFFF). P5 removed the selected Options entry before repairing remembered focus.

P6 moves each controller's selected index4..6 to native index0 BEFORE reducing list counts, keeping old and new entries addressable during native deselect/select callbacks. Normal Solo entry also explicitly focuses index0 after restoring visible controls. The host regression now starts at captured index6/count7, deactivates Options and checks resulting index0/count4. Host and PPC/RPX roundtrip pass. Artifact Turbo_Options_NativeRows_P6.rpx prepared; Cemu PID36796 still open, user asked to close for install. P6 runtime validation pending.
