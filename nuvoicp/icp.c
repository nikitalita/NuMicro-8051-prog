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

// These are MCU dependent (default for N76E003)
static int program_time = 20;
static int page_erase_time = 5000;

static void icp_bitsend(uint32_t data, int len, uint32_t udelay)
{
	/* configure DAT pin as output */
	pgm_dat_dir(1);
	int i = len;

	while (i--) {
		pgm_set_dat((data >> i) & 1);
		pgm_usleep(udelay);
		pgm_set_clk(1);
		pgm_usleep(udelay);
		pgm_set_clk(0);
	}
}

static void icp_send_command(uint8_t cmd, uint32_t dat)
{
	icp_bitsend((dat << 6) | cmd, 24, CMD_SEND_BIT_DELAY);
}

int reset_seq(uint32_t reset_seq, int len){
	for (int i = 0; i < len + 1; i++) {
		pgm_set_rst((reset_seq >> (len - i)) & 1);
		pgm_usleep(10000);
	}
	return 0;
}

void reset_glitch(){
	pgm_set_rst(1);
	pgm_set_rst(0);
}

void icp_send_entry_bits() {
	icp_bitsend(ENTRY_BITS, 24, 60);
}

void icp_send_exit_bits(){
	icp_bitsend(EXIT_BITS, 24, 60);
}

int icp_init(uint8_t do_reset)
{
	int rc;

	rc = pgm_init();
    if (rc != 0) 
		return rc;
	icp_entry(do_reset);
	return 0;
}

void icp_entry(uint8_t do_reset) {
	if (do_reset) {
		reset_seq(ALT_RESET_SEQ, 24);
	} else {
		pgm_set_rst(1);
		pgm_usleep(5000);
		pgm_set_rst(0);
		pgm_usleep(1000);
	}
	
	pgm_usleep(100);
	icp_send_entry_bits();
}

void icp_reentry(uint32_t delay1, uint32_t delay2, uint32_t delay3) {
	pgm_usleep(10);
	if (delay1 > 0) {
		pgm_set_rst(1);
		pgm_usleep(delay1);
	}
	pgm_set_rst(0);
	pgm_usleep(delay2);
	icp_bitsend(ENTRY_BITS, 24, 1);
	pgm_usleep(delay3);
}

void icp_fullexit_entry_glitch(uint32_t delay1, uint32_t delay2, uint32_t delay3){
	icp_exit();
}

void icp_reentry_glitch(uint32_t delay1, uint32_t delay2, uint32_t delay3){
	pgm_usleep(200);
	// this bit here it to ensure that the config bytes are read at the correct time (right next to the reset high)
	pgm_set_rst(1);
	pgm_usleep(delay1);
	pgm_set_rst(0);
	pgm_usleep(delay2);

	//now we do a the full reentry, set the trigger
	pgm_usleep(200);
	pgm_set_trigger(1);
	pgm_set_rst(1);

	// now we sleep for 270us, the length of the config load
	// done in starts because of pigpio limitations (max busy wait = 100us)
	pgm_usleep(100);
	pgm_usleep(100);
	pgm_usleep(70);
	// config bytes are loaded, set trigger = 0
	pgm_set_trigger(0);

	pgm_usleep(delay1 - 270);
	pgm_usleep(0);
	pgm_usleep(delay2);
	icp_bitsend(ENTRY_BITS, 24, 1);
	pgm_usleep(delay3);


	// pgm_set_rst(1);
	// pgm_set_trigger(1);
	// pgm_usleep(delay1);
	// pgm_set_rst(0);
	// pgm_usleep(delay2);
	// int i = 24;
	// // Only send the first 23 bits of the reset sequence
	// pgm_dat_dir(1);
	// while (i-- > 1) {
	// 	pgm_set_dat((ENTRY_BITS >> i) & 1);
	// 	pgm_usleep(1);
	// 	pgm_set_clk(1);
	// 	pgm_usleep(1);
	// 	pgm_set_clk(0);
	// }
	// // then send the last bit and set and unset the clk quickly
	// pgm_set_dat(ENTRY_BITS & 1);
	// pgm_usleep(1);
	// pgm_set_clk(1);
	// // if (trigger_after_entry){
	// // 	pgm_set_trigger(1);
	// // }
	// pgm_set_clk(0);
	// // no wait
}

void icp_reentry_glitch_read(uint32_t delay1, uint32_t delay2, uint32_t delay3, uint8_t * config_bytes) {
	icp_reentry_glitch(delay1, delay2, delay3);
	// for (i = 0; i < 100; i++)
	// 	reset_glitch();
	icp_read_flash(CFG_FLASH_ADDR, CFG_FLASH_LEN, config_bytes);
	
}

void icp_deinit(void)
{
	icp_exit();
	pgm_deinit();
}

void icp_exit(void)
{
	pgm_set_rst(1);
	pgm_usleep(5000);
	pgm_set_rst(0);
	pgm_usleep(10000);
	icp_bitsend(EXIT_BITS, 24, 60);
	pgm_usleep(500);
	pgm_set_rst(1);
}


#define READ_BYTE_SLEEP 1

static uint8_t icp_read_byte(int end)
{
	pgm_dat_dir(0);
	pgm_usleep(READ_BIT_DELAY);
	uint8_t data = 0;
	int i = 8;

	while (i--) {
		pgm_usleep(READ_BIT_DELAY);
		int state = pgm_get_dat();
		pgm_set_clk(1);
		pgm_usleep(READ_BIT_DELAY);
		pgm_set_clk(0);
		data |= (state << i);
	}

	pgm_dat_dir(1);
	pgm_usleep(READ_BIT_DELAY);
	pgm_set_dat(end);
	pgm_usleep(READ_BIT_DELAY);
	pgm_set_clk(1);
	pgm_usleep(READ_BIT_DELAY);
	pgm_set_clk(0);
	pgm_usleep(READ_BIT_DELAY);
	pgm_set_dat(0);

	return data;
}

static void icp_write_byte(uint8_t data, int end, int delay1, int delay2)
{
	icp_bitsend(data, 8, WRITE_BIT_DELAY);
	pgm_set_dat(end);
	pgm_usleep(delay1);
	pgm_set_clk(1);
	pgm_usleep(delay2);
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

uint32_t icp_read_uid(void)
{
	uint8_t uid[3];

	for (int i = 0; i < sizeof(uid); i++) {
		icp_send_command(CMD_READ_UID, i);
		uid[i] = icp_read_byte(1);
	}

	return (uid[2] << 16) | (uid[1] << 8) | uid[0];
}

uint32_t icp_read_ucid(void)
{
	uint8_t ucid[4];

	for (int i = 0; i < sizeof(ucid); i++) {
		icp_send_command(CMD_READ_UID, i + 0x20);
		ucid[i] = icp_read_byte(1);
	}

	return (ucid[3] << 24) | (ucid[2] << 16) | (ucid[1] << 8) | ucid[0];
}

uint32_t icp_read_flash(uint32_t addr, uint32_t len, uint8_t *data)
{
	icp_send_command(CMD_READ_FLASH, addr);

	for (int i = 0; i < len; i++){
		data[i] = icp_read_byte(i == (len-1));
	}
	return addr + len;
}

uint32_t icp_write_flash(uint32_t addr, uint32_t len, uint8_t *data)
{
	icp_send_command(CMD_WRITE_FLASH, addr);
	int delay1 = program_time;
	for (int i = 0; i < len; i++) {
		icp_write_byte(data[i], i == (len-1), delay1, 5);
	}
		
	return addr + len;
}

void icp_mass_erase(void)
{
	icp_send_command(CMD_MASS_ERASE, 0x3A5A5);
	icp_write_byte(0xff, 1, 100000, 10000);
}

void icp_page_erase(uint32_t addr)
{
	icp_send_command(CMD_PAGE_ERASE, addr);
	icp_write_byte(0xff, 1, page_erase_time, 1000);
}

void outputf(const char *s, ...)
{
  char buf[160];
  va_list ap;
  va_start(ap, s);
  vsnprintf(buf, 160, s, ap);
  va_end(ap);
  pgm_print(buf);
}

// disabled for microcontroller targets to avoid storing a large number of strings in flash
#ifdef PRINT_CONFIG_EN
void print_config(config_flags flags){
  outputf("----- Chip Configuration ----\n");
  uint8_t *raw_bytes = (uint8_t *)&flags;
  outputf("Raw config bytes:\t" );
  for (int i = 0; i < CFG_FLASH_LEN; i++){
    outputf("%02X ", raw_bytes[i]);
  }
  outputf("\nMCU Boot select:\t%s\n", flags.CBS ? "APROM" : "LDROM");
  int ldrom_size = (7 - (flags.LDS & 0x7)) * 1024;
  if (ldrom_size > LDROM_MAX_SIZE){
    ldrom_size = LDROM_MAX_SIZE;
  }
  outputf("LDROM size:\t\t%d Bytes\n", ldrom_size);
  outputf("APROM size:\t\t%d Bytes\n", FLASH_SIZE - ldrom_size);
  outputf("Security lock:\t\t%s\n", flags.LOCK ? "UNLOCKED" : "LOCKED"); // this is switched, 1 is off and 0 is on
  outputf("P2.0/Nrst reset:\t%s\n", flags.RPD ? "enabled" : "disabled");
  outputf("On-Chip Debugger:\t%s\n", flags.OCDEN ? "disabled" : "enabled"); // this is switched, 1 is off and 0 is on
  outputf("OCD halt PWM output:\t%s\n", flags.OCDPWM ? "tri-state pins are used as PWM outputs" : "PWM continues");
  outputf("Brown-out detect:\t%s\n", flags.CBODEN ? "enabled" : "disabled");
  outputf("Brown-out voltage:\t");
  switch (flags.CBOV) {
    case 0:
      outputf("4.4V\n");
      break;
    case 1:
      outputf("3.7V\n");
      break;
    case 2:
      outputf("2.7V\n");
      break;
    case 3:
      outputf("2.2V\n");
      break;
  }
  outputf("Brown-out reset:\t%s\n", flags.CBORST ? "enabled" : "disabled");

  outputf("WDT status:\t\t");
  switch (flags.WDTEN) {
    case 15: // 1111
      outputf("WDT is Disabled. WDT can be used as a general purpose timer via software control.\n");
      break;
    case 5:  // 0101
      outputf("WDT is Enabled as a time-out reset timer and it STOPS running during Idle or Power-down mode.\n");
      break;
    default:
      outputf("WDT is Enabled as a time-out reset timer and it KEEPS running during Idle or Power-down mode\n");
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