#
# SDCC Makefile for mcs51
# Modified for N76E003 bootloader
# ------------------------------------------------------

INCDIR  = inc
INCDIR2 = ../nuvoicp/common
MODEL  = small
DEFS = -DFOSC_166000

# ------------------------------------------------------
# SDCC
SRCDIR  = ./src
OBJDIR  = ./obj
OUTDIR  = ./out
LIBDIR  = ./lib
TARGET = $(OUTDIR)/bootloader

C_SRC := $(wildcard $(SRCDIR)/*.c $(LIBDIR)/*.c)
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

CFLAGS = -I$(INCDIR) -I$(INCDIR2) -m$(MCU_MODEL) --model-$(MODEL) --out-fmt-ihx --no-xinit-opt $(DEFS) --peep-file peep.def
CFLAGS+= --code-size 2048 --opt-code-size --fomit-frame-pointer --peep-asm --peep-return --std-c11 --acall-ajmp
LFLAGS = --code-size 2048 -m$(MCU_MODEL) --model-$(MODEL) --out-fmt-ihx $(DEFS)

# ------------------------------------------------------
# Recepies, see GNU MAKE manual

.PHONY: all

all: make-dirs $(TARGET).bin $(TARGET).hex

make-dirs:
	mkdir -p $(OBJDIR)
	mkdir -p $(OUTDIR)

$(OUTDIR)/%.hex: $(OBJDIR)/%.ihx
	packihx $^ > $@

$(OUTDIR)/%.bin: $(OBJDIR)/%.ihx
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
	rm -rf $(OBJDIR)/*
	rm -rf $(TARGET).hex
	rm -rf $(TARGET).bin
	rm -rf $(TARGET).asm


asm: $(CTOASM)

$(OUTDIR)/%.asm: $(LIBDIR)/%.c
	$(CC) -o $@ -S $(CFLAGS) -c $^

$(OUTDIR)/%.asm: $(SRCDIR)/%.c
	$(CC) -o $@ -S $(CFLAGS) -c $^
