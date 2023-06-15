// Description: Header file for the PGM interface.
#pragma once


#include <stdint.h>

#ifdef __cplusplus
extern "C" {

#endif

/**
 * Initialize the PGM interface.
 * 
 * Sets the CLK and RST pins to output mode, sets DAT to Input mode, and sets the RST pin to low.
 * 
 * @return 0 on success, <0 on failure.
 */
int pgm_init(void);

/**
 * Deinitializes pgm interface.
 * 
 * Sets DAT and CLK pins to high-z, and terminates GPIO mode.
 * @param leave_reset_high If 1, the RST pin will be left high. If 0, the RST pin will be set to high-z.
 */
void pgm_deinit(uint8_t leave_reset_high);

// Set the PGM data pin to the given value.
void pgm_set_dat(uint8_t val);

// Get the current value of the PGM data pin.
uint8_t pgm_get_dat(void);

// Set the PGM reset pin to the given value.
void pgm_set_rst(uint8_t val);

// Set the PGM clock pin to the given value.
void pgm_set_clk(uint8_t val);

// Sets the PGM trigger pin to the given value. (Optionally implemented, for fault injection purposes)
void pgm_set_trigger(uint8_t val);

// Sets the direction of the PGM data pin
void pgm_dat_dir(uint8_t state);

// Releases all PGM pins and sets them to high-z.
// The purpose for this is to avoid the pins being left in a high state
// and unable to be controlled by other programs/devices.
void pgm_release_pins(void);

// Releases the RST pin only
void pgm_release_rst(void);

// Device-specific sleep function
uint32_t pgm_usleep(uint32_t usec);

// Device-specific get time function, in microseconds
uint64_t pgm_get_time(void);

// Device-specific print function
void pgm_print(const char *msg);


#ifdef __cplusplus
}

#endif