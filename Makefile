# Direct PS1 SPU MMIO beep diagnostic
PSOXIDE_REPO ?= https://github.com/EBonura/PSoXide.git
PSOXIDE_REV  ?= 3cf22179d8798e8ce5899743fdcf222fc9486a8a
PSOXIDE_DIR  ?= .psoxide
EXAMPLE      := hello-audio
EXAMPLE_DIR  := $(PSOXIDE_DIR)/sdk/examples/$(EXAMPLE)
OUT_DIR      := build
PSX_OUT_DIR  := $(PSOXIDE_DIR)/build/examples/mipsel-sony-psx/release

.PHONY: setup sync build clean status

setup:
	@if [ ! -d "$(PSOXIDE_DIR)/.git" ]; then \
		git clone "$(PSOXIDE_REPO)" "$(PSOXIDE_DIR)"; \
	fi
	@cd "$(PSOXIDE_DIR)" && git checkout --detach "$(PSOXIDE_REV)"

sync: setup
	@cp tools/direct_spu_beep.rs "$(EXAMPLE_DIR)/src/main.rs"

build: sync
	@$(MAKE) -C "$(PSOXIDE_DIR)" disc EXAMPLE=$(EXAMPLE)
	@mkdir -p "$(OUT_DIR)"
	@cp "$(PSX_OUT_DIR)/$(EXAMPLE).bin" "$(OUT_DIR)/primapi.bin"
	@cp "$(PSX_OUT_DIR)/$(EXAMPLE).cue" "$(OUT_DIR)/primapi.cue"
	@echo "Built direct SPU MMIO beep diagnostic"

status:
	@echo "PSoXide rev : $(PSOXIDE_REV)"
	@echo "Example     : $(EXAMPLE)"
	@echo "Mode        : direct SPU MMIO beep"

clean:
	@rm -rf "$(OUT_DIR)" "$(PSOXIDE_DIR)"
