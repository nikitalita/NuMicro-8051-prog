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

#define MAX_BUSY_DELAY 100

// GPIOD is slow enough that there will be at least 750ns between line cycles, so no delay necessary
int CMD_SEND_BIT_DELAY = 0;
int READ_BIT_DELAY = 0;
int WRITE_BIT_DELAY = 0;

#define CONSUMER "nuvoicp"
struct gpiod_chip *chip;
struct gpiod_line *dat_line, *rst_line, *clk_line;

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
	if (!dat_line || !clk_line || !rst_line)
	{
		fprintf(stderr, "Error getting required GPIO lines!\n");
		return -ENOENT;
	}

	ret = gpiod_line_request_input(dat_line, CONSUMER);
	ret |= gpiod_line_request_output(rst_line, CONSUMER, 0);
	ret |= gpiod_line_request_output(clk_line, CONSUMER, 0);
	if (ret < 0)
	{
		fprintf(stderr, "Request line as output failed\n");
		return -ENOENT;
	}

	return 0;
}

void pgm_set_dat(int val)
{
	if (gpiod_line_set_value(dat_line, val) < 0)
		fprintf(stderr, "Setting data line failed\n");
}

int pgm_get_dat(void)
{
	int ret = gpiod_line_get_value(dat_line);
	if (ret < 0)
		fprintf(stderr, "Getting data line failed\n");
	return ret;
}

void pgm_set_rst(int val)
{
	if (gpiod_line_set_value(rst_line, val) < 0)
		fprintf(stderr, "Setting reset line failed\n");
}

void pgm_set_clk(int val)
{
	if (gpiod_line_set_value(clk_line, val) < 0)
		fprintf(stderr, "Setting clock line failed\n");
}

void pgm_dat_dir(int state)
{
	int ret;
	if (state)
		ret = gpiod_line_set_direction_output(dat_line, 0);
	else
		ret = gpiod_line_set_direction_input(dat_line);

	if (ret < 0)
		fprintf(stderr, "Setting data directions failed\n");
}

void pgm_deinit(void)
{
	/* release reset */
	pgm_set_rst(1);

	gpiod_chip_close(chip);
}

void pgm_usleep(unsigned long usec)
{
	if (usec == 0)
		return;
		
	if (usec > MAX_BUSY_DELAY)
	{
		usleep(usec);
		return;
	}
    struct timespec start_time;
    int nsec = usec * 1000;
    clock_gettime(CLOCK_MONOTONIC_RAW, &start_time);

    // Perform your time-sensitive operations
    struct timespec curr_time;
    clock_gettime(CLOCK_MONOTONIC_RAW, &curr_time);
	for ( ; curr_time.tv_nsec - start_time.tv_nsec < nsec; clock_gettime(CLOCK_MONOTONIC_RAW, &curr_time)){
    };
}

void pgm_print(const char *msg)
{
	fprintf(stderr, msg);
}

#endif
