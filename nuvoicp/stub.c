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

#ifndef ARDUINO

#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>

static int8_t dat_dir = -1;
static int8_t dat = -1;
static int8_t rst = -1;
static int8_t clk = -1;
static uint8_t pgm_init_done = false;

int pgm_init(void)
{
	return 0;
}

void pgm_set_dat(unsigned char val)
{
	if (dat_dir == 1) {
		printf("%d", val);
		dat = val;
	} else {
		printf("pgm_set_dat() called while dat_dir == 0\n");
	}
	
}

unsigned char pgm_get_dat(void)
{
	if (dat_dir == 0){
		return dat;
	} else {
		printf("pgm_get_dat() called while dat_dir == 1\n");
		return 0;
	}
}

void pgm_set_rst(unsigned char val)
{
	rst = val;
}

void pgm_set_clk(unsigned char val)
{
	clk = val;
}

void pgm_dat_dir(unsigned char state)
{
	dat_dir = state;
}

void pgm_deinit(unsigned char leave_reset_high)
{
	if (leave_reset_high)
		pgm_set_rst(1);
	else{
		rst = -1;
	}
	clk = -1;
	dat = -1;
	dat_dir = -1;
	pgm_init_done = false;

}

void pgm_release_pins(void)
{
	rst = -1;
	clk = -1;
	dat = -1;
	dat_dir = -1;
}

void pgm_release_rst(void)
{
	rst = -1;
}

void pgm_set_trigger(void)
{
	printf("pgm_set_trigger() called\n");
}

unsigned long pgm_usleep(unsigned long usec)
{
	return usec;
}

void pgm_print(const char *msg)
{
	printf("%s", msg);
}

#endif
