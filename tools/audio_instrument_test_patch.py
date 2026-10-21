#!/usr/bin/env python3
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
s = path.read_text()

# AUDIO TEST 2: minimal deterministic SPU instrument test.
# Keep this deliberately simple so a silent result points at the emulator/audio
# path rather than at INDIA's multi-stem mixer or complex parameter handling.

old_screen = '''            Screen::AudioTest => {\n                if just_pressed(pressed, button::CIRCLE) {\n                    Voice::release(0x00FF_FFFF);\n                    screen = Screen::TestMenu;\n                } else {\n                    handle_audio_test(&mut audio, pressed, &audio_addrs, &audio_rates);\n                }\n            }\n'''
new_screen = '''            Screen::AudioTest => {\n                // All four face buttons are notes in AUDIO TEST 2.\n                // START+SELECT is the explicit back chord.\n                if held(bits, button::START) && held(bits, button::SELECT) {\n                    Voice::release(0x00FF_FFFF);\n                    screen = Screen::TestMenu;\n                } else {\n                    handle_audio_test(&mut audio, pressed, &audio_addrs, &audio_rates);\n                }\n            }\n'''
if old_screen not in s:
    raise SystemExit('audio instrument patch failed: AudioTest screen arm not found')
s = s.replace(old_screen, new_screen, 1)

start = s.find('fn handle_audio_test(')
end = s.find('\nfn audio_adjust(', start)
if start < 0 or end < 0:
    raise SystemExit('audio instrument patch failed: handle_audio_test span not found')

new_handler = r'''fn handle_audio_test(
    state: &mut AudioTestState,
    pressed: u16,
    addrs: &[SpuAddr; AUDIO_SAMPLE_COUNT],
    rates: &[u32; AUDIO_SAMPLE_COUNT],
) {
    // One shared volume for the four-note instrument. Keep left/right matched so
    // this test cannot accidentally disappear into one muted channel.
    if just_pressed(pressed, button::L1) && state.vol_l > 0 {
        state.vol_l -= 1;
        state.vol_r = state.vol_l;
        apply_instrument_volume(state);
    }
    if just_pressed(pressed, button::R1) && state.vol_l < 8 {
        state.vol_l += 1;
        state.vol_r = state.vol_l;
        apply_instrument_volume(state);
    }

    let mut hit = false;

    if just_pressed(pressed, button::SQUARE) {
        trigger_instrument_note(state, 0, addrs, rates);
        hit = true;
    }
    if just_pressed(pressed, button::CROSS) {
        trigger_instrument_note(state, 1, addrs, rates);
        hit = true;
    }
    if just_pressed(pressed, button::CIRCLE) {
        trigger_instrument_note(state, 2, addrs, rates);
        hit = true;
    }
    if just_pressed(pressed, button::TRIANGLE) {
        trigger_instrument_note(state, 3, addrs, rates);
        hit = true;
    }

    if just_pressed(pressed, button::START) {
        trigger_instrument_chord(state, addrs, rates);
        hit = true;
    }

    if just_pressed(pressed, button::SELECT) {
        Voice::release(0x00FF_FFFF);
    }

    if hit {
        state.flash = 10;
    }
}

fn trigger_instrument_note(
    state: &AudioTestState,
    note: u8,
    addrs: &[SpuAddr; AUDIO_SAMPLE_COUNT],
    rates: &[u32; AUDIO_SAMPLE_COUNT],
) {
    // Same known-good PSoXide BEEP sample on four independent hardware voices.
    // Ratios are intentionally far apart so pitch changes are unmistakable.
    const NOTE_PITCH: [u16; 4] = [0x0800, 0x1000, 0x1800, 0x2000];
    let voice = Voice::new(note);
    configure_audio_voice(voice, state, addrs[0], rates[0], NOTE_PITCH[note as usize]);
    Voice::start(voice.mask());
}

fn trigger_instrument_chord(
    state: &AudioTestState,
    addrs: &[SpuAddr; AUDIO_SAMPLE_COUNT],
    rates: &[u32; AUDIO_SAMPLE_COUNT],
) {
    const NOTE_PITCH: [u16; 4] = [0x0800, 0x1000, 0x1800, 0x2000];
    let mut mask = 0u32;
    let mut i = 0u8;
    while i < 4 {
        let voice = Voice::new(i);
        configure_audio_voice(voice, state, addrs[0], rates[0], NOTE_PITCH[i as usize]);
        mask |= voice.mask();
        i += 1;
    }
    Voice::start(mask);
}

fn apply_instrument_volume(state: &AudioTestState) {
    let volume = Volume::linear(state.vol_l as u16, 8);
    let mut i = 0u8;
    while i < 4 {
        Voice::new(i).set_volume(volume, volume);
        i += 1;
    }
}
'''
s = s[:start] + new_handler + s[end:]

start = s.find('fn render_audio_test(')
end = s.find('\nfn draw_audio_param_row(', start)
if start < 0 or end < 0:
    raise SystemExit('audio instrument patch failed: render_audio_test span not found')

new_render = r'''fn render_audio_test(font: &FontAtlas, state: &AudioTestState) {
    font.draw_text(8, 6, "TEST / AUDIO + SPU / V2", (0x70, 0xD0, 0xD0));
    font.draw_text(8, 20, "MINIMAL 4-VOICE HARDWARE SOUND TEST", (0x58, 0x70, 0x70));

    draw_rect(8, 38, 304, 34, (12, 16, 22));
    font.draw_text(16, 48, "SAMPLE", (0x60, 0x60, 0x68));
    font.draw_text(72, 48, "BEEP / PSAU / SPU RAM", (0x80, 0xD0, 0xC0));
    font.draw_text(16, 61, "VOLUME", (0x60, 0x60, 0x68));
    font.draw_text(80, 61, VOL_LABELS[state.vol_l as usize], (0x80, 0xD0, 0xC0));
    draw_volume_bar(144, 63, state.vol_l);

    draw_rect(8, 84, 304, 82, (10, 14, 20));
    font.draw_text(18, 94,  "SQUARE    VOICE 0    0.50X", (0x70, 0x90, 0x90));
    font.draw_text(18, 111, "CROSS     VOICE 1    1.00X", (0x70, 0xB0, 0x90));
    font.draw_text(18, 128, "CIRCLE    VOICE 2    1.50X", (0x90, 0xB0, 0x70));
    font.draw_text(18, 145, "TRIANGLE  VOICE 3    2.00X", (0xB0, 0x90, 0x70));

    font.draw_text(8, 178, "START = 4-VOICE CHORD", (0x68, 0x80, 0x80));
    font.draw_text(8, 191, "SELECT = STOP ALL", (0x68, 0x80, 0x80));
    font.draw_text(8, 204, "L1/R1 = VOLUME", (0x68, 0x80, 0x80));
    font.draw_text(8, 217, "START+SELECT = BACK", (0x58, 0x68, 0x68));
}
'''
s = s[:start] + new_render + s[end:]

path.write_text(s)
print(f'Applied AUDIO TEST 2 four-note SPU instrument patch to {path}')
