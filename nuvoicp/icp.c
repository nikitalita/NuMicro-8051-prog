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

#include <stdint.h>
#include <stdarg.h>
#include <stdio.h>
#include "config.h"
#include "icp.h"
#include "pgm.h"
#include "delay.h"

// These are MCU dependent (default for N76E003)
static int program_time = 20;
static int page_erase_time = 5000;

// to avoid overhead from calling usleep() for 0 us
#define USLEEP(x) if (x > 0) pgm_usleep(x)

#ifdef _DEBUG
#define DEBUG_PRINT(x) icp_outputf(x)
// time measurement
static unsigned long usstart_time = 0;
static unsigned long usend_time = 0;
#define DEBUG_TIMER_START usstart_time = pgm_get_time();
#define DEBUG_TIMER_END usend_time = pgm_get_time();
#define DEBUG_PRINT_TIME(funcname) icp_outputf(#funcname " took %d us\n", usend_time - usstart_time)
#else
#define DEBUG_PRINT(x)
#define TIMER_START
#define DEBUG_TIMER_END
#define DEBUG_PRINT_TIME(funcname)
#endif
#define ENTRY_BIT_DELAY 60



static void icp_bitsend(uint32_t data, int len, uint32_t udelay)
{
	pgm_dat_dir(1);
	int i = len;
	while (i--){
			pgm_set_dat((data >> i) & 1);
			USLEEP(udelay);
			pgm_set_clk(1);
			USLEEP(udelay);
			pgm_set_clk(0);
	}	
}

static void icp_send_command(uint8_t cmd, uint32_t dat)
{
	icp_bitsend((dat << 6) | cmd, 24, DEFAULT_BIT_DELAY);
}

int send_reset_seq(uint32_t reset_seq, int len){
	for (int i = 0; i < len + 1; i++) {
		pgm_set_rst((reset_seq >> (len - i)) & 1);
		USLEEP(10000);
	}
	return 0;
}

void icp_send_entry_bits() {
	icp_bitsend(ENTRY_BITS, 24, ENTRY_BIT_DELAY);
}

void icp_send_exit_bits(){
	icp_bitsend(EXIT_BITS, 24, ENTRY_BIT_DELAY);
}

int icp_init(uint8_t do_reset)
{
	int rc;

	rc = pgm_init();
    if (rc < 0) {
		return rc;
	} else if (rc != 0){
		return -1;
	}
	icp_entry(do_reset);
	uint32_t dev_id = icp_read_device_id();
	if (dev_id >> 8 == 0x2F){
		printf("Device ID mismatch: %x\n", dev_id);
		return -1;
	}
	return 0;
}

void icp_entry(uint8_t do_reset) {
	if (do_reset) {
		send_reset_seq(ICP_RESET_SEQ, 24);
	} else {
		pgm_set_rst(1);
		USLEEP(5000);
		pgm_set_rst(0);
		USLEEP(1000);
	}
	
	USLEEP(100);
	icp_send_entry_bits();
	USLEEP(10);
}

void icp_reentry(uint32_t delay1, uint32_t delay2, uint32_t delay3) {
	USLEEP(10);
	if (delay1 > 0) {
		pgm_set_rst(1);
		USLEEP(delay1);
	}
	pgm_set_rst(0);
	USLEEP(delay2);
	icp_send_entry_bits();
	USLEEP(delay3);
}

void icp_fullexit_entry_glitch(uint32_t delay1, uint32_t delay2, uint32_t delay3){
	icp_exit();
}

void icp_reentry_glitch(uint32_t delay1, uint32_t delay2, uint32_t delay_after_trigger_high, uint32_t delay_before_trigger_low){
	USLEEP(200);
	// this bit here it to ensure that the config bytes are read at the correct time (right next to the reset high)
	pgm_set_rst(1);
	USLEEP(delay1);
	pgm_set_rst(0);
	USLEEP(delay2);

	//now we do a the full reentry, set the trigger
	pgm_set_trigger(1);
	USLEEP(delay_after_trigger_high);
	pgm_set_rst(1);

	// by default, we sleep for 280us, the length of the config load
	if (delay_before_trigger_low == 0) {
		delay_before_trigger_low = 280;
	}

	if (delay_before_trigger_low > delay1){
		USLEEP(delay1);
		pgm_set_rst(0);
		USLEEP(delay_before_trigger_low - delay1);
		pgm_set_trigger(0);
	} else {
		USLEEP(delay_before_trigger_low);
		pgm_set_trigger(0);
		USLEEP(delay1 - delay_before_trigger_low);
		pgm_set_rst(0);
	}
	USLEEP(delay2);
	icp_send_entry_bits();
	USLEEP(10);
}

void icp_reentry_glitch_read(uint32_t delay1, uint32_t delay2, uint32_t delay_after_trigger_high, uint32_t delay_before_trigger_low, uint8_t * config_bytes) {
	icp_reentry_glitch(delay1, delay2, delay_after_trigger_high, delay_before_trigger_low);
	icp_read_flash(CFG_FLASH_ADDR, CFG_FLASH_LEN, config_bytes);
}

void icp_deinit(void)
{
	icp_exit();
	pgm_deinit(1);
}

void icp_exit(void)
{
	pgm_set_rst(1);
	USLEEP(5000);
	pgm_set_rst(0);
	USLEEP(10000);
	icp_send_exit_bits();
	USLEEP(500);
	pgm_set_rst(1);
}


static uint8_t icp_read_byte(int end)
{
	pgm_dat_dir(0);
	USLEEP(DEFAULT_BIT_DELAY);
	uint8_t data = 0;
	int i = 8;

	while (i--) {
		USLEEP(DEFAULT_BIT_DELAY);
		int state = pgm_get_dat();
		pgm_set_clk(1);
		USLEEP(DEFAULT_BIT_DELAY);
		pgm_set_clk(0);
		data |= (state << i);
	}

	pgm_dat_dir(1);
	USLEEP(DEFAULT_BIT_DELAY);
	pgm_set_dat(end);
	USLEEP(DEFAULT_BIT_DELAY);
	pgm_set_clk(1);
	USLEEP(DEFAULT_BIT_DELAY);
	pgm_set_clk(0);
	USLEEP(DEFAULT_BIT_DELAY);
	pgm_set_dat(0);

	return data;
}

static void icp_write_byte(uint8_t data, uint8_t end, uint32_t delay1, uint32_t delay2)
{
	icp_bitsend(data, 8, DEFAULT_BIT_DELAY);

	pgm_set_dat(end);
	USLEEP(delay1);
	pgm_set_clk(1);
	USLEEP(delay2);
	pgm_set_dat(0);
	pgm_set_clk(0);
}

uint32_t icp_read_device_id(void)
{
	icp_send_command(CMD_READ_DEVICE_ID, 0);

	uint8_t devid[2];
	devid[0] = icp_read_byte(0);
	devid[1] = icp_read_byte(1);

	return (devid[1] << 8) | devid[0];
}

uint32_t icp_read_pid(void){
	icp_send_command(CMD_READ_DEVICE_ID, 2);
	uint8_t pid[2];
	pid[0] = icp_read_byte(0);
	pid[1] = icp_read_byte(1);
	return (pid[1] << 8) | pid[0];
}

uint8_t icp_read_cid(void)
{
	icp_send_command(CMD_READ_CID, 0);
	return icp_read_byte(1);
}

void icp_read_uid(uint8_t * buf)
{

	for (uint8_t  i = 0; i < 12; i++) {
		icp_send_command(CMD_READ_UID, i);
		buf[i] = icp_read_byte(1);
	}
	// __uint128_t ret = 0;
	// for (uint8_t  i = 0; i < 12; i++) {
	// 	icp_send_command(CMD_READ_UID, i);
	// 	ret |= (icp_read_byte(1) << (i * 8));
	// }
	// return ret;
}

void icp_read_ucid(uint8_t * buf)
{
	for (uint8_t i = 0; i < 16; i++) {
		icp_send_command(CMD_READ_UID, i + 0x20);
		buf[i] = icp_read_byte(1);
	}

	// __uint128_t ret = 0;
	// for (uint8_t i = 0; i < 16; i++) {
	// 	icp_send_command(CMD_READ_UID, i + 0x20);
	// 	ret |= (icp_read_byte(1) << (i * 8));
	// }
	// return ret;
}

uint32_t icp_read_flash(uint32_t addr, uint32_t len, uint8_t *data)
{
	icp_send_command(CMD_READ_FLASH, addr);

	for (uint32_t i = 0; i < len; i++){
		data[i] = icp_read_byte(i == (len-1));
	}
	return addr + len;
}

uint32_t icp_write_flash(uint32_t addr, uint32_t len, uint8_t *data)
{
	icp_send_command(CMD_WRITE_FLASH, addr);
	int delay1 = program_time;
	for (uint32_t i = 0; i < len; i++) {
		icp_write_byte(data[i], i == (len-1), delay1, 5);
	}
		
	return addr + len;
}

void icp_mass_erase(void)
{
	icp_send_command(CMD_MASS_ERASE, 0x3A5A5);
	icp_write_byte(0xff, 1, 50000, 500);
}

void icp_page_erase(uint32_t addr)
{
	icp_send_command(CMD_PAGE_ERASE, addr);
	icp_write_byte(0xff, 1, page_erase_time, 100);
}

void icp_outputf(const char *s, ...)
{
  char buf[160];
  va_list ap;
  va_start(ap, s);
  vsnprintf(buf, 160, s, ap);
  va_end(ap);
  pgm_print(buf);
}

#ifdef PRINT_CONFIG_EN
void print_config(config_flags flags){
  icp_outputf("----- Chip Configuration ----\n");
  uint8_t *raw_bytes = (uint8_t *)&flags;
  icp_outputf("Raw config bytes:\t" );
  for (int i = 0; i < CFG_FLASH_LEN; i++){
    icp_outputf("%02X ", raw_bytes[i]);
  }
  icp_outputf("\nMCU Boot select:\t%s\n", flags.CBS ? "APROM" : "LDROM");
  int ldrom_size = (7 - (flags.LDS & 0x7)) * 1024;
  if (ldrom_size > LDROM_MAX_SIZE){
    ldrom_size = LDROM_MAX_SIZE;
  }
  icp_outputf("LDROM size:\t\t%d Bytes\n", ldrom_size);
  icp_outputf("APROM size:\t\t%d Bytes\n", FLASH_SIZE - ldrom_size);
  icp_outputf("Security lock:\t\t%s\n", flags.LOCK ? "UNLOCKED" : "LOCKED"); // this is switched, 1 is off and 0 is on
  icp_outputf("P2.0/Nrst reset:\t%s\n", flags.RPD ? "enabled" : "disabled");
  icp_outputf("On-Chip Debugger:\t%s\n", flags.OCDEN ? "disabled" : "enabled"); // this is switched, 1 is off and 0 is on
  icp_outputf("OCD halt PWM output:\t%s\n", flags.OCDPWM ? "tri-state pins are used as PWM outputs" : "PWM continues");
  icp_outputf("Brown-out detect:\t%s\n", flags.CBODEN ? "enabled" : "disabled");
  icp_outputf("Brown-out voltage:\t");
  switch (flags.CBOV) {
    case 0:
      icp_outputf("4.4V\n");
      break;
    case 1:
      icp_outputf("3.7V\n");
      break;
    case 2:
      icp_outputf("2.7V\n");
      break;
    case 3:
      icp_outputf("2.2V\n");
      break;
  }
  icp_outputf("Brown-out reset:\t%s\n", flags.CBORST ? "enabled" : "disabled");

  icp_outputf("WDT status:\t\t");
  switch (flags.WDTEN) {
    case 15: // 1111
      icp_outputf("WDT is Disabled. WDT can be used as a general purpose timer via software control.\n");
      break;
    case 5:  // 0101
      icp_outputf("WDT is Enabled as a time-out reset timer and it STOPS running during Idle or Power-down mode.\n");
      break;
    default:
      icp_outputf("WDT is Enabled as a time-out reset timer and it KEEPS running during Idle or Power-down mode\n");
      break;
  }
}

void icp_dump_config()
{
	config_flags flags;
	icp_read_flash(CFG_FLASH_ADDR, CFG_FLASH_LEN, (uint8_t *)&flags);
	print_config(flags);
}
#endif // PRINT_CONFIG_EN
