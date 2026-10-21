#![no_std]
#![no_main]

extern crate psx_rt;

use psx_font::{fonts::BASIC, FontAtlas};
use psx_gpu::display::{DisplayConfig, DoubleBuffer, Resolution, VideoMode};
use psx_gpu::Gpu;
use psx_vram::{Clut, TextureDepth, TexturePage};

const FONT_TPAGE: TexturePage = TexturePage::new(320, 0, TextureDepth::Bit4);
const FONT_CLUT: Clut = Clut::new(320, 256);

// Direct SPU MMIO registers. This diagnostic intentionally bypasses psx-spu.
const SPU_BASE: u32 = 0x1F80_1C00;
const V0_VOL_L: u32 = SPU_BASE + 0x00;
const V0_VOL_R: u32 = SPU_BASE + 0x02;
const V0_PITCH: u32 = SPU_BASE + 0x04;
const V0_START: u32 = SPU_BASE + 0x06;
const V0_ADSR_LO: u32 = SPU_BASE + 0x08;
const V0_ADSR_HI: u32 = SPU_BASE + 0x0A;
const V0_REPEAT: u32 = SPU_BASE + 0x0E;

const MAIN_VOL_L: u32 = 0x1F80_1D80;
const MAIN_VOL_R: u32 = 0x1F80_1D82;
const REVERB_VOL_L: u32 = 0x1F80_1D84;
const REVERB_VOL_R: u32 = 0x1F80_1D86;
const KEY_ON_LO: u32 = 0x1F80_1D88;
const KEY_ON_HI: u32 = 0x1F80_1D8A;
const KEY_OFF_LO: u32 = 0x1F80_1D8C;
const KEY_OFF_HI: u32 = 0x1F80_1D8E;
const PITCH_MOD_LO: u32 = 0x1F80_1D90;
const PITCH_MOD_HI: u32 = 0x1F80_1D92;
const NOISE_LO: u32 = 0x1F80_1D94;
const NOISE_HI: u32 = 0x1F80_1D96;
const REVERB_EN_LO: u32 = 0x1F80_1D98;
const REVERB_EN_HI: u32 = 0x1F80_1D9A;
const ENDX_LO: u32 = 0x1F80_1D9C;
const ENDX_HI: u32 = 0x1F80_1D9E;
const REVERB_WORK_BASE: u32 = 0x1F80_1DA2;
const TRANSFER_ADDR: u32 = 0x1F80_1DA6;
const TRANSFER_DATA: u32 = 0x1F80_1DA8;
const SPUCNT: u32 = 0x1F80_1DAA;
const TRANSFER_CTRL: u32 = 0x1F80_1DAC;
const SPUSTAT: u32 = 0x1F80_1DAE;
const CD_VOL_L: u32 = 0x1F80_1DB0;
const CD_VOL_R: u32 = 0x1F80_1DB2;

const SPU_ENABLE: u16 = 0x8000;
const SPU_UNMUTE: u16 = 0x4000;
const TRANSFER_MANUAL_WRITE: u16 = 0x0010;
const TRANSFER_MODE_MASK: u16 = 0x0030;
const TRANSFER_CTRL_NORMAL: u16 = 0x0004;
const SPU_SAMPLE_ADDR: u32 = 0x1010;
const SPU_SAMPLE_REG: u16 = (SPU_SAMPLE_ADDR / 8) as u16;

// Four PSX ADPCM blocks (112 samples) forming one crude sine cycle.
// First block marks LOOP START, final block marks END|REPEAT.
// At pitch 0x1000 this loops at ~393.75 Hz: an unmistakable test beep.
static BEEP_ADPCM: [u8; 64] = [
    0x00,0x04,0x00,0x11,0x22,0x32,0x33,0x44,0x54,0x55,0x65,0x66,0x66,0x77,0x77,0x77,
    0x00,0x00,0x77,0x77,0x77,0x67,0x66,0x66,0x55,0x55,0x44,0x34,0x33,0x22,0x12,0x01,
    0x00,0x00,0x00,0xFF,0xEE,0xDE,0xDD,0xCC,0xBC,0xBB,0xAB,0xAA,0xAA,0x99,0x99,0x99,
    0x00,0x03,0x99,0x99,0x99,0xA9,0xAA,0xAA,0xBB,0xBB,0xCC,0xDC,0xDD,0xEE,0xFE,0x0F,
];

#[inline(always)]
fn wr(addr: u32, value: u16) {
    unsafe { core::ptr::write_volatile(addr as *mut u16, value) }
}

#[inline(always)]
fn rd(addr: u32) -> u16 {
    unsafe { core::ptr::read_volatile(addr as *const u16) }
}

fn wait_mode(want: u16) {
    for _ in 0..100_000u32 {
        if (rd(SPUSTAT) & 0x003F) == (want & 0x003F) {
            return;
        }
    }
}

fn wait_transfer_idle() {
    let mut clear = 0u32;
    for _ in 0..100_000u32 {
        if rd(SPUSTAT) & (1 << 10) == 0 {
            clear += 1;
            if clear >= 16 { break; }
        } else {
            clear = 0;
        }
    }
    for _ in 0..256u32 {
        let _ = rd(SPUSTAT);
    }
}

fn init_spu_direct() {
    // Hard silence/reset of every global route that can interfere with V0.
    wr(KEY_OFF_LO, 0xFFFF);
    wr(KEY_OFF_HI, 0x00FF);
    wr(PITCH_MOD_LO, 0);
    wr(PITCH_MOD_HI, 0);
    wr(NOISE_LO, 0);
    wr(NOISE_HI, 0);
    wr(REVERB_EN_LO, 0);
    wr(REVERB_EN_HI, 0);
    wr(REVERB_VOL_L, 0);
    wr(REVERB_VOL_R, 0);
    wr(REVERB_WORK_BASE, 0xFFFE);
    wr(CD_VOL_L, 0);
    wr(CD_VOL_R, 0);

    wr(V0_VOL_L, 0);
    wr(V0_VOL_R, 0);
    wr(V0_PITCH, 0);
    wr(V0_START, 0);
    wr(V0_ADSR_LO, 0);
    wr(V0_ADSR_HI, 0);

    wr(MAIN_VOL_L, 0x3FFF);
    wr(MAIN_VOL_R, 0x3FFF);
    wr(TRANSFER_CTRL, TRANSFER_CTRL_NORMAL);

    // Enable first while muted, then unmute, matching PSX-SPX/PSoXide.
    wr(SPUCNT, SPU_ENABLE);
    wait_mode(0);
    wr(SPUCNT, SPU_ENABLE | SPU_UNMUTE);
    wait_mode(0);
}

fn upload_beep_pio() {
    let base = rd(SPUCNT) & !TRANSFER_MODE_MASK;
    wr(SPUCNT, base);
    wait_mode(base);
    wr(TRANSFER_CTRL, TRANSFER_CTRL_NORMAL);
    wr(TRANSFER_ADDR, SPU_SAMPLE_REG);
    wr(SPUCNT, base | TRANSFER_MANUAL_WRITE);
    wait_mode(base | TRANSFER_MANUAL_WRITE);

    let mut i = 0usize;
    while i < BEEP_ADPCM.len() {
        wr(TRANSFER_DATA, BEEP_ADPCM[i] as u16 | ((BEEP_ADPCM[i + 1] as u16) << 8));
        i += 2;
    }
    wait_transfer_idle();
    wr(SPUCNT, base);
    wait_mode(base);
    wr(TRANSFER_CTRL, TRANSFER_CTRL_NORMAL);
}

fn configure_voice0() {
    wr(V0_VOL_L, 0x3FFF);
    wr(V0_VOL_R, 0x3FFF);
    wr(V0_PITCH, 0x1000);
    wr(V0_START, SPU_SAMPLE_REG);
    wr(V0_REPEAT, SPU_SAMPLE_REG);
    // Instant attack, full sustain, fast exponential release.
    wr(V0_ADSR_LO, 0x000F);
    wr(V0_ADSR_HI, 0x0027);
    wr(ENDX_LO, 0x0001);
    wr(ENDX_HI, 0);
}

fn key_on() {
    wr(KEY_ON_LO, 0x0001);
    wr(KEY_ON_HI, 0);
}

fn key_off() {
    wr(KEY_OFF_LO, 0x0001);
    wr(KEY_OFF_HI, 0);
}

#[no_mangle]
fn main() {
    let Some(peripherals) = psx_rt::Peripherals::take() else { return; };

    let mut gpu = Gpu::new(
        peripherals.gpu_dma,
        DisplayConfig::new(VideoMode::Ntsc, Resolution::R320X240),
    );
    let mut fb = DoubleBuffer::new(Resolution::R320X240);
    gpu.set_draw_area((0, 0), (319, 239));
    gpu.set_draw_offset((0, 0));
    let font = FontAtlas::upload(&BASIC, FONT_TPAGE, FONT_CLUT);

    // Keep the DMA token alive but do not use psx-spu at all.
    let _spu_dma_token = peripherals.spu_dma;

    init_spu_direct();
    upload_beep_pio();
    configure_voice0();
    key_on();

    let mut frame: u32 = 0;
    loop {
        // 0.5 s ON, 1.5 s OFF, repeating automatically. No controller required.
        let phase = frame % 120;
        if phase == 0 { key_on(); }
        if phase == 30 { key_off(); }

        fb.clear(&mut gpu, if phase < 30 { (18, 28, 12) } else { (8, 8, 12) });
        font.draw_text(10, 20, "DIRECT SPU BEEP TEST", (230, 230, 230));
        font.draw_text(10, 40, "NO psx-spu / NO controller", (160, 160, 160));
        font.draw_text(10, 64, "AUTO: 0.5s ON / 1.5s OFF", (160, 160, 160));
        if phase < 30 {
            font.draw_text(10, 96, "BEEP ON", (220, 220, 120));
        } else {
            font.draw_text(10, 96, "BEEP OFF", (110, 110, 110));
        }
        font.draw_text(10, 130, "V0  SPU RAM 0x1010  PIO", (130, 180, 180));
        font.draw_text(10, 148, "~394 Hz  direct MMIO", (130, 180, 180));

        gpu.wait_idle();
        psx_rt::interrupts::wait_vblank();
        fb.swap(&mut gpu);
        frame = frame.wrapping_add(1);
    }
}
