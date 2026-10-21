#!/usr/bin/env python3
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
s = path.read_text()

# Six 5-second, 30 kHz mono PSX-SPU-ADPCM stems. They intentionally reuse the
# same SPU-RAM region as TEST MODE's short SFX bank: all six together occupy
# 514,272 bytes from 0x1010, leaving ~5.9 KiB below the 512 KiB SPU-RAM limit.
audio_anchor = '''static AUDIO_SAMPLES: [AudioSampleDef; AUDIO_SAMPLE_COUNT] = [\n    AudioSampleDef { bytes: AUDIO_BEEP, label: "BEEP" },\n    AudioSampleDef { bytes: AUDIO_COIN, label: "COIN" },\n    AudioSampleDef { bytes: AUDIO_SWOO, label: "SWOOSH" },\n    AudioSampleDef { bytes: AUDIO_PUNCH, label: "PUNCH" },\n];\n'''
audio_insert = audio_anchor + '''\nconst INDIA_AUDIO_COUNT: usize = 6;\nconst INDIA_AUDIO_RATE: u32 = 30_000;\nconst INDIA_VOICE_MASK: u32 = 0x0000_003F;\n\nstatic INDIA_AUDIO_DRUM1: &[u8] = include_bytes!("india_drum1.psau");\nstatic INDIA_AUDIO_DRUM2: &[u8] = include_bytes!("india_drum2.psau");\nstatic INDIA_AUDIO_BASS: &[u8] = include_bytes!("india_bass.psau");\nstatic INDIA_AUDIO_KEYS: &[u8] = include_bytes!("india_keys.psau");\nstatic INDIA_AUDIO_SITAR: &[u8] = include_bytes!("india_sitar.psau");\nstatic INDIA_AUDIO_LEAD: &[u8] = include_bytes!("india_lead.psau");\n\n// Keep this order identical to the 2x3 INDIA UI.\nstatic INDIA_AUDIO_SAMPLES: [&[u8]; INDIA_AUDIO_COUNT] = [\n    INDIA_AUDIO_DRUM1,\n    INDIA_AUDIO_DRUM2,\n    INDIA_AUDIO_BASS,\n    INDIA_AUDIO_KEYS,\n    INDIA_AUDIO_SITAR,\n    INDIA_AUDIO_LEAD,\n];\n'''
if audio_anchor not in s:
    raise SystemExit('india audio patch failed: AUDIO_SAMPLES anchor not found')
s = s.replace(audio_anchor, audio_insert, 1)

old = '''    let (audio_addrs, audio_rates) = upload_audio_bank(&mut spu_driver);\n'''
new = '''    let (mut audio_addrs, mut audio_rates) = upload_audio_bank(&mut spu_driver);\n    let mut prisma_audio_addrs = [SpuAddr::new(SPU_SAMPLE_BASE); INDIA_AUDIO_COUNT];\n    let mut prisma_playing = false;\n'''
if old not in s:
    raise SystemExit('india audio patch failed: audio bank state anchor not found')
s = s.replace(old, new, 1)

# INDIA entry: overwrite the small TEST bank with the six full-resolution stems.
old = '''                        upload_india_image();\n                        upload_india_ui();\n                        screen = Screen::Prisma;\n'''
new = '''                        upload_india_image();\n                        upload_india_ui();\n                        stop_prisma_audio();\n                        prisma_audio_addrs = upload_prisma_audio_bank(&mut spu_driver);\n                        prisma_playing = false;\n                        screen = Screen::Prisma;\n'''
if old not in s:
    raise SystemExit('india audio patch failed: INDIA entry anchor not found')
s = s.replace(old, new, 1)

# Audio TEST MODE needs its own short sample bank restored because INDIA reuses
# the same SPU RAM region.
old = '''                        2 => Screen::AudioTest,\n'''
new = '''                        2 => {\n                            stop_prisma_audio();\n                            let bank = upload_audio_bank(&mut spu_driver);\n                            audio_addrs = bank.0;\n                            audio_rates = bank.1;\n                            Screen::AudioTest\n                        }\n'''
if old not in s:
    raise SystemExit('india audio patch failed: Test Audio arm not found')
s = s.replace(old, new, 1)

# Values become live stem volumes. START is transport PLAY/STOP.
old = '''                let value_index = prisma_selection as usize;\n                if just_pressed(pressed, button::CROSS) && prisma_values[value_index] < 10 {\n                    prisma_values[value_index] += 1;\n                }\n                if just_pressed(pressed, button::SQUARE) && prisma_values[value_index] > 0 {\n                    prisma_values[value_index] -= 1;\n                }\n\n                if just_pressed(pressed, button::CIRCLE) {\n                    upload_home_image();\n                    screen = Screen::Home;\n                }\n'''
new = '''                let value_index = prisma_selection as usize;\n                if just_pressed(pressed, button::CROSS) && prisma_values[value_index] < 10 {\n                    prisma_values[value_index] += 1;\n                    set_prisma_volume(prisma_selection, prisma_values[value_index]);\n                }\n                if just_pressed(pressed, button::SQUARE) && prisma_values[value_index] > 0 {\n                    prisma_values[value_index] -= 1;\n                    set_prisma_volume(prisma_selection, prisma_values[value_index]);\n                }\n\n                // Six stems are keyed-on with one KON mask, so PLAY starts them\n                // sample-synchronously. Their ADPCM blocks loop in hardware.\n                if just_pressed(pressed, button::START) {\n                    if prisma_playing {\n                        stop_prisma_audio();\n                        prisma_playing = false;\n                    } else {\n                        start_prisma_audio(&prisma_audio_addrs, &prisma_values);\n                        prisma_playing = true;\n                    }\n                }\n\n                if just_pressed(pressed, button::CIRCLE) {\n                    stop_prisma_audio();\n                    prisma_playing = false;\n                    upload_home_image();\n                    screen = Screen::Home;\n                }\n'''
if old not in s:
    raise SystemExit('india audio patch failed: Prisma live control anchor not found')
s = s.replace(old, new, 1)

# Insert the six-stem SPU bank and transport helpers immediately before the
# existing TEST MODE audio-bank loader.
anchor = '''fn upload_audio_bank(spu: &mut Spu) -> ([SpuAddr; AUDIO_SAMPLE_COUNT], [u32; AUDIO_SAMPLE_COUNT]) {\n'''
insert = '''fn upload_prisma_audio_bank(spu: &mut Spu) -> [SpuAddr; INDIA_AUDIO_COUNT] {\n    let mut addrs = [SpuAddr::new(SPU_SAMPLE_BASE); INDIA_AUDIO_COUNT];\n    let mut next_addr = SPU_SAMPLE_BASE;\n    let mut i = 0usize;\n\n    while i < INDIA_AUDIO_COUNT {\n        let decoded = Audio::from_bytes(INDIA_AUDIO_SAMPLES[i]).expect("PRISMA INDIA PSAU");\n        let addr = SpuAddr::new(next_addr);\n        spu.upload_adpcm(addr, decoded.adpcm_bytes());\n        addrs[i] = addr;\n        next_addr += decoded.adpcm_bytes().len() as u32;\n        next_addr = (next_addr + 7) & !7;\n        i += 1;\n    }\n\n    addrs\n}\n\nfn set_prisma_volume(index: u8, value: u8) {\n    if index >= INDIA_AUDIO_COUNT as u8 {\n        return;\n    }\n    let voice = Voice::new(index);\n    let level = if value > 10 { 10 } else { value };\n    let volume = Volume::linear(level as u16, 10);\n    voice.set_volume(volume, volume);\n}\n\nfn start_prisma_audio(addrs: &[SpuAddr; INDIA_AUDIO_COUNT], values: &[u8; INDIA_AUDIO_COUNT]) {\n    // Configure all six voices first, then key them on in a single write.\n    // This is the important part for stem phase/sync.\n    let mut mask = 0u32;\n    let mut i = 0usize;\n    while i < INDIA_AUDIO_COUNT {\n        let voice = Voice::new(i as u8);\n        voice.configure_sample(\n            addrs[i],\n            INDIA_AUDIO_RATE,\n            Volume::MAX,\n            Adsr::sample_one_shot(),\n        );\n        let level = if values[i] > 10 { 10 } else { values[i] };\n        let volume = Volume::linear(level as u16, 10);\n        voice.set_volume(volume, volume);\n        voice.set_pitch(Pitch::for_sample_rate(INDIA_AUDIO_RATE));\n        mask |= voice.mask();\n        i += 1;\n    }\n    Voice::start(mask);\n}\n\nfn stop_prisma_audio() {\n    // Mute first for an immediate transport stop, then key-off the six voices.\n    let mut i = 0u8;\n    while i < INDIA_AUDIO_COUNT as u8 {\n        Voice::new(i).set_volume(Volume::SILENCE, Volume::SILENCE);\n        i += 1;\n    }\n    Voice::release(INDIA_VOICE_MASK);\n}\n\nfn upload_audio_bank(spu: &mut Spu) -> ([SpuAddr; AUDIO_SAMPLE_COUNT], [u32; AUDIO_SAMPLE_COUNT]) {\n'''
if anchor not in s:
    raise SystemExit('india audio patch failed: upload_audio_bank anchor not found')
s = s.replace(anchor, insert, 1)

path.write_text(s)
print(f'Applied INDIA 6-stem PLAY/STOP + live mixer to {path}')
