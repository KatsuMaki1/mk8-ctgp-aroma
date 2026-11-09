# CTGP Cafe 8 branding, Cemu integration (2026-10-31)

User supplied Downloads/menu.szs and Downloads/boot (1).szs. Their CTGP Cafe 8
logo was visually inspected from decoded source textures. Do not replace the
current character/cup menus wholesale with the supplied older menu archive.

Installed resources under the Cemu EUR81 update content:

* ui/cmn/menu.szs: texture BC5FFE13 and title-logo-only layout9A7A5A0E from the
  upload. The latter retains the matching material/texture order, placement and
  hidden old right-logo pane. Hidden right-logo resource29458B59 aliases the
  left logo payload to avoid retaining another large obsolete logo image.
  All1143 unrelated members, including both ROB selection layouts and vehicle
  icons, are byte-identical to the pre-branding menu.
* ui/cmn/boot.szs: only texture7A38CD39 and mask7BFF3107 changed from base.
  All15 other members are byte-identical; decompressed size unchanged.

The first merge without aliasing crashed loading mn_ModeSlct_00. The capture is
saved under work/rob/ctgp_logo/first_logo_boot_crash.*. The final aliased menu is
27,654,184 bytes decompressed, 221,184 bytes smaller than the pre-branding menu.
No image resizing, re-encoding or unrelated texture changes were needed.

Final installed menu SHA256:
4f1f1bee4edacb752261454451c30f95ee258acfe338b226cfc22f40ce8c4786

Final installed boot SHA256:
f1c40ef67b78c963f6535ea0b755ed95384197c1552ee7f196e88b18b20562fa

Revisions ctgp8_uploaded_logo_textures and ctgp8_logo_shared_texture are tracked
by code_backups/IndependentROB. The original full rollback remains intact. The
boot override did not exist before this integration and is tracked as new.
Tools/native code and installed R19 RPX were not changed by logo integration.

Twenty-one character/archive tests pass, including alias range validity and
preservation of unrelated resources. Final debug launch PID28976 passed the
prior boot crash. Computer Use observation showed the game at60 FPS on ROB's
vehicle selector, with the black ATV and glider icons visible. The live title
logo itself was not observed because the user had already entered selection.
The R19 horn and formerly missing-icon user test remains pending.

Preparation/install scripts and manifests: work/rob/ctgp_logo,
work/rob/prepare_logo_install.py and work/rob/install_logo.py. Source uploads
were not modified. No Wii U/Aroma bundle has been updated with these logos yet.

The final boot is the user's boot (2).szs, revision ctgp8_boot_logo_v2. Only
member 7BFF3107 differs from the previous boot. On the subsequent Booster48
launch, both the boot logo and the CTGP8 title-screen logo were observed in
Cemu, followed by the vehicle selector without a boot crash.
