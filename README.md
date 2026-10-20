# PRISMA-PI / PlayStation

Experimental PlayStation 1 synthesizer interface built on top of the PSoXide SDK.

## Current milestone

The first milestone is intentionally diagnostic rather than musical:

- HOME screen with an embedded 4bpp image/texture.
- Selectable `PRISMA-PI` and `TEST MODE` entries.
- TEST MODE list with visible selection feedback.
- Full controller-mapping screen for digital buttons and analog sticks.
- Image/VRAM test screen.
- Placeholders for SPU/audio, CD/streaming and memory-card tests.

Controls:

- D-pad UP/DOWN: move selection.
- START or CROSS: enter/confirm.
- CIRCLE: go back from menus.
- START + SELECT: leave the controller mapper (so START and SELECT can both be tested individually).

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

Application code in this repository is developed for PRISMA-PI. Portions adapted from PSoXide examples retain their GPL-2.0-or-later provenance. Visual assets used by PRISMA-PI will be replaced by project-owned/generated artwork as development progresses.
