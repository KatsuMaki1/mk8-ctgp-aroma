# Wii Remote cup-page controls

EUR v81 patch: map Wii Remote Minus to the existing CTGP L action and Plus
to its R action, only while polling cup-page arrow inputs on GP (0x2B), VS
(0x2C) and online course selection (0x3F). GamePad, Classic and Pro inputs
are passed through. MotionPlus and Nunchuk configurations are included.

`tools/native/wiimote_cups.c` wraps native `ui::Input_Key` polling at
0x0253C31C. It temporarily translates the selected UI manager's pressed
(+0x54) and pressed/repeat (+0x58) flags, calls the original poll function,
then restores both fields. Native focus, transition guards, event handling,
page wrapping and sounds remain responsible for acting on the input.
Holding or combining keys is not converted into synthetic repeated events.

Evidence from the actual native code:

* 0x0250CF08 selects 13-entry secondary/UI input maps at 0x100CDE90
  (Remote/MotionPlus) and 0x100CDEC4 (Nunchuk). Their logical bits 3/4 are
  Plus/Minus, while X/Y on the GamePad use logical bits 9/10. The old source
  header incorrectly aliases the latter with Plus/Minus.
* 0x024CB508 returns device kinds: GamePad 1, Remote 2, MotionPlus 3,
  Nunchuk 4, Classic 5, Pro 7. 0x0256403C caches this at UI manager +0x60.
* CTGP handles L/R as 0x800/0x1000 in the common cup-event function at
  0x02B14024. The wrapper targets only these two required-input masks.

`tools/wiimote_cups.py` appends the module to the current Cemu RPX and to
the latest Bolt/Online Sync Test 4 console code pack, preserving existing
payloads and extending section reservations. Both outputs have readback/
hash checks. The console pack has 81 matching patch/verification sites.

Tests: `tests/wiimote_cups_host.c` covers mapping, simultaneous buttons,
other pages/devices and X/Y; `tests/wiimote_cups_wrapper_host.c` covers the
whole wrapper, all three pages, supported devices, four players and the
native fallback index, state restoration, and native callback effects.
The original button maps and expected native hook word are also checked.

Artifacts are in organized outputs/Cemu and
outputs/WiiU/Mises_a_jour/WiiU_Wiimote_Cups(.zip). The console ZIP contains
only sd/. Apply its contents to the SD root with MK8 closed. The expanded
folder has a separate rollback/sd tree restoring the prior six code files.
No plugin, track, UI layout or R2 optimization file needs replacement.

The Cemu RPX was installed after the emulator was closed, with the prior
RPX backed up under the chat workspace's work/wiimote_cups_backup. Startup
was observed running; the user then confirmed that the Cemu test works.
This does not establish real Wii Remote behavior on console, which still
needs hardware confirmation. The console ZIP is 30,911 bytes and contains
only the sd/ tree with the six updated code-pack files.
