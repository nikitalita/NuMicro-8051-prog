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

#ifdef RPI

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <unistd.h>
#include <string.h>
#include <stdbool.h>

#include "icp.h"

#define N76E003_DEVID	0x3650

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

typedef struct _device_info{
	uint16_t devid;
	uint8_t cid;
	uint32_t uid;
	uint32_t ucid;
} device_info;

device_info get_device_info() {
	device_info info;
	info.devid = icp_read_device_id();
	info.cid = icp_read_cid();
	info.uid = icp_read_uid();
	info.ucid = icp_read_ucid();
	return info;
}

void print_device_info(device_info info){
	printf("Device ID:\t0x%04x (%s)\n", info.devid, info.devid == N76E003_DEVID ? "N76E003" : "unknown");
	printf("CID:\t\t0x%02x\n", info.cid);
	printf("UID:\t\t0x%08x\n", info.uid);
	printf("UCID:\t\t0x%08x\n", info.ucid);
}

static const uint8_t blank_cfg[CFG_FLASH_LEN] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF};

config_flags get_default_config() {
	return *(config_flags *)&blank_cfg;
}

void usage(void)
{
	fprintf(stderr,
		"nuvoicp, a RPi ICP flasher for the Nuvoton N76E003\n"
		"written by Steve Markgraf <steve@steve-m.de>\n\n"
		"Usage:\n"
		"\t[-h print this help]\n"
		"\t[-c print chip configuration and exit]\n"
		"\t[-r <filename> read entire flash to file]\n"
		"\t[-w <filename> write file to APROM/entire flash (if LDROM is disabled)]\n"
		"\t[-l <filename> write file to LDROM, enable LDROM, enable boot from LDROM]\n"
		"\t[-s lock the chip after writing]\n"
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
	int read_aprom = 0;
	int aprom_program_size = 0, ldrom_program_size = 0;
	bool dump_config = false;
	bool lock_chip = false;
	char *filename = NULL, *filename_ldrom = NULL;
	FILE *file = NULL, *file_ldrom = NULL;
	uint8_t read_data[FLASH_SIZE], write_data[FLASH_SIZE], ldrom_data[LDROM_MAX_SIZE];

	memset(read_data, 0xff, sizeof(read_data));
	memset(write_data, 0xff, sizeof(write_data));
	memset(ldrom_data, 0xff, sizeof(ldrom_data));
	if (argc <= 1) {
		usage();
		return -1;
	}

	while ((opt = getopt(argc, argv, "chsr:w:l:")) != -1) {
		switch (opt) {
		case 'c':
			dump_config = true;
			break;
		case 'r':
			filename = optarg;
			read_aprom = 1;
			break;
		case 'w':
			filename = optarg;
			write_aprom = 1;
			break;
		case 'l':
			filename_ldrom = optarg;
			write_ldrom = 1;
			break;
		case 's':
		  lock_chip = true;
			break;
		case 'h':
		default:
			fprintf(stderr, "ERROR: Unknown option: %c\n\n", opt);
			usage();
			break;
		}
		if (dump_config){
			break;
		}
	}
	if (read_aprom && write_aprom) {
		fprintf(stderr, "ERROR: Can't read and write APROM at the same time!\n\n");
		usage();
	}
	if (!read_aprom && !write_aprom && !dump_config) {
		fprintf(stderr, "ERROR: No action specified!\n\n");
		usage();
	}

	if (!dump_config) {
	  if (filename) {
	  	file = fopen(filename, write_aprom ? "rb" : "wb");
			if (!file) {
				fprintf(stderr, "ERROR: Failed to open file: %s!\n\n", filename);
				usage();
			}
		}
	  if (filename_ldrom) {
	  	file_ldrom = fopen(filename_ldrom, "rb");
			if (!file_ldrom) {
				fprintf(stderr, "ERROR: Failed to open file: %s!\n\n", filename_ldrom);
				usage();
			}
		}
	}

	if (icp_init(true) != 0) {
		fprintf(stderr, "ERROR: Failed to initialize ICP!\n\n");
		goto err;
	}
	device_info devinfo = get_device_info();
	// chip's locked, re-enter ICP mode to reload the flash
	if (devinfo.cid == 0xFF) {
		icp_reentry(5000, 1000, 10);
		devinfo = get_device_info();
	}
	
	if (devinfo.devid != N76E003_DEVID)
	{
		if ((write_ldrom == 1 || write_aprom == 1) && devinfo.cid == 0xFF) {
			// prompt for user input
			fprintf(stderr, "N76E003 not found (may be locked), do you want to attempt a mass erase? (y/N)\n");
			// take user input
			char c = getchar();
			if (c == 'y' || c == 'Y') {
				fprintf(stderr, "Attempting mass erase...\n");
			}
		} else {
			print_device_info(devinfo);
			fprintf(stderr, "ERROR: N76E003 not found!\n\n");
			goto out_err;
		}
	}

	config_flags current_config;
	icp_read_flash(CFG_FLASH_ADDR, CFG_FLASH_LEN, (uint8_t *)&current_config);
	if (current_config.LOCK == 0 && write_aprom == 0 && write_ldrom == 0) {
		print_device_info(devinfo);
		print_config(current_config);
		fprintf(stderr, "ERROR: Device is locked, cannot read flash!\n\n");
		goto out_err;
	}

	/* Erase entire flash */
	if (write_aprom || write_ldrom) {
		icp_mass_erase();
		// we have to reinitialize if it was previously locked
		if (current_config.LOCK == 0 || devinfo.cid == 0xFF){
			icp_reentry(5000, 1000, 10);
		}
	}
	print_device_info(devinfo);
	print_config(current_config);

	if (dump_config)
		goto out;

	int chosen_ldrom_sz = 0;

	config_flags write_config = get_default_config();
	if (write_ldrom) {
		fprintf(stderr, "Programming LDROM...\n");
		ldrom_program_size = fread(ldrom_data, 1, LDROM_MAX_SIZE, file_ldrom);
		uint8_t chosen_ldrom_sz_kb = ((ldrom_program_size - 1) / 1024) + 1;
		chosen_ldrom_sz = chosen_ldrom_sz_kb * 1024;
		write_config.CBS = 0; // boot from LDROM
		write_config.LDS = ((7 - chosen_ldrom_sz_kb) & 0x7); // config LDROM size
		// write the config
		icp_write_flash(CFG_FLASH_ADDR, CFG_FLASH_LEN, (uint8_t *)&write_config);
		/* program LDROM */
		icp_write_flash(FLASH_SIZE - chosen_ldrom_sz, ldrom_program_size, ldrom_data);
		fprintf(stderr, "Programmed LDROM (%d bytes)\n", ldrom_program_size);
	}

	if (write_aprom) {
		fprintf(stderr, "Programming APROM...\n");
		int aprom_size = FLASH_SIZE - chosen_ldrom_sz;
		aprom_program_size = fread(write_data, 1, aprom_size, file);

		/* program flash */
		icp_write_flash(APROM_FLASH_ADDR, aprom_program_size, write_data);
		fprintf(stderr, "Programmed APROM (%d bytes)\n", aprom_program_size);
	}

	if (write_aprom || write_ldrom) {
		/* verify flash */
		icp_read_flash(APROM_FLASH_ADDR, FLASH_SIZE, read_data);

		/* copy the LDROM content in the buffer of the entire flash for
		 * verification */
		memcpy(&write_data[FLASH_SIZE - chosen_ldrom_sz], ldrom_data, chosen_ldrom_sz);
		if (memcmp(write_data, read_data, FLASH_SIZE)) {
			icp_dump_config();
			fprintf(stderr, "\nError when verifying flash!\n");
			goto out_err;
		}
		fprintf(stderr, "\nEntire Flash verified successfully!\n");
		// we need to write the lock bits AFTER verifying because we will be unable to read it afterwards
		if (lock_chip) {
			write_config.LOCK = 0;
			icp_write_flash(CFG_FLASH_ADDR, CFG_FLASH_LEN, (uint8_t *)&write_config);
		}
		icp_dump_config();
	} else {
		icp_dump_config();
		icp_read_flash(APROM_FLASH_ADDR, FLASH_SIZE, read_data);

		/* save flash content to file */
		if (fwrite(read_data, 1, FLASH_SIZE, file) != FLASH_SIZE) {
			fprintf(stderr, "Error writing file!\n");
			goto out_err;
		}
		else
			fprintf(stderr, "\nFlash successfully read.\n");
	}

out:
	icp_exit();
	return 0;
out_err:
	icp_exit();
err:
	return 1;
}

#endif
