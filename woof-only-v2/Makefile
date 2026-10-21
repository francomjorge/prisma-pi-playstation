PSOXIDE_REPO ?= https://github.com/EBonura/PSoXide.git
PSOXIDE_REV  ?= 3cf22179d8798e8ce5899743fdcf222fc9486a8a
PSOXIDE_DIR  ?= .psoxide-woof-only-v2
EXAMPLE      := woof-only-v2
EXAMPLE_DIR  := $(PSOXIDE_DIR)/sdk/examples/$(EXAMPLE)
OUT_DIR      := woof-only-v2/build
PSX_OUT_DIR  := $(PSOXIDE_DIR)/build/examples/mipsel-sony-psx/release
WOOF_SHA256  := c27a964da823587f8145a8d153ed05633cbeb2e560486568d23429aace0c1f59

.PHONY: setup sync build clean

setup:
	@if [ ! -d "$(PSOXIDE_DIR)/.git" ]; then \
		git clone "$(PSOXIDE_REPO)" "$(PSOXIDE_DIR)"; \
	fi
	@cd "$(PSOXIDE_DIR)" && git checkout --detach "$(PSOXIDE_REV)"

sync: setup
	@mkdir -p "$(EXAMPLE_DIR)/src"
	@cp woof-only-v2/Cargo.toml "$(EXAMPLE_DIR)/Cargo.toml"
	@cp woof-only-v2/src/main.rs "$(EXAMPLE_DIR)/src/main.rs"
	@cat audio-autoplay-test/assets/woof.psau.b64.* | base64 -d > "$(EXAMPLE_DIR)/src/woof.psau"
	@echo "$(WOOF_SHA256)  $(EXAMPLE_DIR)/src/woof.psau" | sha256sum -c -

build: sync
	@$(MAKE) -C "$(PSOXIDE_DIR)" disc EXAMPLE=$(EXAMPLE)
	@mkdir -p "$(OUT_DIR)"
	@cp "$(PSX_OUT_DIR)/$(EXAMPLE).bin" "$(OUT_DIR)/WOOF_ONLY_V2.bin"
	@printf 'FILE "WOOF_ONLY_V2.bin" BINARY\n  TRACK 01 MODE2/2352\n    INDEX 01 00:00:00\n' > "$(OUT_DIR)/WOOF_ONLY_V2.cue"
	@echo "Built $(OUT_DIR)/WOOF_ONLY_V2.cue"

clean:
	@rm -rf "$(OUT_DIR)" "$(EXAMPLE_DIR)"
