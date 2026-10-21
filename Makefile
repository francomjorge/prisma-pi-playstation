# Raw PS1 SPU register diagnostic
PSOXIDE_REPO ?= https://github.com/EBonura/PSoXide.git
PSOXIDE_REV  ?= 3cf22179d8798e8ce5899743fdcf222fc9486a8a
PSOXIDE_DIR  ?= .psoxide
EXAMPLE      := hello-audio
OUT_DIR      := build
PSX_OUT_DIR  := $(PSOXIDE_DIR)/build/examples/mipsel-sony-psx/release
HELLO_AUDIO_SRC := $(PSOXIDE_DIR)/sdk/examples/hello-audio/src/main.rs

.PHONY: setup build clean status

setup:
	@if [ ! -d "$(PSOXIDE_DIR)/.git" ]; then \
		git clone "$(PSOXIDE_REPO)" "$(PSOXIDE_DIR)"; \
	fi
	@cd "$(PSOXIDE_DIR)" && git checkout --detach "$(PSOXIDE_REV)"

build: setup
	@cp diagnostics/raw_spu_beep.rs "$(HELLO_AUDIO_SRC)"
	@$(MAKE) -C "$(PSOXIDE_DIR)" disc EXAMPLE=$(EXAMPLE)
	@mkdir -p "$(OUT_DIR)"
	@cp "$(PSX_OUT_DIR)/$(EXAMPLE).bin" "$(OUT_DIR)/primapi.bin"
	@cp "$(PSX_OUT_DIR)/$(EXAMPLE).cue" "$(OUT_DIR)/primapi.cue"
	@echo "Built raw SPU beep diagnostic"

status:
	@echo "PSoXide rev : $(PSOXIDE_REV)"
	@echo "Example     : $(EXAMPLE)"
	@echo "Mode        : RAW SPU MMIO BEEP"

clean:
	@rm -rf "$(OUT_DIR)" "$(PSOXIDE_DIR)"
