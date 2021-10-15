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
#include <stdlib.h>
#include <stdint.h>
#include <unistd.h>
#include <string.h>

#include "icp.h"

#define N76E003_DEVID	0x3650


void usage(void)
{
	fprintf(stderr,
		"nuvoicp, an ICP flasher for the Nuvoton N76E003\n"
		"written by Steve Markgraf <steve@steve-m.de>\n\n"
		"Usage:\n"
		"\t[-r <filename> read entire flash to file]\n"
		"\t[-w <filename> write file to APROM/entire flash (if LDROM is disabled)]\n"
		"\t[-l <filename> write file to LDROM, enable LDROM, enable boot from LDROM]\n"
		"\nPinout:\n\n"
		"                           40-pin header J8\n"
		" connect 3.3V of MCU ->    3V3  (1) (2)  5V\n"
		"                                 [...]\n"
		"        connect CLK ->  GPIO26 (37) (38) GPIO20 <- connect DAT\n"
		"        connect GND ->     GND (39) (40) GPIO21 <- connect RST\n\n"
		"                      ________\n"
		"                     |   USB  |\n"
		"                     |  PORTS |\n"
		"                     |________|\n\n"
		"Please refer to the 'pinout' command on your RPi\n");
	exit(1);
}

int main(int argc, char *argv[])
{
	int opt;
	int write_aprom = 0, write_ldrom = 0;
	int aprom_program_size = 0, ldrom_program_size = 0;
	char *filename = NULL, *filename_ldrom = NULL;
	FILE *file = NULL, *file_ldrom = NULL;
	uint8_t read_data[FLASH_SIZE], write_data[FLASH_SIZE], ldrom_data[LDROM_MAX_SIZE];

	memset(read_data, 0xff, sizeof(read_data));
	memset(write_data, 0xff, sizeof(write_data));
	memset(ldrom_data, 0xff, sizeof(ldrom_data));

	while ((opt = getopt(argc, argv, "r:w:l:")) != -1) {
		switch (opt) {
		case 'r':
			filename = optarg;
			break;
		case 'w':
			filename = optarg;
			write_aprom = 1;
			break;
		case 'l':
			filename_ldrom = optarg;
			write_ldrom = 1;
			break;
		case 'h':
		default:
			usage();
			break;
		}
	}

	if (filename)
		file = fopen(filename, write_aprom ? "rb" : "wb");

	if (filename_ldrom)
		file_ldrom = fopen(filename_ldrom, "rb");

	if (!(file || file_ldrom)) {
		fprintf(stderr, "Failed to open file!\n\n");
		usage();
		goto err;
	}

	if (icp_init() < 0)
		goto err;

	uint16_t devid = icp_read_device_id();

	if (devid == N76E003_DEVID)
		fprintf(stderr, "Found N76E003\n");
	else {
		fprintf(stderr, "Unknown Device ID: 0x%04x\n", devid);
		goto out;
	}

	uint8_t cid = icp_read_cid();

	fprintf(stderr,"CID\t\t\t0x%02x\n", cid);
	fprintf(stderr,"UID\t\t\t0x%06x\n", icp_read_uid());
	fprintf(stderr,"UCID\t\t\t0x%08x\n", icp_read_ucid());

	/* Erase entire flash */
	if (write_aprom || write_ldrom)
		icp_mass_erase();

	int chosen_ldrom_sz = 0;

	if (write_ldrom) {
		ldrom_program_size = fread(ldrom_data, 1, LDROM_MAX_SIZE, file_ldrom);
		uint8_t chosen_ldrom_sz_kb = ((ldrom_program_size - 1) / 1024) + 1;
		uint8_t ldrom_sz_cfg = (7 - chosen_ldrom_sz_kb) & 0x7;
		chosen_ldrom_sz = chosen_ldrom_sz_kb * 1024;

		/* configure LDROM size and enable boot from LDROM */
		uint8_t cfg[CFG_FLASH_LEN] = { 0x7f, 0xf8 | ldrom_sz_cfg, 0xff, 0xff, 0xff };
		icp_write_flash(CFG_FLASH_ADDR, CFG_FLASH_LEN, cfg);

		/* program LDROM */
		icp_write_flash(FLASH_SIZE - chosen_ldrom_sz, ldrom_program_size, ldrom_data);
		fprintf(stderr, "Programmed LDROM (%d bytes)\n", ldrom_program_size);
	}

	if (write_aprom) {
		int aprom_size = FLASH_SIZE - chosen_ldrom_sz;
		aprom_program_size = fread(write_data, 1, aprom_size, file);

		/* program flash */
		icp_write_flash(APROM_FLASH_ADDR, aprom_program_size, write_data);
		fprintf(stderr, "Programmed APROM (%d bytes)\n", aprom_program_size);
	}

	icp_dump_config();

	if (write_aprom || write_ldrom) {
		/* verify flash */
		icp_read_flash(APROM_FLASH_ADDR, FLASH_SIZE, read_data);

		/* copy the LDROM content in the buffer of the entire flash for
		 * verification */
		memcpy(&write_data[FLASH_SIZE - chosen_ldrom_sz], ldrom_data, chosen_ldrom_sz);
		if (memcmp(write_data, read_data, FLASH_SIZE))
			fprintf(stderr, "\nError when verifying flash!\n");
		else
			fprintf(stderr, "\nEntire Flash verified successfully!\n");
	} else {
		icp_read_flash(APROM_FLASH_ADDR, FLASH_SIZE, read_data);

		/* save flash content to file */
		if (fwrite(read_data, 1, FLASH_SIZE, file) != FLASH_SIZE)
			fprintf(stderr, "Error writing file!\n");
		else
			fprintf(stderr, "\nFlash successfully read.\n");
	}

out:
	icp_exit();
	return 0;

err:
	return 1;
}
