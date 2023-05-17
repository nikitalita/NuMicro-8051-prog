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
#pragma once

#include "config.h"

#ifdef __cplusplus
extern "C" {
#endif

int icp_init(uint8_t do_reset);
void icp_reentry(uint32_t delay1, uint32_t delay2);
void icp_exit(void);
uint32_t icp_read_device_id(void);
uint32_t icp_read_pid(void);
uint8_t icp_read_cid(void);
uint32_t icp_read_uid(void);
uint32_t icp_read_ucid(void);
uint32_t icp_read_flash(uint32_t addr, uint32_t len, uint8_t *data);
uint32_t icp_write_flash(uint32_t addr, uint32_t len, uint8_t *data);
void icp_mass_erase(void);
void icp_page_erase(uint32_t addr);
void outputf(const char *fmt, ...);
#ifdef PRINT_CONFIG_EN
void print_config(config_flags flags);
void icp_dump_config();
#endif
#ifdef __cplusplus
}
#endif
