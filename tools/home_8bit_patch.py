#!/usr/bin/env python3
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
s = path.read_text()

old_constants = '''// 320x240 HOME artwork, stored as 4-bit indexed pixels + 16-entry RGB555 CLUT.
// Split at x=256 because PS1 texture pages address at most 256 texels per page.
static HOME_ASSET: &[u8] = include_bytes!("home_ps1.bin");
const HOME_LEFT_BYTES: usize = 128 * 240;
const HOME_RIGHT_BYTES: usize = 32 * 240;
const HOME_CLUT_OFFSET: usize = HOME_LEFT_BYTES + HOME_RIGHT_BYTES;
const HOME_TPAGE_LEFT: TexturePage = TexturePage::new(832, 256, TextureDepth::Bit4);
const HOME_TPAGE_RIGHT: TexturePage = TexturePage::new(896, 256, TextureDepth::Bit4);
const HOME_CLUT: Clut = Clut::new(512, 496);
'''
new_constants = '''// 320x240 HOME master artwork, stored as 8-bit indexed pixels + 256-entry RGB555 CLUT.
// The image itself contains the complete dashboard, labels and both menu cards.
static HOME_ASSET: &[u8] = include_bytes!("home_ps1.bin");
const HOME_LEFT_BYTES: usize = 256 * 240;
const HOME_RIGHT_BYTES: usize = 64 * 240;
const HOME_CLUT_OFFSET: usize = HOME_LEFT_BYTES + HOME_RIGHT_BYTES;
const HOME_TPAGE_LEFT: TexturePage = TexturePage::new(832, 256, TextureDepth::Bit8);
const HOME_TPAGE_RIGHT: TexturePage = TexturePage::new(960, 256, TextureDepth::Bit8);
const HOME_CLUT: Clut = Clut::new(512, 496);
'''
if old_constants not in s:
    raise SystemExit('home 8bit patch failed: constants not found')
s = s.replace(old_constants, new_constants, 1)

old_render = '''fn render_home(font: &FontAtlas, selection: u8, frame: u32) {
    draw_home_image();

    // Keep the low-resolution HOME deliberately simple. Cover the baked card
    // captions from the concept artwork and redraw only the two large labels.
    draw_rect(20, 173, 138, 45, (0x08, 0x12, 0x20));
    draw_rect(162, 173, 139, 45, (0x12, 0x08, 0x20));

    // PRISMA-PI: P and I get independent colors so they survive clearly at 320x240.
    font.draw_text(53, 190, "PRISMA-", (0xD8, 0xF0, 0xF0));
    font.draw_text(109, 190, "P", (0xF0, 0x38, 0xD8));
    font.draw_text(117, 190, "I", (0x30, 0xE8, 0xF0));
    font.draw_text(195, 190, "TEST MODE", (0xF0, 0xE8, 0xF0));

    let pulse = ((frame / 10) & 1) == 0;
    let cyan = if pulse { (0x30, 0xE8, 0xF0) } else { (0x20, 0xA0, 0xC0) };
    let magenta = if pulse { (0xF0, 0x40, 0xD8) } else { (0xB0, 0x20, 0xA0) };

    if selection == 0 {
        draw_outline(18, 171, 142, 49, cyan);
        let scan_x = 21 + ((frame / 2) % 132) as i16;
        draw_rect(scan_x, 172, 8, 1, (0xD0, 0xF8, 0xFF));
    } else {
        draw_outline(160, 171, 143, 49, magenta);
        let scan_x = 163 + ((frame / 2) % 132) as i16;
        draw_rect(scan_x, 172, 8, 1, (0xFF, 0x90, 0xE8));
    }
}
'''
new_render = '''fn render_home(_font: &FontAtlas, selection: u8, frame: u32) {
    // The complete HOME composition is baked into the 8-bit texture.
    // Only the selector is drawn live on top of it.
    draw_home_image();

    let pulse = ((frame / 10) & 1) == 0;
    let cyan = if pulse { (0x30, 0xE8, 0xF0) } else { (0x20, 0xA0, 0xC0) };
    let magenta = if pulse { (0xF0, 0x40, 0xD8) } else { (0xB0, 0x20, 0xA0) };

    if selection == 0 {
        draw_outline(18, 171, 142, 49, cyan);
        let scan_x = 21 + ((frame / 2) % 132) as i16;
        draw_rect(scan_x, 172, 8, 1, (0xD0, 0xF8, 0xFF));
    } else {
        draw_outline(160, 171, 143, 49, magenta);
        let scan_x = 163 + ((frame / 2) % 132) as i16;
        draw_rect(scan_x, 172, 8, 1, (0xFF, 0x90, 0xE8));
    }
}
'''
if old_render not in s:
    raise SystemExit('home 8bit patch failed: render_home not found')
s = s.replace(old_render, new_render, 1)

old_upload = '''fn upload_home_image() {
    // 4bpp: four texels per VRAM word. 256px -> 64 words, 64px -> 16 words.
    let left_rect = VramRect::new(
        HOME_TPAGE_LEFT.x(),
        HOME_TPAGE_LEFT.y(),
        64,
        240,
    );
    upload_bytes(left_rect, &HOME_ASSET[..HOME_LEFT_BYTES]);

    let right_rect = VramRect::new(
        HOME_TPAGE_RIGHT.x(),
        HOME_TPAGE_RIGHT.y(),
        16,
        240,
    );
    upload_bytes(
        right_rect,
        &HOME_ASSET[HOME_LEFT_BYTES..HOME_CLUT_OFFSET],
    );

    let clut_rect = VramRect::new(HOME_CLUT.x(), HOME_CLUT.y(), 16, 1);
    upload_bytes(clut_rect, &HOME_ASSET[HOME_CLUT_OFFSET..]);
}

fn draw_home_image() {
    HOME_TPAGE_LEFT.apply_as_draw_mode();
    wait_command_ready();
    write_command(psx_hw::gpu::packet::TEXTURED_RECT | pack_color(0x80, 0x80, 0x80));
    write_command(pack_vertex(0, 0));
    write_command(pack_texcoord(0, 0, HOME_CLUT.uv_word()));
    write_command(pack_xy(256, 240));

    HOME_TPAGE_RIGHT.apply_as_draw_mode();
    wait_command_ready();
    write_command(psx_hw::gpu::packet::TEXTURED_RECT | pack_color(0x80, 0x80, 0x80));
    write_command(pack_vertex(256, 0));
    write_command(pack_texcoord(0, 0, HOME_CLUT.uv_word()));
    write_command(pack_xy(64, 240));
}
'''
new_upload = '''fn upload_home_image() {
    // 8bpp: two texels per VRAM word. 256px -> 128 words, 64px -> 32 words.
    let left_rect = VramRect::new(
        HOME_TPAGE_LEFT.x(),
        HOME_TPAGE_LEFT.y(),
        128,
        240,
    );
    upload_bytes(left_rect, &HOME_ASSET[..HOME_LEFT_BYTES]);

    let right_rect = VramRect::new(
        HOME_TPAGE_RIGHT.x(),
        HOME_TPAGE_RIGHT.y(),
        32,
        240,
    );
    upload_bytes(
        right_rect,
        &HOME_ASSET[HOME_LEFT_BYTES..HOME_CLUT_OFFSET],
    );

    let clut_rect = VramRect::new(HOME_CLUT.x(), HOME_CLUT.y(), 256, 1);
    upload_bytes(clut_rect, &HOME_ASSET[HOME_CLUT_OFFSET..]);
}

fn draw_home_image() {
    HOME_TPAGE_LEFT.apply_as_draw_mode();
    wait_command_ready();
    write_command(psx_hw::gpu::packet::TEXTURED_RECT | pack_color(0x80, 0x80, 0x80));
    write_command(pack_vertex(0, 0));
    write_command(pack_texcoord(0, 0, HOME_CLUT.uv_word()));
    write_command(pack_xy(256, 240));

    HOME_TPAGE_RIGHT.apply_as_draw_mode();
    wait_command_ready();
    write_command(psx_hw::gpu::packet::TEXTURED_RECT | pack_color(0x80, 0x80, 0x80));
    write_command(pack_vertex(256, 0));
    write_command(pack_texcoord(0, 0, HOME_CLUT.uv_word()));
    write_command(pack_xy(64, 240));
}
'''
if old_upload not in s:
    raise SystemExit('home 8bit patch failed: upload/draw block not found')
s = s.replace(old_upload, new_upload, 1)

path.write_text(s)
print(f'Applied native 8-bit baked HOME artwork to {path}')
