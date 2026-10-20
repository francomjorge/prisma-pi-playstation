#!/usr/bin/env python3
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
s = path.read_text()

old_import = "use psx_pad::{button, require_analog_on, PadMode, PadReader, PadState, Port};"
new_import = "use psx_pad::{button, poll_on, PadMode, PadState, Port};"

old_setup = """    let mut port = peripherals.controller_port;\n    let _ = require_analog_on(&mut port, Port::One);\n    let mut reader = PadReader::port1();\n    let mut was_connected = true;\n"""
new_setup = """    // Compatibility-first input path: plain controller polling.\n    // Do not force DualShock analog/config mode during menu navigation.\n    let mut port = peripherals.controller_port;\n"""

old_poll = """        let pad_state = reader.poll_on(&mut port);\n        if (pad_state.is_connected() && !was_connected) || pad_state.mode == PadMode::Config {\n            let _ = require_analog_on(&mut port, Port::One);\n        }\n        was_connected = pad_state.is_connected();\n\n"""
new_poll = """        let pad_state = poll_on(&mut port, Port::One);\n\n"""

for old, new, label in [
    (old_import, new_import, "import"),
    (old_setup, new_setup, "setup"),
    (old_poll, new_poll, "poll loop"),
]:
    if old not in s:
        raise SystemExit(f"input compatibility patch failed: {label} pattern not found")
    s = s.replace(old, new, 1)

path.write_text(s)
print(f"Applied controller compatibility patch to {path}")
