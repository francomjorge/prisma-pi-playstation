#!/usr/bin/env python3
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
s = path.read_text()

old = '''    let mut prev_pad = ButtonState::NONE;\n    let mut flashes = [0u8; SFX_COUNT];\n\n    loop {\n        let pad = poll_on(&mut port, Port::One).buttons;\n'''
new = '''    let mut prev_pad = ButtonState::NONE;\n    let mut flashes = [0u8; SFX_COUNT];\n    let mut autoplay_frames: u16 = 0;\n\n    loop {\n        // Diagnostic autoplay: trigger the official JUMP sample at full\n        // volume every ~1.5 seconds, completely independent of controller input.\n        autoplay_frames = autoplay_frames.wrapping_add(1);\n        if autoplay_frames >= 90 {\n            autoplay_frames = 0;\n            let voice = SFX_CHANNELS[0].voice;\n            voice.set_volume(Volume::MAX, Volume::MAX);\n            Voice::start(voice.mask());\n            flashes[0] = FLASH_FRAMES;\n        }\n\n        let pad = poll_on(&mut port, Port::One).buttons;\n'''

if old not in s:
    raise SystemExit('hello-audio autoplay patch anchor not found')

s = s.replace(old, new, 1)
path.write_text(s)
print(f'Applied hello-audio autoplay diagnostic patch to {path}')
