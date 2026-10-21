#!/usr/bin/env python3
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
s = path.read_text()

# First validation build: one real 5-second, 30 kHz mono PSX-SPU-ADPCM stem.
# DRUM2 maps to the second INDIA module (UI index 1) but uses SPU voice 0.
audio_anchor = '''static AUDIO_SAMPLES: [AudioSampleDef; AUDIO_SAMPLE_COUNT] = [\n    AudioSampleDef { bytes: AUDIO_BEEP, label: "BEEP" },\n    AudioSampleDef { bytes: AUDIO_COIN, label: "COIN" },\n    AudioSampleDef { bytes: AUDIO_SWOO, label: "SWOOSH" },\n    AudioSampleDef { bytes: AUDIO_PUNCH, label: "PUNCH" },\n];\n'''
audio_insert = audio_anchor + '''\nconst INDIA_AUDIO_RATE: u32 = 30_000;\nconst INDIA_VOICE_MASK: u32 = 0x0000_0001;\nstatic INDIA_AUDIO_DRUM2: &[u8] = include_bytes!("india_drum2.psau");\n'''
if audio_anchor not in s:
    raise SystemExit('india audio patch failed: AUDIO_SAMPLES anchor not found')
s = s.replace(audio_anchor, audio_insert, 1)

old = '''    let (audio_addrs, audio_rates) = upload_audio_bank(&mut spu_driver);\n'''
new = '''    let (mut audio_addrs, mut audio_rates) = upload_audio_bank(&mut spu_driver);\n    let mut prisma_audio_addr = SpuAddr::new(SPU_SAMPLE_BASE);\n    let mut prisma_playing = false;\n'''
if old not in s:
    raise SystemExit('india audio patch failed: audio bank state anchor not found')
s = s.replace(old, new, 1)

old = '''                        upload_india_image();\n                        upload_india_ui();\n                        screen = Screen::Prisma;\n'''
new = '''                        upload_india_image();\n                        upload_india_ui();\n                        stop_prisma_audio();\n                        prisma_audio_addr = upload_prisma_audio(&mut spu_driver);\n                        prisma_playing = false;\n                        screen = Screen::Prisma;\n'''
if old not in s:
    raise SystemExit('india audio patch failed: INDIA entry anchor not found')
s = s.replace(old, new, 1)

old = '''                        2 => Screen::AudioTest,\n'''
new = '''                        2 => {\n                            stop_prisma_audio();\n                            let bank = upload_audio_bank(&mut spu_driver);\n                            audio_addrs = bank.0;\n                            audio_rates = bank.1;\n                            Screen::AudioTest\n                        }\n'''
if old not in s:
    raise SystemExit('india audio patch failed: Test Audio arm not found')
s = s.replace(old, new, 1)

old = '''                let value_index = prisma_selection as usize;\n                if just_pressed(pressed, button::CROSS) && prisma_values[value_index] < 10 {\n                    prisma_values[value_index] += 1;\n                }\n                if just_pressed(pressed, button::SQUARE) && prisma_values[value_index] > 0 {\n                    prisma_values[value_index] -= 1;\n                }\n\n                if just_pressed(pressed, button::CIRCLE) {\n                    upload_home_image();\n                    screen = Screen::Home;\n                }\n'''
new = '''                let value_index = prisma_selection as usize;\n                if just_pressed(pressed, button::CROSS) && prisma_values[value_index] < 10 {\n                    prisma_values[value_index] += 1;\n                    if prisma_selection == 1 {\n                        set_prisma_volume(prisma_values[1]);\n                    }\n                }\n                if just_pressed(pressed, button::SQUARE) && prisma_values[value_index] > 0 {\n                    prisma_values[value_index] -= 1;\n                    if prisma_selection == 1 {\n                        set_prisma_volume(prisma_values[1]);\n                    }\n                }\n\n                // First validation: START toggles the single DRUM2 stem.\n                if just_pressed(pressed, button::START) {\n                    if prisma_playing {\n                        stop_prisma_audio();\n                        prisma_playing = false;\n                    } else {\n                        start_prisma_audio(prisma_audio_addr, prisma_values[1]);\n                        prisma_playing = true;\n                    }\n                }\n\n                if just_pressed(pressed, button::CIRCLE) {\n                    stop_prisma_audio();\n                    prisma_playing = false;\n                    upload_home_image();\n                    screen = Screen::Home;\n                }\n'''
if old not in s:
    raise SystemExit('india audio patch failed: Prisma live control anchor not found')
s = s.replace(old, new, 1)

anchor = '''fn upload_audio_bank(spu: &mut Spu) -> ([SpuAddr; AUDIO_SAMPLE_COUNT], [u32; AUDIO_SAMPLE_COUNT]) {\n'''
insert = '''fn upload_prisma_audio(spu: &mut Spu) -> SpuAddr {\n    let decoded = Audio::from_bytes(INDIA_AUDIO_DRUM2).expect("PRISMA INDIA DRUM2 PSAU");\n    let addr = SpuAddr::new(SPU_SAMPLE_BASE);\n    spu.upload_adpcm(addr, decoded.adpcm_bytes());\n    addr\n}\n\nfn set_prisma_volume(value: u8) {\n    let level = if value > 10 { 10 } else { value };\n    let volume = Volume::linear(level as u16, 10);\n    Voice::new(0).set_volume(volume, volume);\n}\n\nfn start_prisma_audio(addr: SpuAddr, value: u8) {\n    let voice = Voice::new(0);\n    voice.configure_sample(\n        addr,\n        INDIA_AUDIO_RATE,\n        Volume::MAX,\n        Adsr::sample_one_shot(),\n    );\n    let level = if value > 10 { 10 } else { value };\n    let volume = Volume::linear(level as u16, 10);\n    voice.set_volume(volume, volume);\n    voice.set_pitch(Pitch::for_sample_rate(INDIA_AUDIO_RATE));\n    Voice::start(voice.mask());\n}\n\nfn stop_prisma_audio() {\n    Voice::new(0).set_volume(Volume::SILENCE, Volume::SILENCE);\n    Voice::release(INDIA_VOICE_MASK);\n}\n\nfn upload_audio_bank(spu: &mut Spu) -> ([SpuAddr; AUDIO_SAMPLE_COUNT], [u32; AUDIO_SAMPLE_COUNT]) {\n'''
if anchor not in s:
    raise SystemExit('india audio patch failed: upload_audio_bank anchor not found')
s = s.replace(anchor, insert, 1)

path.write_text(s)
print(f'Applied INDIA one-stem DRUM2 PLAY/STOP test to {path}')
