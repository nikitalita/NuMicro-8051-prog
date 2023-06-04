/*
 * nuvoicp, a RPi ICP flasher for the Nuvoton N76E003
 * https://github.com/steve-m/N76E003-playground
 *
 * Copyright (c) 2021 Steve Markgraf <steve@steve-m.de>
 *
 * Permission is hereby granted, free of charge, to any person obtaining
 * a copy of this software and associated documentation files (the
 * "Software"), to deal in the Software without restriction, including
 * without limitation the rights to use, copy, modify, merge, publish,
 * distribute, sublicense, and/or sell copies of the Software, and to
 * permit persons to whom the Software is furnished to do so, subject to
 * the following conditions:
 *
 * The above copyright notice and this permission notice shall be included
 * in all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
 * EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
 * MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
 * IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
 * CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
 * TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
 * SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 */
#pragma once

#include "config.h"

// N76E003 device constants
#define N76E003_DEVID	    0x3650
#define APROM_FLASH_ADDR	0x0
#define CFG_FLASH_ADDR		0x30000
#define CFG_FLASH_LEN		5
#define LDROM_MAX_SIZE      (4 * 1024)
#define FLASH_SIZE	        (18 * 1024)

// ICP Commands
#define CMD_READ_UID		0x04
#define CMD_READ_CID		0x0b
#define CMD_READ_DEVICE_ID	0x0c
#define CMD_READ_FLASH		0x00
#define CMD_WRITE_FLASH		0x21
#define CMD_MASS_ERASE		0x26
#define CMD_PAGE_ERASE		0x22


// ICP Entry sequence
#define ENTRY_BITS    0x5aa503

// ICP Reset sequence: ICP toggles RST pin according to this bit sequence
#define ICP_RESET_SEQ 0x9e1cb6

// Alternative Reset sequence earlier nulink firmware revisions used
#define ALT_RESET_SEQ 0xAE1CB6

// ICP Exit sequence
#define EXIT_BITS     0xF78F0


#ifdef __cplusplus
extern "C" {
#endif

void icp_send_entry_bits();
void icp_send_exit_bits();
int icp_init(uint8_t do_reset);
void icp_entry(uint8_t do_reset);
void icp_reentry(uint32_t delay1, uint32_t delay2, uint32_t delay3);
void icp_reentry_glitch(uint32_t delay1, uint32_t delay2, uint32_t delay_after_trigger_high, uint32_t delay_before_trigger_low);
void icp_reentry_glitch_read(uint32_t delay1, uint32_t delay2, uint32_t delay_after_trigger_high, uint32_t delay_before_trigger_low, uint8_t * config_bytes);
void icp_deinit(void);
void icp_exit(void);
uint32_t icp_read_device_id(void);
uint32_t icp_read_pid(void);
uint8_t icp_read_cid(void);
uint32_t icp_read_uid(void);
uint32_t icp_read_ucid(void);
uint32_t icp_read_flash(uint32_t addr, uint32_t len, uint8_t *data);
uint32_t icp_write_flash(uint32_t addr, uint32_t len, uint8_t *data);
void icp_mass_erase(void);
void icp_page_erase(uint32_t addr);
void outputf(const char *fmt, ...);

// disabled for microcontroller targets to avoid storing a large number of strings in flash
#ifdef PRINT_CONFIG_EN
void print_config(config_flags flags);
void icp_dump_config();
#endif
#ifdef __cplusplus
}
#endif
