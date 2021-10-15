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

#include <stdio.h>
#include <stdint.h>
#include <unistd.h>

int pgm_init(void);
void pgm_set_dat(int val);
int pgm_get_dat(void);
void pgm_set_rst(int val);
void pgm_set_clk(int val);
void pgm_dat_dir(int state);
void pgm_deinit(void);

#define FLASH_SIZE	(18 * 1024)
#define LDROM_MAX_SIZE	(4 * 1024)

#define APROM_FLASH_ADDR	0x0
#define CFG_FLASH_ADDR		0x30000
#define CFG_FLASH_LEN		5

#define CMD_READ_UID		0x04
#define CMD_READ_CID		0x0b
#define CMD_READ_DEVICE_ID	0x0c
#define CMD_READ_FLASH		0x00
#define CMD_WRITE_FLASH		0x21
#define CMD_MASS_ERASE		0x26
#define CMD_PAGE_ERASE		0x22

void icp_bitsend(uint32_t data, int len)
{
	/* configure DAT pin as output */
	pgm_dat_dir(1);

	int i = len;
	while (i--) {
		pgm_set_dat((data >> i) & 1);
		pgm_set_clk(1);
		pgm_set_clk(0);
	}
}

void icp_send_command(uint8_t cmd, uint32_t dat)
{
	icp_bitsend((dat << 6) | cmd, 24);
}

int icp_init(void)
{
	uint32_t icp_seq = 0x9e1cb6;
	int i = 24;
	int rc;

	rc = pgm_init();
        if (rc < 0) 
		return rc;

	while (i--) {
		pgm_set_rst((icp_seq >> i) & 1);
		usleep(10000);
	}

	usleep(100);

	icp_bitsend(0x5aa503, 24);

	return 0;
}

void icp_exit(void)
{
	pgm_set_rst(1);
	usleep(5000);
	pgm_set_rst(0);
	usleep(10000);
	icp_bitsend(0xf78f0, 24);
	usleep(500);
	pgm_set_rst(1);
	pgm_deinit();
}

uint8_t icp_read_byte(int end)
{
	pgm_dat_dir(0);

	uint8_t data = 0;
	int i = 8;

	while (i--) {
		int state = pgm_get_dat();
		pgm_set_clk(1);
		pgm_set_clk(0);
		data |= (state << i);
	}

	pgm_dat_dir(1);
	pgm_set_dat(end);
	pgm_set_clk(1);
	pgm_set_clk(0);
	pgm_set_dat(0);

	return data;
}

void icp_write_byte(uint8_t data, int end, int delay1, int delay2)
{
	icp_bitsend(data, 8);
	pgm_set_dat(end);
	usleep(delay1);
	pgm_set_clk(1);
	usleep(delay2);
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

	for (int i = 0; i < len; i++)
		data[i] = icp_read_byte(i == (len-1));

	return addr + len;
}

uint32_t icp_write_flash(uint32_t addr, uint32_t len, uint8_t *data)
{
	int progress_printed = 0;
	icp_send_command(CMD_WRITE_FLASH, addr);

	for (int i = 0; i < len; i++) {
		icp_write_byte(data[i], i == (len-1), 200, 50);

		/* print some progress */
		if (((i % 256) == 0) && len > CFG_FLASH_LEN) {
			fprintf(stderr, ".");
			progress_printed++;
		}
	}

	if (progress_printed)
		fprintf(stderr, "\n");

	return addr + len;
}

void icp_dump_config()
{
	uint8_t cfg[CFG_FLASH_LEN];
	icp_read_flash(CFG_FLASH_ADDR, CFG_FLASH_LEN, cfg);

	fprintf(stderr, "MCU Boot select:\t%s\n", cfg[0] & 0x80 ? "APROM" : "LDROM");

	int ldrom_size = (7 - (cfg[1] & 0x7)) * 1024;
	fprintf(stderr, "LDROM size:\t\t%d Bytes\n", ldrom_size);
	fprintf(stderr, "APROM size:\t\t%d Bytes\n", FLASH_SIZE - ldrom_size);
}

void icp_mass_erase(void)
{
	icp_send_command(CMD_MASS_ERASE, 0x3A5A5);
	icp_write_byte(0xff, 1, 100000, 10000);
}

void icp_page_erase(uint32_t addr)
{
	icp_send_command(CMD_PAGE_ERASE, addr);
	icp_write_byte(0xff, 1, 10000, 1000);
}
