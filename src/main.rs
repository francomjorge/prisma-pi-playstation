// SPDX-License-Identifier: GPL-2.0-or-later
//
// PRISMA-PI PlayStation diagnostic shell.
// Controller/font/texture/audio setup is adapted from GPL-2.0-or-later
// PSoXide SDK examples (`hello-input`, `hello-tex`, `hello-audio`).

#![no_std]
#![no_main]

extern crate psx_rt;

use psx_asset::Audio;
use psx_font::{fonts::BASIC, FontAtlas};
use psx_gpu::display::{DisplayConfig, DoubleBuffer, Resolution, VideoMode};
use psx_gpu::Gpu;
use psx_hw::gpu::{pack_color, pack_texcoord, pack_vertex, pack_xy};
use psx_io::gpu::{wait_command_ready, write_command};
use psx_pad::{button, require_analog_on, PadMode, PadReader, PadState, Port};
use psx_spu::{Adsr, Pitch, Spu, SpuAddr, Voice, Volume};
use psx_vram::{upload_bytes, Clut, TextureDepth, TexturePage, VramRect};

const FONT_TPAGE: TexturePage = TexturePage::new(320, 0, TextureDepth::Bit4);
const FONT_CLUT: Clut = Clut::new(320, 256);

const LOGO_W: usize = 96;
const LOGO_H: usize = 48;
const LOGO_BYTES: usize = LOGO_W * LOGO_H / 2;
const LOGO_TPAGE: TexturePage = TexturePage::new(640, 0, TextureDepth::Bit4);
const LOGO_CLUT: Clut = Clut::new(0, 480);

static LOGO_PIXELS: [u8; LOGO_BYTES] = make_logo_pixels();
static LOGO_CLUT_BYTES: [u8; 32] = make_logo_palette();

static AUDIO_BEEP: &[u8] = include_bytes!("../../../../assets/audio/freesfx/psau/ui_beep.psau");
static AUDIO_COIN: &[u8] = include_bytes!("../../../../assets/audio/freesfx/psau/pickup_coin.psau");
static AUDIO_SWOO: &[u8] = include_bytes!("../../../../assets/audio/freesfx/psau/swoosh.psau");
static AUDIO_PUNCH: &[u8] = include_bytes!("../../../../assets/audio/freesfx/psau/hit_punch.psau");

const SPU_SAMPLE_BASE: u32 = 0x1010;
const AUDIO_SAMPLE_COUNT: usize = 4;
const AUDIO_PARAM_COUNT: u8 = 4;
const AUDIO_VOICE_COUNT: u8 = 8;

struct AudioSampleDef {
    bytes: &'static [u8],
    label: &'static str,
}

static AUDIO_SAMPLES: [AudioSampleDef; AUDIO_SAMPLE_COUNT] = [
    AudioSampleDef { bytes: AUDIO_BEEP, label: "BEEP" },
    AudioSampleDef { bytes: AUDIO_COIN, label: "COIN" },
    AudioSampleDef { bytes: AUDIO_SWOO, label: "SWOOSH" },
    AudioSampleDef { bytes: AUDIO_PUNCH, label: "PUNCH" },
];

const PITCH_Q12: [u16; 6] = [0x0800, 0x0C00, 0x1000, 0x1400, 0x1800, 0x2000];
const PITCH_LABELS: [&str; 6] = ["0.50X", "0.75X", "1.00X", "1.25X", "1.50X", "2.00X"];
const VOL_LABELS: [&str; 9] = ["0/8", "1/8", "2/8", "3/8", "4/8", "5/8", "6/8", "7/8", "8/8"];
const ADSR_LABELS: [&str; 3] = ["SAMPLE", "PERC", "TONE"];
const VOICE_LABELS: [&str; 8] = ["V0", "V1", "V2", "V3", "V4", "V5", "V6", "V7"];

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

#[derive(Clone, Copy)]
struct AudioTestState {
    voice: u8,
    sample: u8,
    parameter: u8,
    pitch: u8,
    vol_l: u8,
    vol_r: u8,
    adsr: u8,
    flash: u8,
}

impl AudioTestState {
    const INIT: Self = Self {
        voice: 0,
        sample: 0,
        parameter: 0,
        pitch: 2,
        vol_l: 6,
        vol_r: 6,
        adsr: 0,
        flash: 0,
    };
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

    let mut spu_driver = Spu::new(peripherals.spu_dma);
    let (audio_addrs, audio_rates) = upload_audio_bank(&mut spu_driver);

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
    let mut audio = AudioTestState::INIT;

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
                    screen = if home_selection == 0 { Screen::Prisma } else { Screen::TestMenu };
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
            Screen::AudioTest => {
                if just_pressed(pressed, button::CIRCLE) {
                    Voice::release(0x00FF_FFFF);
                    screen = Screen::TestMenu;
                } else {
                    handle_audio_test(&mut audio, pressed, &audio_addrs, &audio_rates);
                }
            }
            Screen::CdTest | Screen::MemoryTest => {
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
            Screen::AudioTest => {
                if audio.flash != 0 { (8, 22, 18) } else { (10, 4, 7) }
            }
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
            Screen::AudioTest => render_audio_test(&font, &audio),
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

        if audio.flash != 0 {
            audio.flash -= 1;
        }
    }
}

fn upload_audio_bank(spu: &mut Spu) -> ([SpuAddr; AUDIO_SAMPLE_COUNT], [u32; AUDIO_SAMPLE_COUNT]) {
    let mut addrs = [SpuAddr::new(SPU_SAMPLE_BASE); AUDIO_SAMPLE_COUNT];
    let mut rates = [44_100u32; AUDIO_SAMPLE_COUNT];
    let mut next_addr = SPU_SAMPLE_BASE;
    let mut i = 0usize;

    while i < AUDIO_SAMPLE_COUNT {
        let decoded = Audio::from_bytes(AUDIO_SAMPLES[i].bytes).expect("PRISMA-PI PSAU");
        let addr = SpuAddr::new(next_addr);
        spu.upload_adpcm(addr, decoded.adpcm_bytes());
        addrs[i] = addr;
        rates[i] = decoded.sample_rate_hz();
        next_addr += decoded.adpcm_bytes().len() as u32;
        next_addr = (next_addr + 7) & !7;
        i += 1;
    }

    (addrs, rates)
}

fn handle_audio_test(
    state: &mut AudioTestState,
    pressed: u16,
    addrs: &[SpuAddr; AUDIO_SAMPLE_COUNT],
    rates: &[u32; AUDIO_SAMPLE_COUNT],
) {
    if just_pressed(pressed, button::L1) {
        state.voice = if state.voice == 0 { AUDIO_VOICE_COUNT - 1 } else { state.voice - 1 };
    }
    if just_pressed(pressed, button::R1) {
        state.voice = (state.voice + 1) % AUDIO_VOICE_COUNT;
    }
    if just_pressed(pressed, button::L2) {
        state.sample = if state.sample == 0 { (AUDIO_SAMPLE_COUNT - 1) as u8 } else { state.sample - 1 };
    }
    if just_pressed(pressed, button::R2) {
        state.sample = (state.sample + 1) % AUDIO_SAMPLE_COUNT as u8;
    }

    if just_pressed(pressed, button::LEFT) {
        state.parameter = if state.parameter == 0 { AUDIO_PARAM_COUNT - 1 } else { state.parameter - 1 };
    }
    if just_pressed(pressed, button::RIGHT) {
        state.parameter = (state.parameter + 1) % AUDIO_PARAM_COUNT;
    }

    let mut changed = false;
    if just_pressed(pressed, button::UP) {
        changed = audio_adjust(state, 1);
    }
    if just_pressed(pressed, button::DOWN) {
        changed = audio_adjust(state, -1) || changed;
    }
    if changed {
        apply_live_audio_params(state, rates[state.sample as usize]);
    }

    if just_pressed(pressed, button::CROSS) {
        trigger_audio_voice(state, addrs, rates);
        state.flash = 10;
    }
    if just_pressed(pressed, button::SQUARE) {
        Voice::release(Voice::new(state.voice).mask());
    }
    if just_pressed(pressed, button::SELECT) {
        Voice::release(0x00FF_FFFF);
    }
    if just_pressed(pressed, button::START) {
        trigger_audio_chord(state, addrs, rates);
        state.flash = 16;
    }
}

fn audio_adjust(state: &mut AudioTestState, delta: i8) -> bool {
    match state.parameter {
        0 => {
            state.pitch = step_u8(state.pitch, delta, (PITCH_Q12.len() - 1) as u8);
            true
        }
        1 => {
            state.vol_l = step_u8(state.vol_l, delta, 8);
            true
        }
        2 => {
            state.vol_r = step_u8(state.vol_r, delta, 8);
            true
        }
        _ => {
            state.adsr = step_u8(state.adsr, delta, 2);
            true
        }
    }
}

fn step_u8(value: u8, delta: i8, max: u8) -> u8 {
    if delta > 0 {
        if value >= max { 0 } else { value + 1 }
    } else if value == 0 {
        max
    } else {
        value - 1
    }
}

fn trigger_audio_voice(
    state: &AudioTestState,
    addrs: &[SpuAddr; AUDIO_SAMPLE_COUNT],
    rates: &[u32; AUDIO_SAMPLE_COUNT],
) {
    let sample = state.sample as usize;
    let voice = Voice::new(state.voice);
    configure_audio_voice(voice, state, addrs[sample], rates[sample], PITCH_Q12[state.pitch as usize]);
    Voice::start(voice.mask());
}

fn trigger_audio_chord(
    state: &AudioTestState,
    addrs: &[SpuAddr; AUDIO_SAMPLE_COUNT],
    rates: &[u32; AUDIO_SAMPLE_COUNT],
) {
    const CHORD_PITCH: [u16; 4] = [0x0800, 0x1000, 0x1800, 0x2000];
    let sample = state.sample as usize;
    let mut mask = 0u32;
    let mut i = 0u8;
    while i < 4 {
        let voice = Voice::new(i);
        configure_audio_voice(voice, state, addrs[sample], rates[sample], CHORD_PITCH[i as usize]);
        mask |= voice.mask();
        i += 1;
    }
    Voice::start(mask);
}

fn configure_audio_voice(
    voice: Voice,
    state: &AudioTestState,
    addr: SpuAddr,
    rate: u32,
    ratio_q12: u16,
) {
    voice.configure_sample(addr, rate, Volume::MAX, audio_adsr(state.adsr));
    voice.set_volume(
        Volume::linear(state.vol_l as u16, 8),
        Volume::linear(state.vol_r as u16, 8),
    );
    voice.set_pitch(scaled_pitch(rate, ratio_q12));
}

fn apply_live_audio_params(state: &AudioTestState, rate: u32) {
    let voice = Voice::new(state.voice);
    voice.set_volume(
        Volume::linear(state.vol_l as u16, 8),
        Volume::linear(state.vol_r as u16, 8),
    );
    voice.set_pitch(scaled_pitch(rate, PITCH_Q12[state.pitch as usize]));
    voice.set_adsr(audio_adsr(state.adsr));
}

fn scaled_pitch(sample_rate: u32, ratio_q12: u16) -> Pitch {
    let base = Pitch::for_sample_rate(sample_rate).as_u16() as u32;
    let mut raw = (base * ratio_q12 as u32) >> 12;
    if raw == 0 {
        raw = 1;
    }
    if raw > 0x3FFF {
        raw = 0x3FFF;
    }
    Pitch::raw(raw as u16)
}

fn audio_adsr(index: u8) -> Adsr {
    match index {
        0 => Adsr::sample_one_shot(),
        1 => Adsr::percussive(),
        _ => Adsr::default_tone(),
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
    let variant = match mode { 0 => "A", 1 => "B", 2 => "C", _ => "D" };
    font.draw_text(10, 174, "BACKGROUND VARIANT:", (0x60, 0x60, 0x68));
    font.draw_text(178, 174, variant, (0x70, 0xD0, 0xD0));
    draw_rect(10, 194, 52, 10, (80, 24, 42));
    draw_rect(66, 194, 52, 10, (24, 80, 54));
    draw_rect(122, 194, 52, 10, (22, 52, 92));
    draw_rect(178, 194, 52, 10, (84, 72, 22));
    draw_rect(234, 194, 52, 10, (70, 28, 86));
    font.draw_text(10, 216, "LEFT/RIGHT VARIANT  CIRCLE BACK", (0x58, 0x68, 0x68));
}

fn render_audio_test(font: &FontAtlas, state: &AudioTestState) {
    font.draw_text(8, 6, "TEST / AUDIO + SPU", (0x70, 0xD0, 0xD0));
    font.draw_text(8, 20, "REAL VOICE REGISTERS + ADPCM", (0x58, 0x70, 0x70));

    draw_rect(8, 38, 304, 32, (12, 16, 22));
    font.draw_text(16, 47, "VOICE", (0x60, 0x60, 0x68));
    font.draw_text(64, 47, VOICE_LABELS[state.voice as usize], (0x80, 0xD0, 0xC0));
    font.draw_text(112, 47, "SAMPLE", (0x60, 0x60, 0x68));
    font.draw_text(168, 47, AUDIO_SAMPLES[state.sample as usize].label, (0x80, 0xD0, 0xC0));

    draw_audio_param_row(font, 0, state.parameter, 82, "PITCH", PITCH_LABELS[state.pitch as usize]);
    draw_audio_param_row(font, 1, state.parameter, 104, "VOL L", VOL_LABELS[state.vol_l as usize]);
    draw_audio_param_row(font, 2, state.parameter, 126, "VOL R", VOL_LABELS[state.vol_r as usize]);
    draw_audio_param_row(font, 3, state.parameter, 148, "ADSR", ADSR_LABELS[state.adsr as usize]);

    draw_volume_bar(200, 108, state.vol_l);
    draw_volume_bar(200, 130, state.vol_r);

    font.draw_text(8, 176, "CROSS PLAY / SQUARE RELEASE", (0x68, 0x80, 0x80));
    font.draw_text(8, 188, "START 4-VOICE CHORD / SELECT STOP", (0x68, 0x80, 0x80));
    font.draw_text(8, 200, "L1/R1 VOICE  L2/R2 SAMPLE", (0x68, 0x80, 0x80));
    font.draw_text(8, 212, "D-PAD EDIT  CIRCLE BACK", (0x58, 0x68, 0x68));
}

fn draw_audio_param_row(font: &FontAtlas, row: u8, selected: u8, y: i16, label: &str, value: &str) {
    if row == selected {
        draw_rect(8, y - 4, 184, 18, (18, 58, 62));
        font.draw_text(14, y, ">", (0x90, 0xF0, 0xD0));
        font.draw_text(30, y, label, (0x90, 0xF0, 0xD0));
        font.draw_text(104, y, value, (0x90, 0xF0, 0xD0));
    } else {
        font.draw_text(30, y, label, (0x60, 0x68, 0x70));
        font.draw_text(104, y, value, (0x70, 0x90, 0x90));
    }
}

fn draw_volume_bar(x: i16, y: i16, level: u8) {
    draw_rect(x, y, 96, 6, (14, 20, 24));
    if level != 0 {
        draw_rect(x, y, level as u16 * 12, 6, (28, 100, 82));
    }
}

fn render_prisma(font: &FontAtlas) {
    draw_prisma_image(112, 24, 96, 48);
    font.draw_text(100, 84, "PRISMA-PI", (0x70, 0xD0, 0xD0));
    font.draw_text(67, 106, "SYNTH ENGINE PLACEHOLDER", (0x68, 0x68, 0x78));
    draw_rect(38, 136, 244, 34, (12, 18, 24));
    font.draw_text(48, 148, "SPU TEST BENCH NOW AVAILABLE", (0x70, 0xA0, 0xA0));
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

fn draw_menu_row(font: &FontAtlas, index: u8, selection: u8, x: i16, box_y: i16, text_y: i16, label: &str) {
    if index == selection {
        draw_rect(x, box_y, 136, 22, (18, 58, 62));
        font.draw_text(x + 8, text_y, ">", (0x90, 0xF0, 0xD0));
        font.draw_text(x + 24, text_y, label, (0x90, 0xF0, 0xD0));
    } else {
        draw_rect(x, box_y, 136, 22, (10, 16, 22));
        font.draw_text(x + 24, text_y, label, (0x68, 0x70, 0x78));
    }
}

fn draw_button_status(font: &FontAtlas, x: i16, y: i16, mask: u16, label: &str, bits: u16, seen: u16) {
    let is_live = held(bits, mask);
    let was_seen = held(seen, mask);
    let color = if is_live { (24, 112, 58) } else if was_seen { (24, 58, 106) } else { (18, 24, 30) };
    draw_rect(x, y, 9, 9, color);
    let tint = if is_live { (0x70, 0xE0, 0x90) } else if was_seen { (0x70, 0x90, 0xD0) } else { (0x58, 0x58, 0x60) };
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
fn held(bits: u16, mask: u16) -> bool { bits & mask != 0 }

#[inline]
fn just_pressed(pressed: u16, mask: u16) -> bool { pressed & mask != 0 }

#[inline]
fn confirm_pressed(pressed: u16) -> bool {
    just_pressed(pressed, button::START) || just_pressed(pressed, button::CROSS)
}

fn upload_prisma_image() {
    let pixel_rect = VramRect::new(LOGO_TPAGE.x(), LOGO_TPAGE.y(), (LOGO_W / 4) as u16, LOGO_H as u16);
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
    if x == 0 || x == LOGO_W - 1 || y == 0 || y == LOGO_H - 1 { return 5; }
    let mut c = 1;
    if x % 12 == 0 || y % 12 == 0 { c = 2; }
    let phase = x % 48;
    let tri = if phase < 24 { phase } else { 47 - phase };
    let wave_y = 8 + tri;
    if abs_diff(y, wave_y) <= 1 { return 14; }
    let phase2 = (x + 9) % 32;
    let tri2 = if phase2 < 16 { phase2 } else { 31 - phase2 };
    let wave2_y = 39 - tri2;
    if abs_diff(y, wave2_y) == 0 { return 10; }
    if x >= 68 && x <= 91 && y >= 6 && y <= 17 {
        let local = (x - 68) % 8;
        if local <= 4 && (y == 7 || y == 15 || local == 0 || local == 4) { return 8; }
    }
    if y >= 40 && y <= 44 && x >= 8 && x <= 88 {
        let step = (x - 8) / 10;
        let pos = (x - 8) % 10;
        if pos <= 6 { return if step % 3 == 0 { 12 } else { 4 }; }
    }
    c
}

const fn abs_diff(a: usize, b: usize) -> usize { if a >= b { a - b } else { b - a } }

const fn rgb15(r: u16, g: u16, b: u16) -> u16 { (r & 31) | ((g & 31) << 5) | ((b & 31) << 10) }

const fn make_logo_palette() -> [u8; 32] {
    let colors: [u16; 16] = [
        rgb15(0, 0, 0), rgb15(2, 3, 5), rgb15(3, 7, 9), rgb15(4, 10, 12),
        rgb15(5, 12, 14), rgb15(7, 18, 18), rgb15(12, 20, 20), rgb15(16, 23, 22),
        rgb15(8, 22, 18), rgb15(10, 26, 20), rgb15(10, 22, 28), rgb15(18, 18, 28),
        rgb15(24, 12, 28), rgb15(26, 18, 8), rgb15(12, 31, 24), rgb15(28, 31, 31),
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
    out[0] = b'0'; out[1] = b'x';
    out[2] = HEX[((v >> 12) & 0xF) as usize];
    out[3] = HEX[((v >> 8) & 0xF) as usize];
    out[4] = HEX[((v >> 4) & 0xF) as usize];
    out[5] = HEX[(v & 0xF) as usize];
    HexU16(out)
}

fn hex_u8(v: u8) -> HexU8 {
    const HEX: &[u8; 16] = b"0123456789ABCDEF";
    let mut out = [0u8; 4];
    out[0] = b'0'; out[1] = b'x';
    out[2] = HEX[((v >> 4) & 0xF) as usize];
    out[3] = HEX[(v & 0xF) as usize];
    HexU8(out)
}

struct HexU8([u8; 4]);
impl HexU8 {
    fn as_str(&self) -> &str { unsafe { core::str::from_utf8_unchecked(&self.0) } }
}
impl core::ops::Deref for HexU8 {
    type Target = str;
    fn deref(&self) -> &str { self.as_str() }
}

struct HexU16([u8; 6]);
impl HexU16 {
    fn as_str(&self) -> &str { unsafe { core::str::from_utf8_unchecked(&self.0) } }
}
impl core::ops::Deref for HexU16 {
    type Target = str;
    fn deref(&self) -> &str { self.as_str() }
}
