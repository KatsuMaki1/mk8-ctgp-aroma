# Installing the CTGP-Café for MK8 plugin on a Wii U (Aroma)

**Status: not tested on a real console yet.** Everything below has been run in Cemu; the plugin itself builds and follows the same loading
rules as the original CTGP-Café release. Read "If something goes wrong" before you try.

## What you need
- A Wii U running the **Aroma** environment (a current release, with the *ContentRedirection* and *Notifications* modules, which are part of the
  standard Aroma download).
- **Mario Kart 8, European version, with the v81 update installed** (title id `00050000-1010ED00`). The code pack in this folder is built
  for that exact game version; other regions or versions need their own pack (`tools/mkpack.py`).
- An SD card (FAT32) with about **1.5 GB** free.

## Install
1. Copy the **contents of the `sd` folder** to the **root of your SD card**, merging folders if they already exist. You should end up with:
   - `sd:/wiiu/environments/aroma/plugins/mk8-ct.wps`
   - `sd:/cafeloader/000500001010ED00/` (`Addr.bin`, `Code.bin`, `Data.bin`, `Patches.hax`, `Verify.hax`)
   - `sd:/cafeloader/vol/000500001010ED00/content/` (`data.cup0`, `course/`, `mapobj/`, `ui/`, `custom/`, `audio/`, ...)
2. Put the SD card in the console and boot into **Aroma** (the Aroma menu with the plugin loader).
3. Start **Mario Kart 8** from the Wii U menu (disc or installed copy).  The plugin only acts when Mario Kart 8 starts: it patches the game's code
   in memory and adds the CTGP files on top of the game's content. Nothing on the console or the game is modified permanently.
4. In the cup selection screen use the **L/R buttons** to change page: the CTGP cups are on the last pages.

## Uninstall
Delete `sd:/wiiu/environments/aroma/plugins/mk8-ct.wps` (and, if you want, `sd:/cafeloader` and `sd:/wiiu/mk8-ct`). Restart the console.

## If something goes wrong
- **The console does not boot or loops:** power it off, take the SD card out, delete `mk8-ct.wps` from `wiiu/environments/aroma/plugins/`,
  and boot again. The plugin never writes to the console's memory.
- **The game starts normally but there are no CTGP cups:** create these empty files on the SD card to see what the plugin does
  (a file with no content is enough; on Windows, create a text file and remove the `.txt`):
  - `sd:/wiiu/mk8-ct/log_file` – the plugin writes `sd:/wiiu/mk8-ct/log.txt`.
  - `sd:/wiiu/mk8-ct/notif` – the plugin shows an on-screen notification when it is done.
  Check that the title id in the log is `000500001010ED00` and that "Verify" passed. If it says the game's memory does not match, your
  game is not the v81 EUR build this pack was made for.
- **Isolating a problem** (empty files in `sd:/wiiu/mk8-ct/`): `no_code` (content only, no code patches), `no_content` (code patches only),
  `skip_<folder>` (for example `skip_audio`, `skip_mapobj`, `skip_ui`, `skip_course`, `skip_custom`, `skip_charger`, `skip_cup0`).

## Known limitations
- Custom tracks added by this toolkit may be **silent**: the game picks the music from the slot a track sits in. This is being worked on.
- The track name and picture shown on the "Solo race" screen and at the race start can be those of the original track of the same slot.
- Only 6 CTGP cups and 4 tracks per cup (plus the 12 game DLC cups, which can also be edited).
- Skies and map objects are shared by all tracks (one file per name): two tracks that need different skies with the same name conflict.

## Rebuilding this folder
```
python tools/build_dist.py --content <Cemu update content> --base-game <MK8 base content> --release-zip ctgp_cafe_wiiu.zip \
  --v64-rpx Turbo_v64.rpx --v81-rpx Turbo_v81.rpx --plugin plugin/mk8-ct.wps --title-id 000500001010ED00 --out dist
```
The plugin: install devkitPro + WUPS + `libcontentredirection` + `libnotifications`, then run `make` in `plugin/`.
