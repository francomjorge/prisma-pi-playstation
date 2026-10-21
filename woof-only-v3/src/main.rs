// SPDX-License-Identifier: GPL-2.0-or-later
// WOOF_ONLY_V3: isolated PS1 audio diagnostic with visible boot stages.
// No pad input, no menus, no sprites, no game logic.
//
// RED    = GPU/boot OK, before touching SPU
// YELLOW = SPU init OK, before sample upload
// GREEN  = sample parsed/uploaded/configured
// BLUE   = Voice::start issued; the woof should be audible

#![no_std]
#![no_main]

extern crate psx_rt;

use psx_asset::Audio;
use psx_gpu::display::{DisplayConfig, DoubleBuffer, Resolution, VideoMode};
use psx_gpu::Gpu;
use psx_spu::{Adsr, Spu, SpuAddr, Voice, Volume};

static WOOF: &[u8] = include_bytes!("woof.psau");
const SPU_SAMPLE_BASE: u32 = 0x1010;

fn show_frames(
    gpu: &mut Gpu,
    fb: &mut DoubleBuffer,
    color: (u8, u8, u8),
    frames: u32,
) {
    let mut n = 0u32;
    while n < frames {
        fb.clear(gpu, color);
        gpu.wait_idle();
        psx_rt::interrupts::wait_vblank();
        fb.swap(gpu);
        n += 1;
    }
}

#[no_mangle]
fn main() {
    let Some(peripherals) = psx_rt::Peripherals::take() else {
        return;
    };

    // Stage 1: prove that this exact disc booted and video works BEFORE SPU.
    let mut gpu = Gpu::new(
        peripherals.gpu_dma,
        DisplayConfig::new(VideoMode::Ntsc, Resolution::R320X240),
    );
    let mut fb = DoubleBuffer::new(Resolution::R320X240);
    gpu.set_draw_area((0, 0), (319, 239));
    gpu.set_draw_offset((0, 0));
    show_frames(&mut gpu, &mut fb, (120, 0, 0), 90); // RED ~1.5 s

    // Stage 2: initialise SPU. If this stalls, screen remains red.
    let mut spu = Spu::new(peripherals.spu_dma);
    show_frames(&mut gpu, &mut fb, (120, 96, 0), 60); // YELLOW ~1 s

    // Stage 3: parse and upload exactly one embedded PSAU sample.
    let audio = Audio::from_bytes(WOOF).expect("WOOF_ONLY_V3 psau");
    let addr = SpuAddr::new(SPU_SAMPLE_BASE);
    spu.upload_adpcm(addr, audio.adpcm_bytes());

    let voice = Voice::V0;
    voice.configure_sample(
        addr,
        audio.sample_rate_hz(),
        Volume::MAX,
        Adsr::sample_one_shot(),
    );
    show_frames(&mut gpu, &mut fb, (0, 112, 24), 60); // GREEN ~1 s

    // Stage 4: one automatic trigger, no controller interaction.
    Voice::start(voice.mask());

    // Stay BLUE forever after key-on. If it reaches blue but remains silent,
    // boot/GPU/SPU init/sample upload all completed and only playback remains.
    loop {
        fb.clear(&mut gpu, (0, 32, 128));
        gpu.wait_idle();
        psx_rt::interrupts::wait_vblank();
        fb.swap(&mut gpu);
    }
}
