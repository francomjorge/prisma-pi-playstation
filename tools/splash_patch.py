#!/usr/bin/env python3
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
s = path.read_text()

replacements = [
    (
        "static LOGO_CLUT_BYTES: [u8; 32] = make_logo_palette();\n",
        """static LOGO_CLUT_BYTES: [u8; 32] = make_logo_palette();

// 320x240 presentation artwork, converted at build time to 8-bit indexed
// pixels followed by a 256-entry RGB555 CLUT.
static PRESENTATION_ASSET: &[u8] = include_bytes!(\"presentation_ps1.bin\");
const PRESENT_LEFT_BYTES: usize = 256 * 240;
const PRESENT_RIGHT_BYTES: usize = 64 * 240;
const PRESENT_CLUT_OFFSET: usize = PRESENT_LEFT_BYTES + PRESENT_RIGHT_BYTES;
const PRESENT_TPAGE_LEFT: TexturePage = TexturePage::new(640, 256, TextureDepth::Bit8);
const PRESENT_TPAGE_RIGHT: TexturePage = TexturePage::new(768, 256, TextureDepth::Bit8);
const PRESENT_CLUT: Clut = Clut::new(256, 496);
""",
        "presentation asset constants",
    ),
    (
        "enum Screen {\n    Home,",
        "enum Screen {\n    Splash,\n    Home,",
        "splash enum",
    ),
    (
        "    upload_prisma_image();\n",
        "    upload_prisma_image();\n    upload_presentation_image();\n",
        "presentation upload",
    ),
    (
        "    let mut screen = Screen::Home;\n",
        "    let mut screen = Screen::Splash;\n",
        "initial screen",
    ),
    (
        "    let mut audio = AudioTestState::INIT;\n",
        "    let mut audio = AudioTestState::INIT;\n    let mut frame_counter: u32 = 0;\n",
        "frame counter",
    ),
    (
        """        match screen {
            Screen::Home => {
""",
        """        match screen {
            Screen::Splash => {
                if confirm_pressed(pressed) || just_pressed(pressed, button::SELECT) {
                    screen = Screen::Home;
                }
            }
            Screen::Home => {
""",
        "splash controls",
    ),
    (
        """        let bg = match screen {
            Screen::Home => (5, 7, 12),
""",
        """        let bg = match screen {
            Screen::Splash => (0, 0, 0),
            Screen::Home => (5, 7, 12),
""",
        "splash background",
    ),
    (
        """        match screen {
            Screen::Home => render_home(&font, home_selection, pad_state),
""",
        """        match screen {
            Screen::Splash => render_splash(&font, frame_counter),
            Screen::Home => render_home(&font, home_selection, pad_state),
""",
        "splash render arm",
    ),
    (
        """        previous_bits = bits;

        if audio.flash != 0 {
""",
        """        previous_bits = bits;
        frame_counter = frame_counter.wrapping_add(1);

        if audio.flash != 0 {
""",
        "frame increment",
    ),
    (
        "fn upload_prisma_image() {\n",
        """fn upload_presentation_image() {
    // The 8-bit texture is 320 pixels wide. The first 256 pixels occupy
    // 128 VRAM words; the final 64 pixels occupy another 32 words.
    let left_rect = VramRect::new(
        PRESENT_TPAGE_LEFT.x(),
        PRESENT_TPAGE_LEFT.y(),
        128,
        240,
    );
    upload_bytes(left_rect, &PRESENTATION_ASSET[..PRESENT_LEFT_BYTES]);

    let right_rect = VramRect::new(
        PRESENT_TPAGE_RIGHT.x(),
        PRESENT_TPAGE_RIGHT.y(),
        32,
        240,
    );
    upload_bytes(
        right_rect,
        &PRESENTATION_ASSET[PRESENT_LEFT_BYTES..PRESENT_CLUT_OFFSET],
    );

    let clut_rect = VramRect::new(PRESENT_CLUT.x(), PRESENT_CLUT.y(), 256, 1);
    upload_bytes(clut_rect, &PRESENTATION_ASSET[PRESENT_CLUT_OFFSET..]);
}

fn draw_presentation_image() {
    PRESENT_TPAGE_LEFT.apply_as_draw_mode();
    wait_command_ready();
    write_command(psx_hw::gpu::packet::TEXTURED_RECT | pack_color(0x80, 0x80, 0x80));
    write_command(pack_vertex(0, 0));
    write_command(pack_texcoord(0, 0, PRESENT_CLUT.uv_word()));
    write_command(pack_xy(256, 240));

    PRESENT_TPAGE_RIGHT.apply_as_draw_mode();
    wait_command_ready();
    write_command(psx_hw::gpu::packet::TEXTURED_RECT | pack_color(0x80, 0x80, 0x80));
    write_command(pack_vertex(256, 0));
    write_command(pack_texcoord(0, 0, PRESENT_CLUT.uv_word()));
    write_command(pack_xy(64, 240));
}

fn render_splash(font: &FontAtlas, frame: u32) {
    draw_presentation_image();

    // A small live shimmer rides along the PRISMA-PI underline. The artwork
    // itself stays untouched; this GPU overlay proves we are drawing a new
    // animated layer every frame.
    const TINTS: [(u8, u8, u8); 4] = [
        (0x30, 0xD8, 0xF0),
        (0xF0, 0x30, 0xD8),
        (0xF0, 0xD8, 0x30),
        (0xB0, 0xE8, 0xF0),
    ];
    let tint = TINTS[((frame / 8) & 3) as usize];
    let scan_x = 72 + ((frame / 2) % 176) as i16;
    draw_rect(scan_x, 109, 18, 1, tint);

    // Pulse the two colored PI accents independently.
    let phase = ((frame / 10) & 1) as u8;
    let p_tint = if phase == 0 { (0xF0, 0x30, 0xD0) } else { (0xD0, 0x70, 0xF0) };
    let i_tint = if phase == 0 { (0x20, 0xE0, 0xD8) } else { (0x70, 0xF0, 0xB0) };
    draw_rect(178, 106, 11, 1, p_tint);
    draw_rect(194, 106, 5, 1, i_tint);

    if ((frame / 30) & 1) == 0 {
        font.draw_text(112, 222, \"PRESS START\", tint);
    }
}

fn upload_prisma_image() {
""",
        "presentation functions",
    ),
]

for old, new, label in replacements:
    if old not in s:
        raise SystemExit(f"splash patch failed: {label} pattern not found")
    s = s.replace(old, new, 1)

path.write_text(s)
print(f"Applied presentation splash + live GPU shimmer to {path}")
