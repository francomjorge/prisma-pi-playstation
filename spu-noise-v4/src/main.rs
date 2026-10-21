// SPDX-License-Identifier: GPL-2.0-or-later
// SPU_NOISE_V4: lowest-level PS1 audio diagnostic.
// No samples, no PSAU, no SPU RAM upload, no controller input.
// Uses only the PlayStation SPU's internal noise generator.

#![no_std]
#![no_main]

extern crate psx_rt;

use psx_gpu::display::{DisplayConfig, DoubleBuffer, Resolution, VideoMode};
use psx_gpu::Gpu;
use psx_spu::{set_main_volume, set_noise_clock, Adsr, Spu, Voice, Volume};

#[no_mangle]
fn main() {
    let Some(peripherals) = psx_rt::Peripherals::take() else {
        return;
    };

    // Video comes first so we can see whether execution reached main().
    let mut gpu = Gpu::new(
        peripherals.gpu_dma,
        DisplayConfig::new(VideoMode::Ntsc, Resolution::R320X240),
    );
    let mut fb = DoubleBuffer::new(Resolution::R320X240);
    gpu.set_draw_area((0, 0), (319, 239));
    gpu.set_draw_offset((0, 0));

    // RED for ~1 second: executable + GPU are alive.
    for _ in 0..60 {
        fb.clear(&mut gpu, (120, 0, 0));
        gpu.wait_idle();
        psx_rt::interrupts::wait_vblank();
        fb.swap(&mut gpu);
    }

    // Initialise SPU. This does not upload any user sample.
    let _spu = Spu::new(peripherals.spu_dma);
    set_main_volume(Volume::MAX, Volume::MAX);

    // YELLOW for ~1 second: SPU init returned.
    for _ in 0..60 {
        fb.clear(&mut gpu, (110, 90, 0));
        gpu.wait_idle();
        psx_rt::interrupts::wait_vblank();
        fb.swap(&mut gpu);
    }

    // Voice 0 is routed to the SPU's INTERNAL NOISE GENERATOR.
    // No sample address, no ADPCM decoding and no SPU RAM are involved.
    let voice = Voice::V0;
    voice.set_volume(Volume::MAX, Volume::MAX);
    voice.set_adsr(Adsr::default_tone());
    Voice::set_noise_mask(voice.mask());

    // Start at a clearly audible mid/high noise clock.
    set_noise_clock(4, 0);
    Voice::start(voice.mask());

    // MAGENTA: first noise clock, ~1 second.
    for _ in 0..60 {
        fb.clear(&mut gpu, (110, 0, 90));
        gpu.wait_idle();
        psx_rt::interrupts::wait_vblank();
        fb.swap(&mut gpu);
    }

    // Change the noise clock while the same voice remains keyed on.
    set_noise_clock(8, 2);

    // CYAN: second/lower noise clock, ~1 second.
    for _ in 0..60 {
        fb.clear(&mut gpu, (0, 100, 110));
        gpu.wait_idle();
        psx_rt::interrupts::wait_vblank();
        fb.swap(&mut gpu);
    }

    // One final clock change to make an audible pitch/timbre transition obvious.
    set_noise_clock(12, 3);

    // WHITE: third/lower noise clock, ~1 second.
    for _ in 0..60 {
        fb.clear(&mut gpu, (120, 120, 120));
        gpu.wait_idle();
        psx_rt::interrupts::wait_vblank();
        fb.swap(&mut gpu);
    }

    Voice::release(voice.mask());
    Voice::set_noise_mask(0);

    // BLUE forever: test finished. Audio should now be silent.
    loop {
        fb.clear(&mut gpu, (0, 20, 110));
        gpu.wait_idle();
        psx_rt::interrupts::wait_vblank();
        fb.swap(&mut gpu);
    }
}
