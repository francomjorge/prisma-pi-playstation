// SPDX-License-Identifier: GPL-2.0-or-later
// Standalone PS1 SPU autoplay diagnostic.
// Boots, waits briefly, plays one embedded sample once, then idles forever.

#![no_std]
#![no_main]

extern crate psx_rt;

use psx_asset::Audio;
use psx_spu::{Adsr, Spu, SpuAddr, Voice, Volume};

static WOOF: &[u8] = include_bytes!("woof.psau");
const SPU_SAMPLE_BASE: u32 = 0x1010;

#[no_mangle]
fn main() {
    let Some(peripherals) = psx_rt::Peripherals::take() else {
        return;
    };

    let mut spu = Spu::new(peripherals.spu_dma);
    let audio = Audio::from_bytes(WOOF).expect("woof psau");
    let addr = SpuAddr::new(SPU_SAMPLE_BASE);

    spu.upload_adpcm(addr, audio.adpcm_bytes());

    let voice = Voice::V0;
    voice.configure_sample(
        addr,
        audio.sample_rate_hz(),
        Volume::linear(3, 4),
        Adsr::sample(),
    );

    // Give the frontend/SPU path about half a second to settle, then key on.
    let mut frames = 0u8;
    while frames < 30 {
        psx_rt::interrupts::wait_vblank();
        frames += 1;
    }

    Voice::start(voice.mask());

    // No pad polling, no menu, no retrigger: one automatic one-shot only.
    loop {
        psx_rt::interrupts::wait_vblank();
    }
}
