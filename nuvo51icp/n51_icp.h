/*
 * nuvo51icp, an ICP flasher for the Nuvoton NuMicro 8051 line of chips
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

#ifdef __cplusplus
extern "C" {
#endif

/***
 * @brief     Initializes the PGM interface.
 * @param[in] do_reset If set, the reset sequence will be sent when performing ICP entry (recommended to set this to 1).
 * @return    0 on success, any other value on failure
*/
int N51ICP_init();

/**
 * @brief      Deinitializes the PGM interface.
 * 
 * @param[in] leave_reset_high  If set, the reset pin will not be released and will be left high after deinitializing the PGM interface.
*/
void N51ICP_deinit(uint8_t leave_reset_high);

/**
 * Read Device ID (i.e. the chip identifier)
*/
uint32_t N51ICP_read_device_id(void);
/**
 * Read Product ID
*/
uint32_t N51ICP_read_pid(void);
/**
 * Read Customer ID
*/
uint8_t N51ICP_read_cid(void);
/**
 * Read User ID
*/
void N51ICP_read_uid(uint8_t * buf);
/**
 * Read User Configuration ID
*/
void N51ICP_read_ucid(uint8_t * buf);
/**
 * Read Flash
*/
uint32_t N51ICP_read_flash(uint32_t addr, uint32_t len, uint8_t *data);
/**
 * Write Flash
*/
uint32_t N51ICP_write_flash(uint32_t addr, uint32_t len, uint8_t *data);
/**
 * Mass Erase
*/
void N51ICP_mass_erase(void);
/**
 * Page Erase
*/
void N51ICP_page_erase(uint32_t addr);
/**
 * @brief      Output formatted string to the console, using the host device's implementation of print.
 * 
 * @param[in]  fmt   The format string
 * @param[in]  ...   The arguments to be formatted
*/
void N51ICP_outputf(const char *fmt, ...);

/***
 * @brief     Set the program time for the N76E003.
 * 
 * @param delay_us The time to wait while programming (default: 25us)
 * @param hold_us The time to wait after programming (default: 5us)
 */
void N51ICP_set_program_time(uint32_t delay_us, uint32_t hold_us);

/***
 * @brief     Set the page erase time for the N76E003.
 * 
 * @param delay_us The time to wait while erasing (default: 6000us)
 * @param hold_us The time to wait after erasing (default: 100us)
*/
void N51ICP_set_page_erase_time(uint32_t delay_us, uint32_t hold_us);

/***
 * @brief     Set the mass erase time for the N76E003.
 * 
 * @param delay_us The time to wait while erasing (default: 65000us)
 * @param hold_us The time to wait after erasing (default: 1000us)

*/
void N51ICP_set_mass_erase_time(uint32_t delay_us, uint32_t hold_us);

/**
 * @brief      Puts the target chip into ICP mode.
 * 
 * @param do_reset If set, the reset sequence will be sent when performing ICP entry (recommended to set this to 1).
 * @return         The detected device ID
*/
uint32_t N51ICP_enter_icp_mode(uint8_t do_reset);

/**
 * @brief      Takes the target chip out of ICP mode.
*/
void N51ICP_exit_icp_mode(void);

/**
 * @brief      Re-enters the target chip into ICP mode.
 * 
 * @param delay1  Delay after reset is set to high (Recommended: 5000)
 * @param delay2  Delay after reset is set to low (Recommended: 1000)
 * @param delay3  Delay after the entry bits are sent on the data line (Recommended: 10)
*/
void N51ICP_reentry(uint32_t delay1, uint32_t delay2, uint32_t delay3);

/**
 * Sends the ICP entry bits on the DAT line to the target chip.
*/
void N51ICP_send_entry_bits();
/**
 * Sends the ICP exit bits on the DAT line to the target chip.
*/
void N51ICP_send_exit_bits();

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

#ifdef __cplusplus
}
#endif
