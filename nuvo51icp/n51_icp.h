/*
 * nuvo51icp, a RPi ICP flasher for the Nuvoton N76E003
 * https://github.com/steve-m/N76E003-playground
 *
 * Copyright (c) 2021 Steve Markgraf <steve@steve-m.de>
 * Copyright (c) 2023-2024 Nikita Lita
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

// ICP Commands
#define N51ICP_CMD_READ_UID		    0x04
#define N51ICP_CMD_READ_CID		    0x0b
#define N51ICP_CMD_READ_DEVICE_ID	0x0c
#define N51ICP_CMD_READ_FLASH		0x00
#define N51ICP_CMD_WRITE_FLASH		0x21
#define N51ICP_CMD_MASS_ERASE		0x26
#define N51ICP_CMD_PAGE_ERASE		0x22


// ICP Entry sequence
#define ENTRY_BITS    0x5aa503

// ICP Reset sequence: ICP toggles RST pin according to this bit sequence
#define ICP_RESET_SEQ 0x9e1cb6

// Alternative Reset sequence earlier nulink firmware revisions used
#define ALT_RESET_SEQ 0xAE1CB6

// ICP Exit sequence
#define EXIT_BITS     0xF78F0


#ifdef __cplusplus
extern "C" {
#endif

void N51ICP_send_entry_bits();
void N51ICP_send_exit_bits();
int N51ICP_init(uint8_t do_reset);
void N51ICP_enter_icp_mode(uint8_t do_reset);
void N51ICP_reentry(uint32_t delay1, uint32_t delay2, uint32_t delay3);

/**
 * @brief      ICP reentry glitching
 * 
 * @details    This function is for getting the configuration bytes to read at consistent times during an ICP reentry.
 *             Every time reset is set high, the configuration bytes are read, but the timing of the reset high is not consistent 
 *             unless an additional reset 1,0 is performed first. When this is done, the configuration bytes are consistently read at about 2us after the reset high.
 *             This is primarily for capturing the configuration byte load process.
 * 
 * @param[in]  delay1  Delay after reset is set to high
 * @param[in]  delay2  Delay after reset is set to low
 * @param[in]  delay_after_trigger_high  Delay after setting trigger pin high (for triggering a capture device), before setting reset high 
 * @param[in]  delay_before_trigger_low  Delay after setting reset high, before setting trigger pin low
*/
void N51ICP_reentry_glitch(uint32_t delay1, uint32_t delay2, uint32_t delay_after_trigger_high, uint32_t delay_before_trigger_low);
void N51ICP_deinit(void);
void N51ICP_exit_icp_mode(void);
uint32_t N51ICP_read_device_id(void);
uint32_t N51ICP_read_pid(void);
uint8_t N51ICP_read_cid(void);
void N51ICP_read_uid(uint8_t * buf);
void N51ICP_read_ucid(uint8_t * buf);
uint32_t N51ICP_read_flash(uint32_t addr, uint32_t len, uint8_t *data);
uint32_t N51ICP_write_flash(uint32_t addr, uint32_t len, uint8_t *data);
void N51ICP_mass_erase(void);
void N51ICP_page_erase(uint32_t addr);
void N51ICP_outputf(const char *fmt, ...);
void N51ICP_pgm_deinit_only(uint8_t leave_reset_high);

#ifdef __cplusplus
}
#endif
