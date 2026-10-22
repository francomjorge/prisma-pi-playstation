# PRISMA-PI PS1 build pipeline
PSOXIDE_REPO ?= https://github.com/EBonura/PSoXide.git
PSOXIDE_REV  ?= 3cf22179d8798e8ce5899743fdcf222fc9486a8a
PSOXIDE_DIR  ?= .psoxide
EXAMPLE      := primapi
EXAMPLE_DIR  := $(PSOXIDE_DIR)/sdk/examples/$(EXAMPLE)
OUT_DIR      := build
PSX_OUT_DIR  := $(PSOXIDE_DIR)/build/examples/mipsel-sony-psx/release
INDIA_AUDIO_ARCHIVE := assets/audio/india/india_audio_5s_30k.tar.xz
FRONTEND     ?=

.PHONY: setup sync build run clean status

setup:
	@if [ ! -d "$(PSOXIDE_DIR)/.git" ]; then \
		git clone "$(PSOXIDE_REPO)" "$(PSOXIDE_DIR)"; \
	fi
	@cd "$(PSOXIDE_DIR)" && git checkout --detach "$(PSOXIDE_REV)"

sync: setup
	@mkdir -p "$(EXAMPLE_DIR)/src"
	@cp Cargo.toml "$(EXAMPLE_DIR)/Cargo.toml"
	@cp src/main.rs "$(EXAMPLE_DIR)/src/main.rs"
	@python3 tools/mesh3d_codegen.py assets/3d/play11_meshes.b64 "$(EXAMPLE_DIR)/src/mesh3d.rs"
	@cat assets/3d/play12_extra_chars.b64.00 \
		assets/3d/play12_extra_chars.b64.01 \
		assets/3d/play12_extra_chars.b64.02 \
		assets/3d/play12_extra_chars.b64.03 \
		assets/3d/play12_extra_chars.b64.04 \
		assets/3d/play12_extra_chars.b64.05 \
		> "$(EXAMPLE_DIR)/src/play12_extra_chars.b64"
	@python3 tools/extra_chars_codegen.py "$(EXAMPLE_DIR)/src/play12_extra_chars.b64" "$(EXAMPLE_DIR)/src/extra_chars.rs"
	@cat assets/3d/play11_ufo_tex.b64 | base64 -d | gzip -d > "$(EXAMPLE_DIR)/src/play11_ufo_tex.bin"
	@cat assets/3d/play11_zurg_tex.b64 | base64 -d | gzip -d > "$(EXAMPLE_DIR)/src/play11_zurg_tex.bin"
	@cat assets/presentation_ps1.b64 \
		assets/presentation_ps1.b64.01 \
		assets/presentation_ps1.b64.02 \
		assets/presentation_ps1.b64.03 \
		assets/presentation_ps1.b64.04 \
		assets/presentation_ps1.b64.05 \
		| base64 -d | gzip -d > "$(EXAMPLE_DIR)/src/presentation_ps1.bin"
	@cat assets/home_ps1.b64.00a \
		assets/home_ps1.b64.00b \
		assets/home_ps1.b64.00c \
		assets/home_ps1.b64.01 \
		assets/home_ps1.b64.02 \
		assets/home_ps1.b64.03 \
		assets/home_ps1.b64.04 \
		assets/home_ps1.b64.05 \
		assets/home_ps1.b64.06 \
		assets/home_ps1.b64.07 \
		| base64 -d | gzip -d > "$(EXAMPLE_DIR)/src/home_ps1.bin"
	@cat assets/india_ps1.b64 \
		assets/india_ps1.b64.01 \
		assets/india_ps1.b64.02 \
		assets/india_ps1.b64.03 \
		assets/india_ps1.b64.04a \
		assets/india_ps1.b64.04b \
		assets/india_ps1.b64.04c \
		assets/india_ps1.b64.05 \
		| base64 -d | gzip -d > "$(EXAMPLE_DIR)/src/india_ps1.bin"
	@cat assets/india_ui_ps1.b64 | base64 -d | gzip -d > "$(EXAMPLE_DIR)/src/india_ui_ps1.bin"
	@cat assets/prisma_fire_ps1.b64 | base64 -d | gzip -d > "$(EXAMPLE_DIR)/src/prisma_fire_ps1.bin"
	@if xz -t "$(INDIA_AUDIO_ARCHIVE)" >/dev/null 2>&1; then \
		tar -xJf "$(INDIA_AUDIO_ARCHIVE)" -C "$(EXAMPLE_DIR)/src"; \
	else \
		echo "INDIA audio archive is corrupt/unavailable; building diagnostic SPU test without INDIA stems"; \
	fi
	@python3 tools/input_compat.py "$(EXAMPLE_DIR)/src/main.rs"
	@python3 tools/splash_patch.py "$(EXAMPLE_DIR)/src/main.rs"
	@python3 tools/home_patch.py "$(EXAMPLE_DIR)/src/main.rs"
	@python3 tools/home_8bit_patch.py "$(EXAMPLE_DIR)/src/main.rs"
	@python3 tools/home_selector_patch.py "$(EXAMPLE_DIR)/src/main.rs"
	@python3 tools/india_patch.py "$(EXAMPLE_DIR)/src/main.rs"
	@python3 tools/india_controls_patch.py "$(EXAMPLE_DIR)/src/main.rs"
	@python3 tools/india_numbers_align_patch.py "$(EXAMPLE_DIR)/src/main.rs"
	@python3 tools/prisma_fire_patch.py "$(EXAMPLE_DIR)/src/main.rs"
	@if [ -f "$(EXAMPLE_DIR)/src/india_drum1.psau" ]; then \
		python3 tools/india_audio_patch.py "$(EXAMPLE_DIR)/src/main.rs"; \
	else \
		echo "Skipping INDIA audio patch for diagnostic build"; \
	fi
	@python3 tools/audio_instrument_test_patch.py "$(EXAMPLE_DIR)/src/main.rs"
	@python3 tools/gte_test_patch.py "$(EXAMPLE_DIR)/src/main.rs"
	@python3 tools/3d_play1_patch.py "$(EXAMPLE_DIR)/src/main.rs"
	@python3 tools/3d_play12_runtime_patch.py "$(EXAMPLE_DIR)/src/main.rs"
	@python3 tools/3d_play12_extra_chars_patch.py "$(EXAMPLE_DIR)/src/main.rs"

build: sync
	@$(MAKE) -C "$(PSOXIDE_DIR)" disc EXAMPLE=$(EXAMPLE)
	@mkdir -p "$(OUT_DIR)"
	@cp "$(PSX_OUT_DIR)/$(EXAMPLE).bin" "$(OUT_DIR)/$(EXAMPLE).bin"
	@cp "$(PSX_OUT_DIR)/$(EXAMPLE).cue" "$(OUT_DIR)/$(EXAMPLE).cue"
	@echo "Built $(OUT_DIR)/$(EXAMPLE).cue"

run: build
	@test -n "$(FRONTEND)" || (echo "Set FRONTEND=/absolute/path/to/frontend"; exit 1)
	@"$(FRONTEND)" launch --path "$(CURDIR)/$(OUT_DIR)/$(EXAMPLE).cue"

status:
	@echo "PSoXide repo: $(PSOXIDE_REPO)"
	@echo "PSoXide rev : $(PSOXIDE_REV)"
	@echo "Example     : $(EXAMPLE)"

clean:
	@rm -rf "$(OUT_DIR)"
	@if [ -d "$(EXAMPLE_DIR)" ]; then rm -rf "$(EXAMPLE_DIR)"; fi
