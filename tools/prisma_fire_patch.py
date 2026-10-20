#!/usr/bin/env python3
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
s = path.read_text()

old = '''const INDIA_UI_CLUT: Clut = Clut::new(0, 497);\n'''
new = '''const INDIA_UI_CLUT: Clut = Clut::new(0, 497);\n\n// Animated PRISMA- title: six fire frames, 128x192 8-bit atlas.\n// Palette index 0 is transparent; PI and INDIA remain baked/static.\nstatic PRISMA_FIRE_ASSET: &[u8] = include_bytes!("prisma_fire_ps1.bin");\nconst PRISMA_FIRE_PIXELS: usize = 128 * 192;\nconst PRISMA_FIRE_TPAGE: TexturePage = TexturePage::new(768, 0, TextureDepth::Bit8);\nconst PRISMA_FIRE_CLUT: Clut = Clut::new(256, 497);\n'''
if old not in s:
    raise SystemExit('prisma fire patch failed: INDIA UI constants anchor not found')
s = s.replace(old, new, 1)

old = '''                        upload_india_image();\n                        upload_india_ui();\n                        screen = Screen::Prisma;\n'''
new = '''                        upload_india_image();\n                        upload_india_ui();\n                        upload_prisma_fire();\n                        screen = Screen::Prisma;\n'''
if old not in s:
    raise SystemExit('prisma fire patch failed: INDIA entry anchor not found')
s = s.replace(old, new, 1)

anchor = '''fn upload_india_ui() {\n'''
insert = '''fn upload_prisma_fire() {\n    // 8bpp: 128 texels wide = 64 VRAM words. Six 32px-high frames.\n    let pixel_rect = VramRect::new(PRISMA_FIRE_TPAGE.x(), PRISMA_FIRE_TPAGE.y(), 64, 192);\n    upload_bytes(pixel_rect, &PRISMA_FIRE_ASSET[..PRISMA_FIRE_PIXELS]);\n\n    let clut_rect = VramRect::new(PRISMA_FIRE_CLUT.x(), PRISMA_FIRE_CLUT.y(), 256, 1);\n    upload_bytes(clut_rect, &PRISMA_FIRE_ASSET[PRISMA_FIRE_PIXELS..]);\n}\n\nfn draw_prisma_fire(frame: u32) {\n    // Ping-pong through the six flame frames to avoid a visible hard loop.\n    const SEQUENCE: [u8; 10] = [0, 1, 2, 3, 4, 5, 4, 3, 2, 1];\n    let index = SEQUENCE[((frame / 6) % SEQUENCE.len() as u32) as usize];\n    let v = index * 32;\n\n    PRISMA_FIRE_TPAGE.apply_as_draw_mode();\n    wait_command_ready();\n    write_command(psx_hw::gpu::packet::TEXTURED_RECT | pack_color(0x80, 0x80, 0x80));\n    write_command(pack_vertex(166, 21));\n    write_command(pack_texcoord(0, v, PRISMA_FIRE_CLUT.uv_word()));\n    write_command(pack_xy(105, 30));\n}\n\nfn upload_india_ui() {\n'''
if anchor not in s:
    raise SystemExit('prisma fire patch failed: upload_india_ui anchor not found')
s = s.replace(anchor, insert, 1)

old = '''fn render_india(selection: u8, frame: u32, values: &[u8; 6]) {\n    draw_india_image();\n'''
new = '''fn render_india(selection: u8, frame: u32, values: &[u8; 6]) {\n    draw_india_image();\n    // Only PRISMA- animates; PI and INDIA remain part of the static master artwork.\n    draw_prisma_fire(frame);\n'''
if old not in s:
    raise SystemExit('prisma fire patch failed: render_india anchor not found')
s = s.replace(old, new, 1)

path.write_text(s)
print(f'Applied six-frame PRISMA- fire animation to {path}')
