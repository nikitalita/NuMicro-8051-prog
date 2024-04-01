#
# SDCC Makefile for mcs51
# Modified for N76E003 bootloader
# ------------------------------------------------------

PINCDIR  = inc
EXTRAINCDIRS = ../nuvo51icp/common
MODEL  = small
_OBJDIR = objdir
_TARGET = bootloader

LDROM_SIZE = 2048

DEFS =

ifeq ($(PLATFORM),)
    $(warning PLATFORM not defined, defaulting to N76E003)
    PLATFORM := N76E003
endif

OBJDIR = $(_OBJDIR)-$(PLATFORM)
$(info PLATFORM: $(PLATFORM))
$(info OBJDIR: $(OBJDIR))

TARGET = $(_TARGET)-$(PLATFORM)

ifeq ($(PLATFORM), N76E003)
    SUPPORTS_24MHZ = 0
    DEFAULT_CLK = FOSC_166000
    INCDIR = $(PINCDIR)/N76E003
    # PRG Size = 18K Bytes
    MAX_APROM_SIZE = 18432
    # INT-MEM Size = 256 Bytes
    # 18432 - LDROM_SISZE
    APROM_SIZE = 16384
    IRAM_SIZE = 256
    # EXT-MEM Size = 768 Bytes
    XRAM_SIZE = 768
else ifeq ($(PLATFORM), N76S003)
    SUPPORTS_24MHZ = 0
    DEFAULT_CLK = FOSC_166000
    INCDIR = $(PINCDIR)/N76S003
    MAX_APROM_SIZE = 18432
    # INT-MEM Size = 256 Bytes
    IRAM_SIZE = 256
    # EXT-MEM Size = 1K Bytes
    XRAM_SIZE = 1024
else ifeq ($(PLATFORM), MS5116K)
    SUPPORTS_24MHZ = 1
    DEFAULT_CLK = FOSC_240000
    INCDIR = $(PINCDIR)/MS5116K
    # PRG Size = 16K Bytes
    MAX_APROM_SIZE = 16384
    # INT-MEM Size = 256 Bytes
    IRAM_SIZE = 256
    # EXT-MEM Size = 1K Bytes
    XRAM_SIZE = 1024
else ifeq ($(PLATFORM), MS5132K)
    SUPPORTS_24MHZ = 1
    DEFAULT_CLK = FOSC_240000
    INCDIR = $(PINCDIR)/MS5132K
    # PRG Size = 32K Bytes
    MAX_APROM_SIZE = 32768
    # INT-MEM Size = 256 Bytes
    IRAM_SIZE = 256
    # EXT-MEM Size = 2K Bytes
    XRAM_SIZE = 2048
else
    $(error Unsupported PLATFORM: $(PLATFORM))
endif

DEFS += -D$(DEFAULT_CLK) -DMAX_APROM_SIZE=$(MAX_APROM_SIZE) -DLDROM_SIZE=$(LDROM_SIZE)

# ------------------------------------------------------
# SDCC
SRCDIR  = ./src

C_SRC := $(wildcard $(SRCDIR)/*.c)
ASM_SRC = $(wildcard $(SRCDIR)/*.asm)

C_SRC_FILE = $(notdir $(C_SRC))
C_OBJ_FILE = $(C_SRC_FILE:%.c=%.c.rel)
C_TO_ASM_FILE = $(C_SRC_FILE:%.c=%.asm)

ASM_SRC_FILE = $(notdir $(ASM_SRC))
ASM_OBJ_FILE = $(ASM_SRC_FILE:%.asm=%.asm.rel)

OBJ = $(addprefix $(OBJDIR)/, $(C_OBJ_FILE)) $(addprefix $(OBJDIR)/, $(ASM_OBJ_FILE))
CTOASM = $(addprefix $(OUTDIR)/, $(C_TO_ASM_FILE))



CC = sdcc
MCU_MODEL = mcs51

CFLAGS = -D__SDCC__=1 -I$(INCDIR) -m$(MCU_MODEL) --model-$(MODEL)
CFLAGS += --out-fmt-ihx --no-xinit-opt $(DEFS) --peep-file peep.def
CFLAGS += --code-size $(LDROM_SIZE) --iram-size $(IRAM_SIZE) --xram-size $(XRAM_SIZE)
CFLAGS += --opt-code-size --fomit-frame-pointer --peep-asm --peep-return --std-c11 --acall-ajmp
CFLAGS += $(patsubst %,-I%,$(EXTRAINCDIRS))

LFLAGS = --code-size 2048 -m$(MCU_MODEL) --model-$(MODEL) --out-fmt-ihx $(DEFS)
# ------------------------------------------------------
# Recepies, see GNU MAKE manual

.PHONY: all

all: make-dirs $(TARGET).bin $(TARGET).hex

make-dirs:
	mkdir -p $(OBJDIR)

%.hex: $(OBJDIR)/%.ihx
	packihx $^ > $@

%.bin: $(OBJDIR)/%.ihx
	makebin -p $^ $@

$(OBJDIR)/%.ihx: $(OBJ)
	$(CC) -o $@ $(LFLAGS) $^

$(OBJDIR)/%.c.rel: $(LIBDIR)/%.c
	$(CC) -o $@ $(CFLAGS) -c $^

$(OBJDIR)/%.c.rel: $(SRCDIR)/%.c
	$(CC) -o $@ $(CFLAGS) -c $^

$(OBJDIR)/%.asm.rel: $(SRCDIR)/%.asm
	$(AS) $(AFLAGS) -o $@ $^

.PHONY: clean

clean:
	rm -rf $(_OBJDIR)-*/*
	rm -rf $(_TARGET)*.hex
	rm -rf $(_TARGET)*.bin
	rm -rf $(_TARGET)*.asm


asm: $(CTOASM)

%.asm: %.c
	$(CC) -o $@ -S $(CFLAGS) -c $^

