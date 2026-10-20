#!/usr/bin/env python3
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
s = path.read_text()

replacements = [
    (
        "const PRESENT_CLUT: Clut = Clut::new(256, 496);\n",
        """const PRESENT_CLUT: Clut = Clut::new(256, 496);

// 320x240 HOME artwork, stored as 4-bit indexed pixels + 16-entry RGB555 CLUT.
// Split at x=256 because PS1 texture pages address at most 256 texels per page.
static HOME_ASSET: &[u8] = include_bytes!(\"home_ps1.bin\");
const HOME_LEFT_BYTES: usize = 128 * 240;
const HOME_RIGHT_BYTES: usize = 32 * 240;
const HOME_CLUT_OFFSET: usize = HOME_LEFT_BYTES + HOME_RIGHT_BYTES;
const HOME_TPAGE_LEFT: TexturePage = TexturePage::new(832, 256, TextureDepth::Bit4);
const HOME_TPAGE_RIGHT: TexturePage = TexturePage::new(896, 256, TextureDepth::Bit4);
const HOME_CLUT: Clut = Clut::new(512, 496);
""",
        "home asset constants",
    ),
    (
        "    upload_prisma_image();\n    upload_presentation_image();\n",
        "    upload_prisma_image();\n    upload_presentation_image();\n    upload_home_image();\n",
        "home upload call",
    ),
    (
        """            Screen::Home => {
                if just_pressed(pressed, button::UP) || just_pressed(pressed, button::DOWN) {
                    home_selection ^= 1;
                }
                if confirm_pressed(pressed) {
                    screen = if home_selection == 0 { Screen::Prisma } else { Screen::TestMenu };
                }
            }
""",
        """            Screen::Home => {
                // HOME is a two-card horizontal browser: LEFT / RIGHT only.
                if just_pressed(pressed, button::LEFT) || just_pressed(pressed, button::RIGHT) {
                    home_selection ^= 1;
                }
                if confirm_pressed(pressed) {
                    screen = if home_selection == 0 { Screen::Prisma } else { Screen::TestMenu };
                }
            }
""",
        "horizontal home navigation",
    ),
    (
        "Screen::Home => render_home(&font, home_selection, pad_state),",
        "Screen::Home => render_home(&font, home_selection, frame_counter),",
        "home render call",
    ),
    (
        """fn render_home(font: &FontAtlas, selection: u8, state: PadState) {
    draw_prisma_image(112, 18, 96, 48);
    font.draw_text(100, 74, \"PRISMA-PI\", (0x70, 0xD0, 0xD0));
    font.draw_text(72, 88, \"PLAYSTATION SYNTH LAB\", (0x70, 0x70, 0x80));
    draw_menu_row(font, 0, selection, 92, 126, 136, \"PRISMA-PI\");
    draw_menu_row(font, 1, selection, 92, 154, 164, \"TEST MODE\");

    font.draw_text(16, 184, \"PAD:\", (0x60, 0x60, 0x68));
    font.draw_text(56, 184, pad_mode_label(state.mode), pad_mode_tint(state.mode));
    font.draw_text(160, 184, \"ID:\", (0x60, 0x60, 0x68));
    let id = hex_u8(state.id_low);
    font.draw_text(192, 184, &id, (0x70, 0x90, 0x90));

    font.draw_text(16, 198, \"BITS:\", (0x60, 0x60, 0x68));
    let raw = hex_u16(state.buttons.bits());
    font.draw_text(64, 198, &raw, (0x70, 0xD0, 0xD0));
    font.draw_text(184, 198, \"NOACK\", (0xD0, 0x90, 0x50));

    font.draw_text(76, 220, \"UP/DOWN  START OR CROSS\", (0x60, 0x60, 0x68));
}
""",
        """fn render_home(font: &FontAtlas, selection: u8, frame: u32) {
    draw_home_image();

    // Keep the low-resolution HOME deliberately simple. Cover the baked card
    // captions from the concept artwork and redraw only the two large labels.
    draw_rect(20, 173, 138, 45, (0x08, 0x12, 0x20));
    draw_rect(162, 173, 139, 45, (0x12, 0x08, 0x20));

    // PRISMA-PI: P and I get independent colors so they survive clearly at 320x240.
    font.draw_text(53, 190, \"PRISMA-\", (0xD8, 0xF0, 0xF0));
    font.draw_text(109, 190, \"P\", (0xF0, 0x38, 0xD8));
    font.draw_text(117, 190, \"I\", (0x30, 0xE8, 0xF0));
    font.draw_text(195, 190, \"TEST MODE\", (0xF0, 0xE8, 0xF0));

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
""",
        "graphical home render",
    ),
    (
        "fn upload_presentation_image() {\n",
        """fn upload_home_image() {
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

fn draw_outline(x: i16, y: i16, w: u16, h: u16, color: (u8, u8, u8)) {
    draw_rect(x, y, w, 1, color);
    draw_rect(x, y + h as i16 - 1, w, 1, color);
    draw_rect(x, y, 1, h, color);
    draw_rect(x + w as i16 - 1, y, 1, h, color);
}

fn upload_presentation_image() {
""",
        "home texture functions",
    ),
    (
        """            Screen::ControllerMap => {
                seen_buttons |= bits;
                if held(bits, button::START) && held(bits, button::SELECT) {
                    screen = Screen::TestMenu;
                } else if held(bits, button::L3) && held(bits, button::R3) {
                    seen_buttons = 0;
                }
            }
""",
        """            Screen::ControllerMap => {
                seen_buttons |= bits;
                if held(bits, button::START) && held(bits, button::SELECT) {
                    screen = Screen::TestMenu;
                }
            }
""",
        "remove L3/R3 mapper action",
    ),
    (
        """    if just_pressed(pressed, button::L2) {
        state.sample = if state.sample == 0 { (AUDIO_SAMPLE_COUNT - 1) as u8 } else { state.sample - 1 };
    }
    if just_pressed(pressed, button::R2) {
        state.sample = (state.sample + 1) % AUDIO_SAMPLE_COUNT as u8;
    }
""",
        """    // Keep the instrument compatible with simple digital PS1 pads:
    // TRIANGLE cycles the sample bank; L1/R1 stay dedicated to voice select.
    if just_pressed(pressed, button::TRIANGLE) {
        state.sample = (state.sample + 1) % AUDIO_SAMPLE_COUNT as u8;
    }
""",
        "remove L2/R2 audio actions",
    ),
    (
        """    const LEFT: [(u16, &str); 8] = [
        (button::UP, \"UP\"),
        (button::RIGHT, \"RIGHT\"),
        (button::DOWN, \"DOWN\"),
        (button::LEFT, \"LEFT\"),
        (button::L1, \"L1\"),
        (button::L2, \"L2\"),
        (button::L3, \"L3\"),
        (button::SELECT, \"SELECT\"),
    ];
    const RIGHT: [(u16, &str); 8] = [
        (button::TRIANGLE, \"TRIANGLE\"),
        (button::CIRCLE, \"CIRCLE\"),
        (button::CROSS, \"CROSS\"),
        (button::SQUARE, \"SQUARE\"),
        (button::R1, \"R1\"),
        (button::R2, \"R2\"),
        (button::R3, \"R3\"),
        (button::START, \"START\"),
    ];

    let bits = state.buttons.bits();
    let mut row: usize = 0;
    while row < 8 {
""",
        """    const LEFT: [(u16, &str); 6] = [
        (button::UP, \"UP\"),
        (button::RIGHT, \"RIGHT\"),
        (button::DOWN, \"DOWN\"),
        (button::LEFT, \"LEFT\"),
        (button::L1, \"L1\"),
        (button::SELECT, \"SELECT\"),
    ];
    const RIGHT: [(u16, &str); 6] = [
        (button::TRIANGLE, \"TRIANGLE\"),
        (button::CIRCLE, \"CIRCLE\"),
        (button::CROSS, \"CROSS\"),
        (button::SQUARE, \"SQUARE\"),
        (button::R1, \"R1\"),
        (button::START, \"START\"),
    ];

    let bits = state.buttons.bits();
    let mut row: usize = 0;
    while row < 6 {
""",
        "simplify controller map",
    ),
    (
        "font.draw_text(8, 180, \"LEFT STICK\", (0x60, 0x60, 0x68));\n    font.draw_text(168, 180, \"RIGHT STICK\", (0x60, 0x60, 0x68));",
        "font.draw_text(8, 180, \"DIGITAL PAD / SIMPLE MODE\", (0x60, 0x60, 0x68));\n    font.draw_text(168, 180, \"L1 / R1 MAX\", (0x60, 0x60, 0x68));",
        "mapper labels",
    ),
]

for old, new, label in replacements:
    if old not in s:
        raise SystemExit(f"home patch failed: {label} pattern not found")
    s = s.replace(old, new, 1)

path.write_text(s)
print(f"Applied full-screen HOME artwork, horizontal selection and simple labels to {path}")
