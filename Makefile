PSOXIDE_REPO ?= https://github.com/EBonura/PSoXide.git
PSOXIDE_REV  ?= 3cf22179d8798e8ce5899743fdcf222fc9486a8a
PSOXIDE_DIR  ?= .psoxide
EXAMPLE      := primapi
EXAMPLE_DIR  := $(PSOXIDE_DIR)/sdk/examples/$(EXAMPLE)
OUT_DIR      := build
PSX_OUT_DIR  := $(PSOXIDE_DIR)/build/examples/mipsel-sony-psx/release
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
