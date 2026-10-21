#![no_std]
#![no_main]

extern crate psx_rt;

use psx_font::{fonts::BASIC, FontAtlas};
use psx_gpu::display::{DisplayConfig, DoubleBuffer, Resolution, VideoMode};
use psx_gpu::Gpu;
use psx_vram::{Clut, TextureDepth, TexturePage};

const FONT_TPAGE: TexturePage = TexturePage::new(320, 0, TextureDepth::Bit4);
const FONT_CLUT: Clut = Clut::new(320, 256);

// Raw PS1 SPU MMIO registers. This diagnostic intentionally does not use
// psx_spu::Spu, upload_adpcm, Voice or Pitch.
const SPU_BASE: u32 = 0x1F80_1C00;
const MAIN_VOL_LEFT: u32 = 0x1F80_1D80;
const MAIN_VOL_RIGHT: u32 = 0x1F80_1D82;
const REVERB_VOL_LEFT: u32 = 0x1F80_1D84;
const REVERB_VOL_RIGHT: u32 = 0x1F80_1D86;
const KEY_ON_LO: u32 = 0x1F80_1D88;
const KEY_ON_HI: u32 = 0x1F80_1D8A;
const KEY_OFF_LO: u32 = 0x1F80_1D8C;
const KEY_OFF_HI: u32 = 0x1F80_1D8E;
const PITCH_MOD_LO: u32 = 0x1F80_1D90;
const PITCH_MOD_HI: u32 = 0x1F80_1D92;
const NOISE_LO: u32 = 0x1F80_1D94;
const NOISE_HI: u32 = 0x1F80_1D96;
const REVERB_ENABLE_LO: u32 = 0x1F80_1D98;
const REVERB_ENABLE_HI: u32 = 0x1F80_1D9A;
const REVERB_WORK_BASE: u32 = 0x1F80_1DA2;
const TRANSFER_ADDR: u32 = 0x1F80_1DA6;
const TRANSFER_DATA: u32 = 0x1F80_1DA8;
const SPUCNT: u32 = 0x1F80_1DAA;
const TRANSFER_CTRL: u32 = 0x1F80_1DAC;
const SPUSTAT: u32 = 0x1F80_1DAE;
const CD_VOL_LEFT: u32 = 0x1F80_1DB0;
const CD_VOL_RIGHT: u32 = 0x1F80_1DB2;

const SPU_ENABLE: u16 = 1 << 15;
const SPU_UNMUTE: u16 = 1 << 14;
const SPU_TRANSFER_MANUAL_WRITE: u16 = 1 << 4;
const SPU_RAM_ADDR: u32 = 0x1010;
const SPU_RAM_REG: u16 = (SPU_RAM_ADDR / 8) as u16;

// Two looping PSX ADPCM blocks. Filter 0, shift 2, approximately one
// sine-like cycle per 28 decoded samples. At pitch 0x0800 this produces
// an obvious ~788 Hz diagnostic tone.
const TONE_ADPCM: [u8; 32] = [
    0x02, 0x04,
    0x20, 0x64, 0x77, 0x46, 0x02, 0xCE, 0x9A,
    0xA9, 0xEC, 0x20, 0x64, 0x67, 0x24, 0xE0,
    0x02, 0x03,
    0x20, 0x64, 0x77, 0x46, 0x02, 0xCE, 0x9A,
    0xA9, 0xEC, 0x20, 0x64, 0x67, 0x24, 0xE0,
];

#[inline(always)]
fn write16(addr: u32, value: u16) {
    unsafe { core::ptr::write_volatile(addr as *mut u16, value) }
}

#[inline(always)]
fn read16(addr: u32) -> u16 {
    unsafe { core::ptr::read_volatile(addr as *const u16) }
}

fn wait_mode(want: u16) {
    for _ in 0..100_000u32 {
        if (read16(SPUSTAT) & 0x003F) == (want & 0x003F) {
            return;
        }
    }
}

fn raw_spu_init() {
    write16(KEY_OFF_LO, 0xFFFF);
    write16(KEY_OFF_HI, 0x00FF);

    for v in 0..24u32 {
        let base = SPU_BASE + v * 0x10;
        write16(base + 0x0, 0);
        write16(base + 0x2, 0);
        write16(base + 0x4, 0);
        write16(base + 0x6, 0);
        write16(base + 0x8, 0);
        write16(base + 0xA, 0);
    }

    write16(PITCH_MOD_LO, 0);
    write16(PITCH_MOD_HI, 0);
    write16(NOISE_LO, 0);
    write16(NOISE_HI, 0);
    write16(REVERB_ENABLE_LO, 0);
    write16(REVERB_ENABLE_HI, 0);
    write16(REVERB_VOL_LEFT, 0);
    write16(REVERB_VOL_RIGHT, 0);
    write16(REVERB_WORK_BASE, 0xFFFE);
    write16(CD_VOL_LEFT, 0);
    write16(CD_VOL_RIGHT, 0);
    write16(MAIN_VOL_LEFT, 0x3FFF);
    write16(MAIN_VOL_RIGHT, 0x3FFF);

    // Enable muted first, then unmute after SPUSTAT catches up.
    write16(SPUCNT, SPU_ENABLE);
    wait_mode(0);
    write16(SPUCNT, SPU_ENABLE | SPU_UNMUTE);
    wait_mode(0);
    write16(TRANSFER_CTRL, 0x0004);
}

fn raw_upload_tone() {
    let normal = SPU_ENABLE | SPU_UNMUTE;
    write16(TRANSFER_CTRL, 0x0004);
    write16(TRANSFER_ADDR, SPU_RAM_REG);
    write16(SPUCNT, normal | SPU_TRANSFER_MANUAL_WRITE);
    wait_mode(SPU_TRANSFER_MANUAL_WRITE);

    let mut i = 0usize;
    while i < TONE_ADPCM.len() {
        let hw = (TONE_ADPCM[i] as u16) | ((TONE_ADPCM[i + 1] as u16) << 8);
        write16(TRANSFER_DATA, hw);
        i += 2;
    }

    // The test payload is only 16 halfwords, below the SPU FIFO depth.
    // Still wait for the transfer-busy flag to remain clear before leaving
    // manual-write mode.
    let mut clear = 0u32;
    for _ in 0..100_000u32 {
        if read16(SPUSTAT) & (1 << 10) == 0 {
            clear += 1;
            if clear >= 32 {
                break;
            }
        } else {
            clear = 0;
        }
    }
    for _ in 0..2048u32 {
        let _ = read16(SPUSTAT);
    }

    write16(SPUCNT, normal);
    wait_mode(0);
}

fn raw_start_tone() {
    let v0 = SPU_BASE;
    write16(KEY_OFF_LO, 0x0001);

    write16(v0 + 0x0, 0x3FFF); // left volume
    write16(v0 + 0x2, 0x3FFF); // right volume
    write16(v0 + 0x4, 0x0800); // half-rate pitch
    write16(v0 + 0x6, SPU_RAM_REG); // sample start
    write16(v0 + 0x8, 0x000F); // ADSR lower: same sample preset as PSoXide
    write16(v0 + 0xA, 0x001F); // ADSR upper
    write16(v0 + 0xE, SPU_RAM_REG); // repeat address

    write16(KEY_ON_HI, 0);
    write16(KEY_ON_LO, 0x0001);
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

    raw_spu_init();
    raw_upload_tone();
    raw_start_tone();

    loop {
        fb.clear(&mut gpu, (2, 20, 8));
        font.draw_text(20, 80, "RAW SPU BEEP", (240, 240, 240));
        font.draw_text(20, 104, "NO PSAU / NO PSX_SPU DRIVER", (180, 220, 180));
        font.draw_text(20, 128, "CONTINUOUS ~788 HZ TONE", (255, 220, 90));
        font.draw_text(20, 164, "IF SILENT: EMULATOR SPU PATH", (180, 180, 180));

        gpu.wait_idle();
        psx_rt::interrupts::wait_vblank();
        fb.swap(&mut gpu);
    }
}
