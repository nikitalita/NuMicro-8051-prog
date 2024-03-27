/*
 * nuvo51icp, a RPi ICP flasher for the Nuvoton N76E003
 * https://github.com/steve-m/N76E003-playground
 *
 * Copyright (c) 2021 Steve Markgraf <steve@steve-m.de>
 * Copyright (c) 2023-2024 Nikita Lita
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

#include <stdint.h>
#include <stdarg.h>
#include <stdio.h>
#include "config.h"
#include "n51_icp.h"
#include "n51_pgm.h"
#include "delay.h"

// These are MCU dependent (default for N76E003)
static int program_time = 20;
static int page_erase_time = 6000;

// to avoid overhead from calling usleep() for 0 us
#define USLEEP(x) if (x > 0) N51PGM_usleep(x)

#ifdef _DEBUG
#define DEBUG_PRINT(x) N51ICP_outputf(x)
#else
#define DEBUG_PRINT(x)
#endif
#define ENTRY_BIT_DELAY 60

#define LEAVE_RESET_HIGH 1
#define SUPPORT_OTHER_CHIPS 0

static void N51ICP_bitsend(uint32_t data, int len, uint32_t udelay)
{
	N51PGM_dat_dir(1);
	int i = len;
	while (i--){
			N51PGM_set_dat((data >> i) & 1);
			USLEEP(udelay);
			N51PGM_set_clk(1);
			USLEEP(udelay);
			N51PGM_set_clk(0);
	}
}

static void N51ICP_send_command(uint8_t cmd, uint32_t dat)
{
	N51ICP_bitsend((dat << 6) | cmd, 24, DEFAULT_BIT_DELAY);
}

int send_reset_seq(uint32_t reset_seq, int len){
	for (int i = 0; i < len + 1; i++) {
		N51PGM_set_rst((reset_seq >> (len - i)) & 1);
		USLEEP(10000);
	}
	return 0;
}

void N51ICP_send_entry_bits() {
	N51ICP_bitsend(ENTRY_BITS, 24, ENTRY_BIT_DELAY);
}

void N51ICP_send_exit_bits(){
	N51ICP_bitsend(EXIT_BITS, 24, ENTRY_BIT_DELAY);
}

int N51ICP_init(uint8_t do_reset)
{
	int rc;
	if (!N51PGM_is_init()) {
		rc = N51PGM_init();
		if (rc < 0) {
			return rc;
		} else if (rc != 0){
			return -1;
		}
	}
	N51ICP_enter_icp_mode(do_reset);
	uint32_t dev_id = N51ICP_read_device_id();
#if !SUPPORT_OTHER_CHIPS
	if (dev_id >> 8 == 0x2F){
		printf("Device ID mismatch: %x\n", dev_id);
		return -1;
	}
#endif
	return 0;
}

void N51ICP_enter_icp_mode(uint8_t do_reset) {
	if (do_reset) {
		send_reset_seq(ICP_RESET_SEQ, 24);
	} else {
		N51PGM_set_rst(1);
		USLEEP(5000);
		N51PGM_set_rst(0);
		USLEEP(1000);
	}
	
	USLEEP(100);
	N51ICP_send_entry_bits();
	USLEEP(10);
}

void N51ICP_reentry(uint32_t delay1, uint32_t delay2, uint32_t delay3) {
	USLEEP(10);
	if (delay1 > 0) {
		N51PGM_set_rst(1);
		USLEEP(delay1);
	}
	N51PGM_set_rst(0);
	USLEEP(delay2);
	N51ICP_send_entry_bits();
	USLEEP(delay3);
}

void N51ICP_fullexit_entry_glitch(uint32_t delay1, uint32_t delay2, uint32_t delay3){
	N51ICP_exit_icp_mode();
}

void N51ICP_reentry_glitch(uint32_t delay1, uint32_t delay2, uint32_t delay_after_trigger_high, uint32_t delay_before_trigger_low){
	USLEEP(200);
	// this bit here it to ensure that the config bytes are read at the correct time (right next to the reset high)
	N51PGM_set_rst(1);
	USLEEP(delay1);
	N51PGM_set_rst(0);
	USLEEP(delay2);

	//now we do a the full reentry, set the trigger
	N51PGM_set_trigger(1);
	USLEEP(delay_after_trigger_high);
	N51PGM_set_rst(1);

	// by default, we sleep for 280us, the length of the config load
	if (delay_before_trigger_low == 0) {
		delay_before_trigger_low = 280;
	}

	if (delay_before_trigger_low > delay1){
		USLEEP(delay1);
		N51PGM_set_rst(0);
		USLEEP(delay_before_trigger_low - delay1);
		N51PGM_set_trigger(0);
	} else {
		USLEEP(delay_before_trigger_low);
		N51PGM_set_trigger(0);
		USLEEP(delay1 - delay_before_trigger_low);
		N51PGM_set_rst(0);
	}
	USLEEP(delay2);
	N51ICP_send_entry_bits();
	USLEEP(10);
}

void N51ICP_reentry_glitch_read(uint32_t delay1, uint32_t delay2, uint32_t delay_after_trigger_high, uint32_t delay_before_trigger_low, uint8_t * config_bytes) {
	N51ICP_reentry_glitch(delay1, delay2, delay_after_trigger_high, delay_before_trigger_low);
	N51ICP_read_flash(CFG_FLASH_ADDR, CFG_FLASH_LEN, config_bytes);
}

void N51ICP_deinit(void)
{
	if (N51PGM_is_init()){
		N51ICP_exit_icp_mode();
	}
	N51PGM_deinit(LEAVE_RESET_HIGH);
}

void N51ICP_pgm_deinit_only(uint8_t leave_reset_high)
{
	N51PGM_deinit(leave_reset_high);
}

void N51ICP_exit_icp_mode(void)
{
	N51PGM_set_rst(1);
	USLEEP(5000);
	N51PGM_set_rst(0);
	USLEEP(10000);
	N51ICP_send_exit_bits();
	USLEEP(500);
	N51PGM_set_rst(1);
}


static uint8_t N51ICP_read_byte(int end)
{
	N51PGM_dat_dir(0);
	USLEEP(DEFAULT_BIT_DELAY);
	uint8_t data = 0;
	int i = 8;

	while (i--) {
		USLEEP(DEFAULT_BIT_DELAY);
		int state = N51PGM_get_dat();
		N51PGM_set_clk(1);
		USLEEP(DEFAULT_BIT_DELAY);
		N51PGM_set_clk(0);
		data |= (state << i);
	}

	N51PGM_dat_dir(1);
	USLEEP(DEFAULT_BIT_DELAY);
	N51PGM_set_dat(end);
	USLEEP(DEFAULT_BIT_DELAY);
	N51PGM_set_clk(1);
	USLEEP(DEFAULT_BIT_DELAY);
	N51PGM_set_clk(0);
	USLEEP(DEFAULT_BIT_DELAY);
	N51PGM_set_dat(0);

	return data;
}

static void N51ICP_write_byte(uint8_t data, uint8_t end, uint32_t delay1, uint32_t delay2)
{
	N51ICP_bitsend(data, 8, DEFAULT_BIT_DELAY);

	N51PGM_set_dat(end);
	USLEEP(delay1);
	N51PGM_set_clk(1);
	USLEEP(delay2);
	N51PGM_set_dat(0);
	N51PGM_set_clk(0);
}

uint32_t N51ICP_read_device_id(void)
{
	N51ICP_send_command(N51ICP_CMD_READ_DEVICE_ID, 0);

	uint8_t devid[2];
	devid[0] = N51ICP_read_byte(0);
	devid[1] = N51ICP_read_byte(1);

	return (devid[1] << 8) | devid[0];
}

uint32_t N51ICP_read_pid(void){
	N51ICP_send_command(N51ICP_CMD_READ_DEVICE_ID, 2);
	uint8_t pid[2];
	pid[0] = N51ICP_read_byte(0);
	pid[1] = N51ICP_read_byte(1);
	return (pid[1] << 8) | pid[0];
}

uint8_t N51ICP_read_cid(void)
{
	N51ICP_send_command(N51ICP_CMD_READ_CID, 0);
	return N51ICP_read_byte(1);
}

void N51ICP_read_uid(uint8_t * buf)
{

	for (uint8_t  i = 0; i < 12; i++) {
		N51ICP_send_command(N51ICP_CMD_READ_UID, i);
		buf[i] = N51ICP_read_byte(1);
	}
}

void N51ICP_read_ucid(uint8_t * buf)
{
	for (uint8_t i = 0; i < 16; i++) {
		N51ICP_send_command(N51ICP_CMD_READ_UID, i + 0x20);
		buf[i] = N51ICP_read_byte(1);
	}
}

uint32_t N51ICP_read_flash(uint32_t addr, uint32_t len, uint8_t *data)
{
	if (len == 0) {
		return 0;
	}
	N51ICP_send_command(N51ICP_CMD_READ_FLASH, addr);

	for (uint32_t i = 0; i < len; i++){
		data[i] = N51ICP_read_byte(i == (len-1));
	}
	return addr + len;
}

uint32_t N51ICP_write_flash(uint32_t addr, uint32_t len, uint8_t *data)
{
	if (len == 0) {
		return 0;
	}
	N51ICP_send_command(N51ICP_CMD_WRITE_FLASH, addr);
	int delay1 = program_time;
	for (uint32_t i = 0; i < len; i++) {
		N51ICP_write_byte(data[i], i == (len-1), delay1, 5);
	}

	return addr + len;
}

void N51ICP_mass_erase(void)
{
	N51ICP_send_command(N51ICP_CMD_MASS_ERASE, 0x3A5A5);
	N51ICP_write_byte(0xff, 1, 65000, 500);
}

void N51ICP_page_erase(uint32_t addr)
{
	N51ICP_send_command(N51ICP_CMD_PAGE_ERASE, addr);
	N51ICP_write_byte(0xff, 1, page_erase_time, 100);
}

void N51ICP_outputf(const char *s, ...)
{
  char buf[160];
  va_list ap;
  va_start(ap, s);
  vsnprintf(buf, 160, s, ap);
  va_end(ap);
  N51PGM_print(buf);
}
