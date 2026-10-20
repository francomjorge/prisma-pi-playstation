// SPDX-License-Identifier: GPL-2.0-or-later
//
// PRISMA-PI PlayStation diagnostic shell.
// Controller/font/texture setup is adapted from the GPL-2.0-or-later
// PSoXide SDK examples `hello-input` and `hello-tex`.

#![no_std]
#![no_main]

extern crate psx_rt;

use psx_font::{fonts::BASIC, FontAtlas};
use psx_gpu::display::{DisplayConfig, DoubleBuffer, Resolution, VideoMode};
use psx_gpu::Gpu;
use psx_hw::gpu::{pack_color, pack_texcoord, pack_vertex, pack_xy};
use psx_io::gpu::{wait_command_ready, write_command};
use psx_pad::{button, require_analog_on, PadMode, PadReader, PadState, Port};
use psx_vram::{upload_bytes, Clut, TextureDepth, TexturePage, VramRect};

const SCREEN_W: i16 = 320;
const SCREEN_H: i16 = 240;

// Font VRAM layout follows PSoXide's hello-input example.
const FONT_TPAGE: TexturePage = TexturePage::new(320, 0, TextureDepth::Bit4);
const FONT_CLUT: Clut = Clut::new(320, 256);

// PRISMA-PI boot/test image: a 96x48 4bpp texture generated below.
// It deliberately lives outside both 320x240 framebuffer halves.
const LOGO_W: usize = 96;
const LOGO_H: usize = 48;
const LOGO_BYTES: usize = LOGO_W * LOGO_H / 2;
const LOGO_TPAGE: TexturePage = TexturePage::new(640, 0, TextureDepth::Bit4);
const LOGO_CLUT: Clut = Clut::new(0, 480);

static LOGO_PIXELS: [u8; LOGO_BYTES] = make_logo_pixels();
static LOGO_CLUT_BYTES: [u8; 32] = make_logo_palette();

#[derive(Clone, Copy, PartialEq, Eq)]
enum Screen {
    Home,
    TestMenu,
    ControllerMap,
    ImageTest,
    AudioTest,
    CdTest,
    MemoryTest,
    Prisma,
}

#[no_mangle]
fn main() {
    let Some(peripherals) = psx_rt::Peripherals::take() else {
        return;
    };

    let mut gpu = Gpu::new(
        peripherals.gpu_dma,
        DisplayConfig::new(VideoMode::Ntsc, Resolution::R320X240),
    );
    let mut fb = DoubleBuffer::new(Resolution::R320X240);
    gpu.set_draw_area((0, 0), (319, 239));
    gpu.set_draw_offset((0, 0));

    let font = FontAtlas::upload(&BASIC, FONT_TPAGE, FONT_CLUT);
    upload_prisma_image();

    let mut port = peripherals.controller_port;
    let _ = require_analog_on(&mut port, Port::One);
    let mut reader = PadReader::port1();
    let mut was_connected = true;

    let mut screen = Screen::Home;
    let mut home_selection: u8 = 0;
    let mut test_selection: u8 = 0;
    let mut image_mode: u8 = 0;
    let mut seen_buttons: u16 = 0;
    let mut previous_bits: u16 = 0;

    loop {
        let pad_state = reader.poll_on(&mut port);
        if (pad_state.is_connected() && !was_connected) || pad_state.mode == PadMode::Config {
            let _ = require_analog_on(&mut port, Port::One);
        }
        was_connected = pad_state.is_connected();

        let bits = pad_state.buttons.bits();
        let pressed = bits & !previous_bits;

        match screen {
            Screen::Home => {
                if just_pressed(pressed, button::UP) || just_pressed(pressed, button::DOWN) {
                    home_selection ^= 1;
                }
                if confirm_pressed(pressed) {
                    screen = if home_selection == 0 {
                        Screen::Prisma
                    } else {
                        Screen::TestMenu
                    };
                }
            }
            Screen::TestMenu => {
                if just_pressed(pressed, button::UP) {
                    test_selection = if test_selection == 0 { 5 } else { test_selection - 1 };
                }
                if just_pressed(pressed, button::DOWN) {
                    test_selection = if test_selection >= 5 { 0 } else { test_selection + 1 };
                }
                if just_pressed(pressed, button::CIRCLE) {
                    screen = Screen::Home;
                } else if confirm_pressed(pressed) {
                    screen = match test_selection {
                        0 => {
                            seen_buttons = 0;
                            Screen::ControllerMap
                        }
                        1 => Screen::ImageTest,
                        2 => Screen::AudioTest,
                        3 => Screen::CdTest,
                        4 => Screen::MemoryTest,
                        _ => Screen::Home,
                    };
                }
            }
            Screen::ControllerMap => {
                seen_buttons |= bits;

                // A chord is used for navigation so START and SELECT remain
                // individually testable inputs.
                if held(bits, button::START) && held(bits, button::SELECT) {
                    screen = Screen::TestMenu;
                } else if held(bits, button::L3) && held(bits, button::R3) {
                    seen_buttons = 0;
                }
            }
            Screen::ImageTest => {
                if just_pressed(pressed, button::LEFT) {
                    image_mode = image_mode.wrapping_sub(1) & 3;
                }
                if just_pressed(pressed, button::RIGHT) {
                    image_mode = image_mode.wrapping_add(1) & 3;
                }
                if just_pressed(pressed, button::CIRCLE) {
                    screen = Screen::TestMenu;
                }
            }
            Screen::AudioTest | Screen::CdTest | Screen::MemoryTest => {
                if just_pressed(pressed, button::CIRCLE) {
                    screen = Screen::TestMenu;
                }
            }
            Screen::Prisma => {
                if just_pressed(pressed, button::CIRCLE) {
                    screen = Screen::Home;
                }
            }
        }

        let bg = match screen {
            Screen::Home => (5, 7, 12),
            Screen::TestMenu => (6, 10, 13),
            Screen::ControllerMap => (3, 8, 8),
            Screen::ImageTest => match image_mode {
                0 => (4, 5, 10),
                1 => (9, 3, 10),
                2 => (3, 9, 9),
                _ => (10, 6, 2),
            },
            Screen::AudioTest => (10, 4, 7),
            Screen::CdTest => (4, 6, 12),
            Screen::MemoryTest => (8, 6, 2),
            Screen::Prisma => (4, 4, 8),
        };
        fb.clear(&mut gpu, bg);

        match screen {
            Screen::Home => render_home(&font, home_selection),
            Screen::TestMenu => render_test_menu(&font, test_selection),
            Screen::ControllerMap => render_controller_map(&font, pad_state, seen_buttons),
            Screen::ImageTest => render_image_test(&font, image_mode),
            Screen::AudioTest => render_placeholder(
                &font,
                "AUDIO / SPU",
                "NEXT: VOICES / PITCH / ADSR / SAMPLE",
                "CIRCLE = BACK",
            ),
            Screen::CdTest => render_placeholder(
                &font,
                "CD / STREAM",
                "NEXT: DATA / XA / LOOP / SEEK",
                "CIRCLE = BACK",
            ),
            Screen::MemoryTest => render_placeholder(
                &font,
                "MEMORY CARD",
                "NEXT: DETECT / READ / WRITE / SAVE",
                "CIRCLE = BACK",
            ),
            Screen::Prisma => render_prisma(&font),
        }

        gpu.wait_idle();
        psx_rt::interrupts::wait_vblank();
        fb.swap(&mut gpu);
        previous_bits = bits;
    }
}

fn render_home(font: &FontAtlas, selection: u8) {
    draw_prisma_image(112, 18, 96, 48);

    font.draw_text(100, 74, "PRISMA-PI", (0x70, 0xD0, 0xD0));
    font.draw_text(72, 88, "PLAYSTATION SYNTH LAB", (0x70, 0x70, 0x80));

    draw_menu_row(font, 0, selection, 92, 126, 136, "PRISMA-PI");
    draw_menu_row(font, 1, selection, 92, 154, 164, "TEST MODE");

    font.draw_text(76, 208, "UP/DOWN  START OR CROSS", (0x60, 0x60, 0x68));
}

fn render_test_menu(font: &FontAtlas, selection: u8) {
    font.draw_text(12, 10, "PRISMA-PI / TEST MODE", (0x70, 0xD0, 0xD0));
    font.draw_text(12, 26, "SELECT A HARDWARE TEST", (0x60, 0x70, 0x70));

    const ITEMS: [&str; 6] = [
        "CONTROLLER MAP",
        "IMAGE / VRAM",
        "AUDIO / SPU",
        "CD / STREAM",
        "MEMORY CARD",
        "BACK",
    ];

    let mut i: u8 = 0;
    while i < 6 {
        let y = 54 + i as i16 * 26;
        draw_menu_row(font, i, selection, 38, y, y + 10, ITEMS[i as usize]);
        i += 1;
    }

    font.draw_text(12, 220, "CIRCLE = HOME", (0x58, 0x58, 0x60));
}

fn render_controller_map(font: &FontAtlas, state: PadState, seen: u16) {
    font.draw_text(8, 6, "TEST / CONTROLLER MAP", (0x70, 0xD0, 0xD0));
    font.draw_text(8, 20, "LIVE=GREEN  SEEN=BLUE", (0x58, 0x70, 0x70));

    const LEFT: [(u16, &str); 8] = [
        (button::UP, "UP"),
        (button::RIGHT, "RIGHT"),
        (button::DOWN, "DOWN"),
        (button::LEFT, "LEFT"),
        (button::L1, "L1"),
        (button::L2, "L2"),
        (button::L3, "L3"),
        (button::SELECT, "SELECT"),
    ];
    const RIGHT: [(u16, &str); 8] = [
        (button::TRIANGLE, "TRIANGLE"),
        (button::CIRCLE, "CIRCLE"),
        (button::CROSS, "CROSS"),
        (button::SQUARE, "SQUARE"),
        (button::R1, "R1"),
        (button::R2, "R2"),
        (button::R3, "R3"),
        (button::START, "START"),
    ];

    let bits = state.buttons.bits();
    let mut row: usize = 0;
    while row < 8 {
        let y = 38 + row as i16 * 15;
        draw_button_status(font, 8, y, LEFT[row].0, LEFT[row].1, bits, seen);
        draw_button_status(font, 164, y, RIGHT[row].0, RIGHT[row].1, bits, seen);
        row += 1;
    }

    font.draw_text(8, 163, "MODE:", (0x60, 0x60, 0x68));
    font.draw_text(56, 163, pad_mode_label(state.mode), pad_mode_tint(state.mode));
    font.draw_text(174, 163, "BITS:", (0x60, 0x60, 0x68));
    let raw = hex_u16(bits);
    font.draw_text(222, 163, &raw, (0x70, 0x90, 0x90));

    font.draw_text(8, 180, "LEFT STICK", (0x60, 0x60, 0x68));
    font.draw_text(168, 180, "RIGHT STICK", (0x60, 0x60, 0x68));

    if state.is_analog() {
        draw_stick_values(font, 8, 195, state.sticks.left_x, state.sticks.left_y);
        draw_stick_values(font, 168, 195, state.sticks.right_x, state.sticks.right_y);
    } else {
        font.draw_text(8, 195, "DIGITAL / N-A", (0xB0, 0x70, 0x40));
        font.draw_text(168, 195, "DIGITAL / N-A", (0xB0, 0x70, 0x40));
    }

    font.draw_text(8, 218, "START+SELECT BACK | L3+R3 RESET", (0x60, 0x70, 0x70));
}

fn render_image_test(font: &FontAtlas, mode: u8) {
    font.draw_text(10, 8, "TEST / IMAGE + VRAM", (0x70, 0xD0, 0xD0));
    font.draw_text(10, 22, "EMBEDDED 4BPP + CLUT TEXTURE", (0x60, 0x70, 0x70));

    draw_rect(28, 48, 264, 112, (10, 12, 18));
    draw_rect(32, 52, 256, 104, (18, 20, 28));
    draw_prisma_image(112, 78, 96, 48);

    let variant = match mode {
        0 => "A",
        1 => "B",
        2 => "C",
        _ => "D",
    };
    font.draw_text(10, 174, "BACKGROUND VARIANT:", (0x60, 0x60, 0x68));
    font.draw_text(178, 174, variant, (0x70, 0xD0, 0xD0));

    draw_rect(10, 194, 52, 10, (80, 24, 42));
    draw_rect(66, 194, 52, 10, (24, 80, 54));
    draw_rect(122, 194, 52, 10, (22, 52, 92));
    draw_rect(178, 194, 52, 10, (84, 72, 22));
    draw_rect(234, 194, 52, 10, (70, 28, 86));

    font.draw_text(10, 216, "LEFT/RIGHT VARIANT  CIRCLE BACK", (0x58, 0x68, 0x68));
}

fn render_prisma(font: &FontAtlas) {
    draw_prisma_image(112, 24, 96, 48);
    font.draw_text(100, 84, "PRISMA-PI", (0x70, 0xD0, 0xD0));
    font.draw_text(67, 106, "SYNTH ENGINE PLACEHOLDER", (0x68, 0x68, 0x78));

    draw_rect(38, 136, 244, 34, (12, 18, 24));
    font.draw_text(54, 148, "NEXT MILESTONE: SPU + VOICES", (0x70, 0xA0, 0xA0));

    font.draw_text(102, 214, "CIRCLE = HOME", (0x58, 0x58, 0x60));
}

fn render_placeholder(font: &FontAtlas, title: &str, detail: &str, footer: &str) {
    font.draw_text(10, 10, "TEST MODE", (0x60, 0x70, 0x70));
    font.draw_text(10, 34, title, (0x70, 0xD0, 0xD0));
    draw_rect(10, 62, 300, 80, (10, 14, 20));
    font.draw_text(20, 82, "TEST SLOT RESERVED", (0x78, 0x78, 0x88));
    font.draw_text(20, 106, detail, (0x60, 0x78, 0x78));
    font.draw_text(10, 214, footer, (0x58, 0x58, 0x60));
}

fn draw_menu_row(
    font: &FontAtlas,
    index: u8,
    selection: u8,
    x: i16,
    box_y: i16,
    text_y: i16,
    label: &str,
) {
    let selected = index == selection;
    if selected {
        draw_rect(x, box_y, 136, 22, (18, 58, 62));
        font.draw_text(x + 8, text_y, ">", (0x90, 0xF0, 0xD0));
        font.draw_text(x + 24, text_y, label, (0x90, 0xF0, 0xD0));
    } else {
        draw_rect(x, box_y, 136, 22, (10, 16, 22));
        font.draw_text(x + 24, text_y, label, (0x68, 0x70, 0x78));
    }
}

fn draw_button_status(
    font: &FontAtlas,
    x: i16,
    y: i16,
    mask: u16,
    label: &str,
    bits: u16,
    seen: u16,
) {
    let is_live = held(bits, mask);
    let was_seen = held(seen, mask);

    let color = if is_live {
        (24, 112, 58)
    } else if was_seen {
        (24, 58, 106)
    } else {
        (18, 24, 30)
    };

    draw_rect(x, y, 9, 9, color);
    let tint = if is_live {
        (0x70, 0xE0, 0x90)
    } else if was_seen {
        (0x70, 0x90, 0xD0)
    } else {
        (0x58, 0x58, 0x60)
    };
    font.draw_text(x + 15, y, label, tint);
}

fn draw_stick_values(font: &FontAtlas, x: i16, y: i16, vx: u8, vy: u8) {
    font.draw_text(x, y, "X", (0x58, 0x58, 0x60));
    let hx = hex_u8(vx);
    font.draw_text(x + 16, y, &hx, (0x70, 0xA0, 0xB0));
    font.draw_text(x + 64, y, "Y", (0x58, 0x58, 0x60));
    let hy = hex_u8(vy);
    font.draw_text(x + 80, y, &hy, (0x70, 0xA0, 0xB0));
}

fn pad_mode_label(mode: PadMode) -> &'static str {
    match mode {
        PadMode::Disconnected => "NO PAD",
        PadMode::Digital => "DIGITAL",
        PadMode::Negcon => "NEGCON",
        PadMode::Analog => "ANALOG",
        PadMode::Config => "CONFIG",
        PadMode::Unknown => "UNKNOWN",
    }
}

fn pad_mode_tint(mode: PadMode) -> (u8, u8, u8) {
    match mode {
        PadMode::Disconnected => (0xD0, 0x50, 0x50),
        PadMode::Analog => (0x60, 0xD0, 0x80),
        PadMode::Digital => (0xD0, 0x90, 0x40),
        _ => (0x90, 0xA0, 0xD0),
    }
}

#[inline]
fn held(bits: u16, mask: u16) -> bool {
    bits & mask != 0
}

#[inline]
fn just_pressed(pressed: u16, mask: u16) -> bool {
    pressed & mask != 0
}

#[inline]
fn confirm_pressed(pressed: u16) -> bool {
    just_pressed(pressed, button::START) || just_pressed(pressed, button::CROSS)
}

fn upload_prisma_image() {
    let pixel_rect = VramRect::new(
        LOGO_TPAGE.x(),
        LOGO_TPAGE.y(),
        (LOGO_W / 4) as u16,
        LOGO_H as u16,
    );
    upload_bytes(pixel_rect, &LOGO_PIXELS);

    let clut_rect = VramRect::new(LOGO_CLUT.x(), LOGO_CLUT.y(), 16, 1);
    upload_bytes(clut_rect, &LOGO_CLUT_BYTES);
}

fn draw_prisma_image(x: i16, y: i16, w: u16, h: u16) {
    LOGO_TPAGE.apply_as_draw_mode();
    wait_command_ready();
    write_command(psx_hw::gpu::packet::TEXTURED_RECT | pack_color(0x80, 0x80, 0x80));
    write_command(pack_vertex(x, y));
    write_command(pack_texcoord(0, 0, LOGO_CLUT.uv_word()));
    write_command(pack_xy(w, h));
}

fn draw_rect(x: i16, y: i16, w: u16, h: u16, color: (u8, u8, u8)) {
    wait_command_ready();
    write_command(psx_hw::gpu::packet::FLAT_RECT | pack_color(color.0, color.1, color.2));
    write_command(pack_vertex(x, y));
    write_command(pack_xy(w, h));
}

const fn make_logo_pixels() -> [u8; LOGO_BYTES] {
    let mut out = [0u8; LOGO_BYTES];
    let mut y: usize = 0;
    while y < LOGO_H {
        let mut x: usize = 0;
        while x < LOGO_W {
            let p0 = logo_pixel(x, y) & 0x0f;
            let p1 = logo_pixel(x + 1, y) & 0x0f;
            let byte_index = (y * LOGO_W + x) / 2;
            out[byte_index] = p0 | (p1 << 4);
            x += 2;
        }
        y += 1;
    }
    out
}

const fn logo_pixel(x: usize, y: usize) -> u8 {
    if x == 0 || x == LOGO_W - 1 || y == 0 || y == LOGO_H - 1 {
        return 5;
    }

    // Dark panel background.
    let mut c = 1;

    // Fine synth/oscilloscope grid.
    if x % 12 == 0 || y % 12 == 0 {
        c = 2;
    }

    // Main triangular waveform.
    let phase = x % 48;
    let tri = if phase < 24 { phase } else { 47 - phase };
    let wave_y = 8 + tri;
    if abs_diff(y, wave_y) <= 1 {
        return 14;
    }

    // Secondary waveform, lower and tighter.
    let phase2 = (x + 9) % 32;
    let tri2 = if phase2 < 16 { phase2 } else { 31 - phase2 };
    let wave2_y = 39 - tri2;
    if abs_diff(y, wave2_y) == 0 {
        return 10;
    }

    // Small virtual knobs on the right.
    if x >= 68 && x <= 91 && y >= 6 && y <= 17 {
        let local = (x - 68) % 8;
        if local <= 4 && (y == 7 || y == 15 || local == 0 || local == 4) {
            return 8;
        }
    }

    // Sequencer steps along the bottom.
    if y >= 40 && y <= 44 && x >= 8 && x <= 88 {
        let step = (x - 8) / 10;
        let pos = (x - 8) % 10;
        if pos <= 6 {
            return if step % 3 == 0 { 12 } else { 4 };
        }
    }

    c
}

const fn abs_diff(a: usize, b: usize) -> usize {
    if a >= b { a - b } else { b - a }
}

const fn rgb15(r: u16, g: u16, b: u16) -> u16 {
    (r & 31) | ((g & 31) << 5) | ((b & 31) << 10)
}

const fn make_logo_palette() -> [u8; 32] {
    let colors: [u16; 16] = [
        rgb15(0, 0, 0),
        rgb15(2, 3, 5),
        rgb15(3, 7, 9),
        rgb15(4, 10, 12),
        rgb15(5, 12, 14),
        rgb15(7, 18, 18),
        rgb15(12, 20, 20),
        rgb15(16, 23, 22),
        rgb15(8, 22, 18),
        rgb15(10, 26, 20),
        rgb15(10, 22, 28),
        rgb15(18, 18, 28),
        rgb15(24, 12, 28),
        rgb15(26, 18, 8),
        rgb15(12, 31, 24),
        rgb15(28, 31, 31),
    ];

    let mut out = [0u8; 32];
    let mut i: usize = 0;
    while i < 16 {
        let v = colors[i];
        out[i * 2] = (v & 0xff) as u8;
        out[i * 2 + 1] = (v >> 8) as u8;
        i += 1;
    }
    out
}

fn hex_u16(v: u16) -> HexU16 {
    const HEX: &[u8; 16] = b"0123456789ABCDEF";
    let mut out = [0u8; 6];
    out[0] = b'0';
    out[1] = b'x';
    out[2] = HEX[((v >> 12) & 0xF) as usize];
    out[3] = HEX[((v >> 8) & 0xF) as usize];
    out[4] = HEX[((v >> 4) & 0xF) as usize];
    out[5] = HEX[(v & 0xF) as usize];
    HexU16(out)
}

fn hex_u8(v: u8) -> HexU8 {
    const HEX: &[u8; 16] = b"0123456789ABCDEF";
    let mut out = [0u8; 4];
    out[0] = b'0';
    out[1] = b'x';
    out[2] = HEX[((v >> 4) & 0xF) as usize];
    out[3] = HEX[(v & 0xF) as usize];
    HexU8(out)
}

struct HexU8([u8; 4]);
impl HexU8 {
    fn as_str(&self) -> &str {
        // SAFETY: buffer contains ASCII literals and hexadecimal digits only.
        unsafe { core::str::from_utf8_unchecked(&self.0) }
    }
}
impl core::ops::Deref for HexU8 {
    type Target = str;
    fn deref(&self) -> &str {
        self.as_str()
    }
}

struct HexU16([u8; 6]);
impl HexU16 {
    fn as_str(&self) -> &str {
        // SAFETY: buffer contains ASCII literals and hexadecimal digits only.
        unsafe { core::str::from_utf8_unchecked(&self.0) }
    }
}
impl core::ops::Deref for HexU16 {
    type Target = str;
    fn deref(&self) -> &str {
        self.as_str()
    }
}
