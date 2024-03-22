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



int N51PGM_init(void)
{
	int ret;
	// Pi 5 compatibility: check for the existence of gpiochip4
	chip = gpiod_chip_open_by_name("gpiochip4");
	if (!chip) {
		// Pi 3-4
		chip = gpiod_chip_open_by_name("gpiochip0");
	}
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

void N51PGM_set_dat(uint8_t val)
{
	if (gpiod_line_set_value(dat_line, val) < 0)
		fprintf(stderr, "Setting data line failed\n");
}

uint8_t N51PGM_get_dat(void)
{
	int ret = gpiod_line_get_value(dat_line);
	if (ret < 0)
		fprintf(stderr, "Getting data line failed\n");
	return ret;
}

void N51PGM_set_rst(uint8_t val)
{
	if (gpiod_line_set_value(rst_line, val) < 0)
		fprintf(stderr, "Setting reset line failed\n");
}

void N51PGM_set_clk(uint8_t val)
{
	if (gpiod_line_set_value(clk_line, val) < 0)
		fprintf(stderr, "Setting clock line failed\n");
}

void N51PGM_dat_dir(uint8_t state)
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



uint32_t N51PGM_usleep(uint32_t usec)
{
	if (usec == 0)
		return 0;

	if (usec > MAX_BUSY_DELAY)
	{
		return usleep(usec);
	}
    uint64_t start_time = N51PGM_get_time();
	uint64_t curr_time;
	uint64_t utimepassed = 0;
	while (true){
		curr_time = N51PGM_get_time();
		utimepassed = curr_time - start_time;
		if (utimepassed > usec){
			break;
		}
    }
	return utimepassed;
}

void N51PGM_print(const char *msg)
{
	fprintf(stderr,"%s", msg);
}
#ifdef _DEBUG
#define DEBUG_PRINT(msg, ...) fprintf(stderr, msg)
#else
#define DEBUG_PRINT(msg, ...)
#endif
int get_prev_flags(struct gpiod_line * line){
	int ret = 0;
	if (gpiod_line_is_open_drain(line)){
		ret |= GPIOD_LINE_REQUEST_FLAG_OPEN_DRAIN;
		DEBUG_PRINT("line is open drain\n");
	}
	if (gpiod_line_is_open_source(line)){
		ret |= GPIOD_LINE_REQUEST_FLAG_OPEN_SOURCE;
		DEBUG_PRINT("line is open source\n");
	}
	// if (gpiod_line_is_active_low(line)){
	// 	ret |= GPIOD_LINE_REQUEST_FLAG_ACTIVE_LOW;
	// 	DEBUG_PRINT("line is active low\n");
	// }
	if (gpiod_line_bias(line) == GPIOD_LINE_BIAS_DISABLE){
		ret |= GPIOD_LINE_REQUEST_FLAG_BIAS_DISABLE;
		DEBUG_PRINT("line is bias disabled\n");
	} else if (gpiod_line_bias(line) == GPIOD_LINE_BIAS_PULL_UP){
		ret |= GPIOD_LINE_REQUEST_FLAG_BIAS_PULL_UP;
		DEBUG_PRINT("line is bias pull up\n");
	} else if (gpiod_line_bias(line) == GPIOD_LINE_BIAS_PULL_DOWN){
		ret |= GPIOD_LINE_REQUEST_FLAG_BIAS_PULL_DOWN;
		DEBUG_PRINT("line is bias pull down\n");
	} else if (gpiod_line_bias(line) == GPIOD_LINE_BIAS_AS_IS){
		DEBUG_PRINT("line is bias unknown\n");
	}
	return ret;
}
#define LOWER_FLAG_MASK (GPIOD_LINE_REQUEST_FLAG_OPEN_DRAIN | GPIOD_LINE_REQUEST_FLAG_OPEN_SOURCE | GPIOD_LINE_REQUEST_FLAG_ACTIVE_LOW)

void N51PGM_release_pin(struct gpiod_line * line){
	if (!line || !chip){
		return;
	}
	int flags = (get_prev_flags(line) & LOWER_FLAG_MASK) | GPIOD_LINE_REQUEST_FLAG_BIAS_DISABLE;
	gpiod_line_set_config(line, GPIOD_LINE_REQUEST_DIRECTION_INPUT, flags, 0);
	gpiod_line_release(line);
}

void N51PGM_release_non_reset_pins(void){
	if (dat_line) {
		DEBUG_PRINT("Releasing dat line\n");
		N51PGM_release_pin(dat_line);
	}
	if (clk_line) {
		DEBUG_PRINT("Releasing clk line\n");
		N51PGM_release_pin(clk_line);
	}
	if (trigger_line) {
		DEBUG_PRINT("Releasing trigger line\n");
		N51PGM_release_pin(trigger_line);
	}
}

void N51PGM_release_rst(void) {
	if (rst_line) {
		DEBUG_PRINT("Releasing rst line\n");
		N51PGM_release_pin(rst_line);
	}
}

void N51PGM_release_pins(void){
	N51PGM_release_non_reset_pins();
	N51PGM_release_rst();
}

void N51PGM_deinit(uint8_t leave_reset_high)
{
	if (leave_reset_high){
		N51PGM_set_rst(1);
		N51PGM_release_non_reset_pins();
	} else {
		N51PGM_release_pins();
	}
	if (chip) {
		gpiod_chip_close(chip);
	}
}


uint64_t N51PGM_get_time(){
	struct timespec curr_time;
	clock_gettime(CLOCK_MONOTONIC_RAW, &curr_time);
	return (curr_time.tv_sec * 1000000) + (curr_time.tv_nsec / 1000);
}

void N51PGM_set_trigger(uint8_t val){
	if (gpiod_line_set_value(trigger_line, val) < 0)
		fprintf(stderr, "Setting trigger line failed\n");
}

#endif
