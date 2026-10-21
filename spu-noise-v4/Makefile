PSOXIDE_REPO ?= https://github.com/EBonura/PSoXide.git
PSOXIDE_REV  ?= 3cf22179d8798e8ce5899743fdcf222fc9486a8a
PSOXIDE_DIR  ?= .psoxide-spu-noise-v4
EXAMPLE      := spu-noise-v4
EXAMPLE_DIR  := $(PSOXIDE_DIR)/sdk/examples/$(EXAMPLE)
OUT_DIR      := spu-noise-v4/build
PSX_OUT_DIR  := $(PSOXIDE_DIR)/build/examples/mipsel-sony-psx/release

.PHONY: setup sync build clean

setup:
	@if [ ! -d "$(PSOXIDE_DIR)/.git" ]; then \
		git clone "$(PSOXIDE_REPO)" "$(PSOXIDE_DIR)"; \
	fi
	@cd "$(PSOXIDE_DIR)" && git checkout --detach "$(PSOXIDE_REV)"

sync: setup
	@mkdir -p "$(EXAMPLE_DIR)/src"
	@cp spu-noise-v4/Cargo.toml "$(EXAMPLE_DIR)/Cargo.toml"
	@cp spu-noise-v4/src/main.rs "$(EXAMPLE_DIR)/src/main.rs"

build: sync
	@$(MAKE) -C "$(PSOXIDE_DIR)" disc EXAMPLE=$(EXAMPLE)
	@mkdir -p "$(OUT_DIR)"
	@cp "$(PSX_OUT_DIR)/$(EXAMPLE).bin" "$(OUT_DIR)/$(EXAMPLE).bin"
	@cp "$(PSX_OUT_DIR)/$(EXAMPLE).cue" "$(OUT_DIR)/$(EXAMPLE).cue"
	@echo "Built $(OUT_DIR)/$(EXAMPLE).cue"

clean:
	@rm -rf "$(OUT_DIR)" "$(EXAMPLE_DIR)"
