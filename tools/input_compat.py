#!/usr/bin/env python3
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
s = path.read_text()

replacements = [
    (
        "use psx_pad::{button, require_analog_on, PadMode, PadReader, PadState, Port};",
        "use psx_pad::{button, poll_on, PadMode, PadState, Port};",
        "import",
    ),
    (
        """    let mut port = peripherals.controller_port;\n    let _ = require_analog_on(&mut port, Port::One);\n    let mut reader = PadReader::port1();\n    let mut was_connected = true;\n""",
        """    // Compatibility-first input path: plain controller polling.\n    // Do not force DualShock analog/config mode during menu navigation.\n    let mut port = peripherals.controller_port;\n""",
        "setup",
    ),
    (
        """        let pad_state = reader.poll_on(&mut port);\n        if (pad_state.is_connected() && !was_connected) || pad_state.mode == PadMode::Config {\n            let _ = require_analog_on(&mut port, Port::One);\n        }\n        was_connected = pad_state.is_connected();\n\n""",
        """        let pad_state = poll_on(&mut port, Port::One);\n\n""",
        "poll loop",
    ),
    (
        "Screen::Home => render_home(&font, home_selection),",
        "Screen::Home => render_home(&font, home_selection, pad_state),",
        "home render call",
    ),
    (
        """fn render_home(font: &FontAtlas, selection: u8) {\n    draw_prisma_image(112, 18, 96, 48);\n    font.draw_text(100, 74, \"PRISMA-PI\", (0x70, 0xD0, 0xD0));\n    font.draw_text(72, 88, \"PLAYSTATION SYNTH LAB\", (0x70, 0x70, 0x80));\n    draw_menu_row(font, 0, selection, 92, 126, 136, \"PRISMA-PI\");\n    draw_menu_row(font, 1, selection, 92, 154, 164, \"TEST MODE\");\n    font.draw_text(76, 208, \"UP/DOWN  START OR CROSS\", (0x60, 0x60, 0x68));\n}\n""",
        """fn render_home(font: &FontAtlas, selection: u8, state: PadState) {\n    draw_prisma_image(112, 18, 96, 48);\n    font.draw_text(100, 74, \"PRISMA-PI\", (0x70, 0xD0, 0xD0));\n    font.draw_text(72, 88, \"PLAYSTATION SYNTH LAB\", (0x70, 0x70, 0x80));\n    draw_menu_row(font, 0, selection, 92, 126, 136, \"PRISMA-PI\");\n    draw_menu_row(font, 1, selection, 92, 154, 164, \"TEST MODE\");\n\n    // RetroArch/libretro diagnostic: show exactly what the emulated PS1 sees.\n    font.draw_text(16, 184, \"PAD:\", (0x60, 0x60, 0x68));\n    font.draw_text(56, 184, pad_mode_label(state.mode), pad_mode_tint(state.mode));\n    font.draw_text(160, 184, \"ID:\", (0x60, 0x60, 0x68));\n    let id = hex_u8(state.id_low);\n    font.draw_text(192, 184, &id, (0x70, 0x90, 0x90));\n\n    font.draw_text(16, 198, \"BITS:\", (0x60, 0x60, 0x68));\n    let raw = hex_u16(state.buttons.bits());\n    font.draw_text(64, 198, &raw, (0x70, 0xD0, 0xD0));\n\n    font.draw_text(76, 220, \"UP/DOWN  START OR CROSS\", (0x60, 0x60, 0x68));\n}\n""",
        "home diagnostics",
    ),
]

for old, new, label in replacements:
    if old not in s:
        raise SystemExit(f"input compatibility patch failed: {label} pattern not found")
    s = s.replace(old, new, 1)

path.write_text(s)
print(f"Applied controller compatibility + RetroArch diagnostics to {path}")
