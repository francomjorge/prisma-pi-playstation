#!/usr/bin/env python3
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
s = path.read_text()

# Diagnostic build: one real 5-second DRUM2 PSAU stem.
# Mirrors PSoXide hello-audio exactly: upload, configure once with the
# sample's own cooked rate + Adsr::sample(), then key-on. It auto-plays
# on entering INDIA so controller START is not part of the first test.
audio_anchor = '''static AUDIO_SAMPLES: [AudioSampleDef; AUDIO_SAMPLE_COUNT] = [\n    AudioSampleDef { bytes: AUDIO_BEEP, label: "BEEP" },\n    AudioSampleDef { bytes: AUDIO_COIN, label: "COIN" },\n    AudioSampleDef { bytes: AUDIO_SWOO, label: "SWOOSH" },\n    AudioSampleDef { bytes: AUDIO_PUNCH, label: "PUNCH" },\n];\n'''
audio_insert = audio_anchor + '''\nconst INDIA_VOICE_MASK: u32 = 0x0000_0001;\nstatic INDIA_AUDIO_DRUM2: &[u8] = include_bytes!("india_drum2.psau");\n'''
if audio_anchor not in s:
    raise SystemExit('india audio patch failed: AUDIO_SAMPLES anchor not found')
s = s.replace(audio_anchor, audio_insert, 1)

old = '''    let (audio_addrs, audio_rates) = upload_audio_bank(&mut spu_driver);\n'''
new = '''    let (mut audio_addrs, mut audio_rates) = upload_audio_bank(&mut spu_driver);\n    let mut prisma_audio_addr = SpuAddr::new(SPU_SAMPLE_BASE);\n    let mut prisma_audio_rate = 44_100u32;\n    let mut prisma_playing = false;\n'''
if old not in s:
    raise SystemExit('india audio patch failed: audio bank state anchor not found')
s = s.replace(old, new, 1)

old = '''                        upload_india_image();\n                        upload_india_ui();\n                        screen = Screen::Prisma;\n'''
new = '''                        upload_india_image();\n                        upload_india_ui();\n                        Voice::release(INDIA_VOICE_MASK);\n                        let prisma_sample = upload_prisma_audio(&mut spu_driver);\n                        prisma_audio_addr = prisma_sample.0;\n                        prisma_audio_rate = prisma_sample.1;\n                        prisma_values[1] = 10;\n                        configure_prisma_voice(prisma_audio_addr, prisma_audio_rate, Volume::MAX);\n                        Voice::start(Voice::new(0).mask());\n                        prisma_playing = true;\n                        screen = Screen::Prisma;\n'''
if old not in s:
    raise SystemExit('india audio patch failed: INDIA entry anchor not found')
s = s.replace(old, new, 1)

old = '''                        2 => Screen::AudioTest,\n'''
new = '''                        2 => {\n                            Voice::release(INDIA_VOICE_MASK);\n                            let bank = upload_audio_bank(&mut spu_driver);\n                            audio_addrs = bank.0;\n                            audio_rates = bank.1;\n                            Screen::AudioTest\n                        }\n'''
if old not in s:
    raise SystemExit('india audio patch failed: Test Audio arm not found')
s = s.replace(old, new, 1)

old = '''                let value_index = prisma_selection as usize;\n                if just_pressed(pressed, button::CROSS) && prisma_values[value_index] < 10 {\n                    prisma_values[value_index] += 1;\n                }\n                if just_pressed(pressed, button::SQUARE) && prisma_values[value_index] > 0 {\n                    prisma_values[value_index] -= 1;\n                }\n\n                if just_pressed(pressed, button::CIRCLE) {\n                    upload_home_image();\n                    screen = Screen::Home;\n                }\n'''
new = '''                let value_index = prisma_selection as usize;\n                if just_pressed(pressed, button::CROSS) && prisma_values[value_index] < 10 {\n                    prisma_values[value_index] += 1;\n                    if prisma_selection == 1 {\n                        set_prisma_volume(prisma_values[1]);\n                    }\n                }\n                if just_pressed(pressed, button::SQUARE) && prisma_values[value_index] > 0 {\n                    prisma_values[value_index] -= 1;\n                    if prisma_selection == 1 {\n                        set_prisma_volume(prisma_values[1]);\n                    }\n                }\n\n                // START remains transport, but audio has already auto-started\n                // when the INDIA screen was entered.\n                if just_pressed(pressed, button::START) {\n                    if prisma_playing {\n                        Voice::release(INDIA_VOICE_MASK);\n                        prisma_playing = false;\n                    } else {\n                        configure_prisma_voice(\n                            prisma_audio_addr,\n                            prisma_audio_rate,\n                            prisma_volume(prisma_values[1]),\n                        );\n                        Voice::start(Voice::new(0).mask());\n                        prisma_playing = true;\n                    }\n                }\n\n                if just_pressed(pressed, button::CIRCLE) {\n                    Voice::release(INDIA_VOICE_MASK);\n                    prisma_playing = false;\n                    upload_home_image();\n                    screen = Screen::Home;\n                }\n'''
if old not in s:
    raise SystemExit('india audio patch failed: Prisma live control anchor not found')
s = s.replace(old, new, 1)

anchor = '''fn upload_audio_bank(spu: &mut Spu) -> ([SpuAddr; AUDIO_SAMPLE_COUNT], [u32; AUDIO_SAMPLE_COUNT]) {\n'''
insert = '''fn upload_prisma_audio(spu: &mut Spu) -> (SpuAddr, u32) {\n    let decoded = Audio::from_bytes(INDIA_AUDIO_DRUM2).expect("PRISMA INDIA DRUM2 PSAU");\n    let addr = SpuAddr::new(SPU_SAMPLE_BASE);\n    spu.upload_adpcm(addr, decoded.adpcm_bytes());\n    (addr, decoded.sample_rate_hz())\n}\n\nfn prisma_volume(value: u8) -> Volume {\n    let level = if value > 10 { 10 } else { value };\n    Volume::linear(level as u16, 10)\n}\n\nfn set_prisma_volume(value: u8) {\n    let volume = prisma_volume(value);\n    Voice::new(0).set_volume(volume, volume);\n}\n\nfn configure_prisma_voice(addr: SpuAddr, rate: u32, volume: Volume) {\n    Voice::new(0).configure_sample(addr, rate, volume, Adsr::sample());\n}\n\nfn upload_audio_bank(spu: &mut Spu) -> ([SpuAddr; AUDIO_SAMPLE_COUNT], [u32; AUDIO_SAMPLE_COUNT]) {\n'''
if anchor not in s:
    raise SystemExit('india audio patch failed: upload_audio_bank anchor not found')
s = s.replace(anchor, insert, 1)

path.write_text(s)
print(f'Applied INDIA DRUM2 auto-play SPU diagnostic to {path}')
