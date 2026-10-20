# PRISMA-PI / PlayStation

Experimental PlayStation 1 synthesizer interface built on top of the PSoXide SDK.

## Current milestone

The project currently boots into a diagnostic shell that is becoming the hardware test bench for the synthesizer:

- HOME screen with an embedded 4bpp image/texture.
- Selectable `PRISMA-PI` and `TEST MODE` entries.
- TEST MODE list with visible selection feedback.
- Full controller-mapping screen for digital buttons and analog sticks.
- Image/VRAM test screen.
- Interactive AUDIO/SPU test bench using real PS1 SPU voices and ADPCM sample RAM.
- Placeholders for CD/streaming and memory-card tests.

### General controls

- D-pad UP/DOWN: move selection.
- START or CROSS: enter/confirm.
- CIRCLE: go back from menus.
- START + SELECT: leave the controller mapper (so START and SELECT can both be tested individually).

### AUDIO / SPU test

The audio test uses eight selectable hardware voices and four temporary cooked PSAU samples. It exposes real SPU parameters rather than simulated UI values.

- `L1 / R1`: select voice V0..V7.
- `L2 / R2`: select sample.
- `LEFT / RIGHT`: select parameter: PITCH, VOL L, VOL R or ADSR.
- `UP / DOWN`: change the selected parameter.
- `CROSS`: configure and key-on the selected voice.
- `SQUARE`: key-off/release the selected voice.
- `START`: trigger a four-voice pitch chord using the selected sample.
- `SELECT`: key-off all voices.
- `CIRCLE`: stop all voices and return to TEST MODE.

Pitch choices currently span 0.50x to 2.00x. Stereo volume is independently adjustable in eighths. ADSR presets are `SAMPLE`, `PERC` and `TONE`, mapping to PSoXide's real SPU envelope presets.

The current audio samples are PSoXide example assets and are intentionally isolated so they can be replaced later by PRISMA-PI's own sound bank without changing the test logic.

## Build

This repository keeps the application code small and pins PSoXide as the SDK/toolchain source.

```sh
make setup
make build
```

Output:

```text
build/primapi.bin
build/primapi.cue
```

To run with a PSoXide-compatible frontend/emulator:

```sh
make run FRONTEND=/absolute/path/to/frontend
```

## SDK pin

PSoXide is pinned by the Makefile to a known revision rather than following `main` implicitly. The app is synchronized into PSoXide's `sdk/examples/primapi` layout before building so it uses the SDK's own linker, post-link checks and disc packer.

## Licensing / provenance

Application code in this repository is developed for PRISMA-PI. Portions adapted from PSoXide examples retain their GPL-2.0-or-later provenance. Visual assets and final audio assets used by PRISMA-PI will be project-owned/generated material as development progresses.
