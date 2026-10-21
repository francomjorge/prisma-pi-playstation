// SPDX-License-Identifier: GPL-2.0-or-later
// WOOF_ONLY_V2: isolated PS1 audio sanity test.
// No pad input, no menu, no sprites, no game logic.
// Boots to a flat screen, waits a few frames, plays one embedded sample once.

#![no_std]
#![no_main]

extern crate psx_rt;

use psx_asset::Audio;
use psx_gpu::display::{DisplayConfig, DoubleBuffer, Resolution, VideoMode};
use psx_gpu::Gpu;
use psx_spu::{Adsr, Spu, SpuAddr, Voice, Volume};

static WOOF: &[u8] = include_bytes!("woof.psau");
const SPU_SAMPLE_BASE: u32 = 0x1010;

#[no_mangle]
fn main() {
    let Some(peripherals) = psx_rt::Peripherals::take() else {
        return;
    };

    // Minimal video only so this disc is unmistakable:
    // a flat blue screen, no images/assets/UI.
    let mut gpu = Gpu::new(
        peripherals.gpu_dma,
        DisplayConfig::new(VideoMode::Ntsc, Resolution::R320X240),
    );
    let mut fb = DoubleBuffer::new(Resolution::R320X240);
    gpu.set_draw_area((0, 0), (319, 239));
    gpu.set_draw_offset((0, 0));

    // Isolated SPU path.
    let mut spu = Spu::new(peripherals.spu_dma);
    let audio = Audio::from_bytes(WOOF).expect("WOOF_ONLY_V2 psau");
    let addr = SpuAddr::new(SPU_SAMPLE_BASE);
    spu.upload_adpcm(addr, audio.adpcm_bytes());

    let voice = Voice::V0;
    voice.configure_sample(
        addr,
        audio.sample_rate_hz(),
        Volume::linear(3, 4),
        Adsr::sample_one_shot(),
    );

    let mut frame: u32 = 0;
    let mut played = false;

    loop {
        // Solid diagnostic screen only. If anything else appears,
        // the emulator is not running this disc image.
        fb.clear(&mut gpu, (8, 24, 72));
        gpu.wait_idle();
        psx_rt::interrupts::wait_vblank();
        fb.swap(&mut gpu);

        // Automatic one-shot. No buttons, no controller polling.
        if !played && frame >= 12 {
            Voice::start(voice.mask());
            played = true;
        }
        frame = frame.wrapping_add(1);
    }
}
