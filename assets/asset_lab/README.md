# PRISMA-PI Asset Lab

Pilot batch 01 is intentionally isolated from the stable main branch.

Addressable resources reserved by the Asset Browser:

- `0x0002` `CP437_SYMBOLS` — 8x8 glyph cells, 16x16 grid / 128x128 atlas target.
- `0x0011` `UI_KNOB` — 32x32, 8 states/frames target.
- `0x0020` `TEX_METAL` — 64x64 target.
- `0x0043` `GHOST_ASCII_32` — 32x32, 8 animation frames target.

Pipeline rule: source art -> deterministic cooker -> indexed pixels/CLUT -> AssetId -> VRAM upload -> Asset Browser render.

The source-art and cooked-binary stages are not marked complete until the exact pixels/palette have been generated and visually verified. This directory therefore tracks the pilot batch without pretending placeholder art is final.
