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

#include <unistd.h>
#include <gpiod.h>
#include <stdio.h>
#include <errno.h>

#include "pgm.h"

/* GPIO line numbers for RPi, must be changed for other SBCs */
#define GPIO_DAT 20
#define GPIO_RST 21
#define GPIO_CLK 26

#define GPIO_TRIGGER 16

#define MAX_BUSY_DELAY 300

// GPIOD is slow enough that there will be at least 750ns between line cycles, so no delay necessary


#define CONSUMER "nuvoicp"
struct gpiod_chip *chip;
struct gpiod_line *dat_line, *rst_line, *clk_line, *trigger_line;

int pgm_init(void)
{
	int ret;

	chip = gpiod_chip_open_by_name("gpiochip0");
	if (!chip)
	{
		fprintf(stderr, "Open chip failed\n");
		return -ENOENT;
	}

	dat_line = gpiod_chip_get_line(chip, GPIO_DAT);
	rst_line = gpiod_chip_get_line(chip, GPIO_RST);
	clk_line = gpiod_chip_get_line(chip, GPIO_CLK);
	trigger_line = gpiod_chip_get_line(chip, GPIO_TRIGGER);
	if (!dat_line || !clk_line || !rst_line || !trigger_line)
	{
		fprintf(stderr, "Error getting required GPIO lines!\n");
		return -ENOENT;
	}

	ret = gpiod_line_request_input(dat_line, CONSUMER);
	ret |= gpiod_line_request_output(rst_line, CONSUMER, 0);
	ret |= gpiod_line_request_output(clk_line, CONSUMER, 0);
	ret |= gpiod_line_request_output(trigger_line, CONSUMER, 0);

	if (ret < 0)
	{
		fprintf(stderr, "Request line as output failed\n");
		return -ENOENT;
	}

	return 0;
}

void pgm_set_dat(unsigned char val)
{
	if (gpiod_line_set_value(dat_line, val) < 0)
		fprintf(stderr, "Setting data line failed\n");
}

unsigned char pgm_get_dat(void)
{
	int ret = gpiod_line_get_value(dat_line);
	if (ret < 0)
		fprintf(stderr, "Getting data line failed\n");
	return ret;
}

void pgm_set_rst(unsigned char val)
{
	if (gpiod_line_set_value(rst_line, val) < 0)
		fprintf(stderr, "Setting reset line failed\n");
}

void pgm_set_clk(unsigned char val)
{
	if (gpiod_line_set_value(clk_line, val) < 0)
		fprintf(stderr, "Setting clock line failed\n");
}

void pgm_dat_dir(unsigned char state)
{
	// gpiod_line_release(dat_line);
	int ret;
	if (state)
		ret = gpiod_line_set_direction_output(dat_line, 0);
	else
		ret = gpiod_line_set_direction_input(dat_line);

	if (ret < 0)
		fprintf(stderr, "Setting data directions failed\n");
}



unsigned long pgm_usleep(unsigned long usec)
{
	if (usec == 0)
		return 0;

	if (usec > MAX_BUSY_DELAY)
	{
		return usleep(usec);
	}
    struct timespec start_time;
    int nsec = usec * 1000;
    clock_gettime(CLOCK_MONOTONIC_RAW, &start_time);

    struct timespec curr_time;
    clock_gettime(CLOCK_MONOTONIC_RAW, &curr_time);
	long ntimepassed = 0;
	while (true){
		clock_gettime(CLOCK_MONOTONIC_RAW, &curr_time);
		ntimepassed = (curr_time.tv_nsec - start_time.tv_nsec);
		long secspassed = (curr_time.tv_sec - start_time.tv_sec);
		if (secspassed > 0){
			ntimepassed += ((curr_time.tv_sec - start_time.tv_sec) * 1000000);
		}
		if (ntimepassed > nsec){
			break;
		}
    }
	return ntimepassed / 1000;
}

void pgm_print(const char *msg)
{
	fprintf(stderr,"%s", msg);
}

void pgm_release_non_reset_pins(void){
	if (dat_line) {
		gpiod_line_release(dat_line);
	}
	if (clk_line) {
		gpiod_line_release(clk_line);
	}
	if (trigger_line) {
		gpiod_line_release(trigger_line);
	}
}

void pgm_release_rst(void) {
	if (rst_line) {
		gpiod_line_release(rst_line);
	}
}

void pgm_release_pins(void){
	pgm_release_non_reset_pins();
	pgm_release_rst();
}

void pgm_deinit(unsigned char leave_reset_high)
{
	if (leave_reset_high){
		pgm_set_rst(1);
		pgm_release_non_reset_pins();
	} else {
		pgm_release_pins();
	}
	if (chip) {
		gpiod_chip_close(chip);
	}
}

void pgm_set_trigger(unsigned char val){
	if (gpiod_line_set_value(trigger_line, val) < 0)
		fprintf(stderr, "Setting trigger line failed\n");
}

#endif
