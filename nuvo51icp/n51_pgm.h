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
int N51PGM_init(void);

/**
 * Deinitializes pgm interface.
 * 
 * Sets DAT and CLK pins to high-z, and terminates GPIO mode.
 * NOTE: When implementing, make sure that this function is re-entrant!
 * @param leave_reset_high If 1, the RST pin will be left high. If 0, the RST pin will be set to high-z.
 */
void N51PGM_deinit(uint8_t leave_reset_high);

// Check if the PGM interface is initialized.
uint8_t N51PGM_is_init();

// Set the PGM data pin to the given value.
void N51PGM_set_dat(uint8_t val);

// Get the current value of the PGM data pin.
uint8_t N51PGM_get_dat(void);

// Set the PGM reset pin to the given value.
void N51PGM_set_rst(uint8_t val);

// Set the PGM clock pin to the given value.
void N51PGM_set_clk(uint8_t val);

// Sets the PGM trigger pin to the given value. (Optionally implemented, for fault injection purposes)
void N51PGM_set_trigger(uint8_t val);

// Sets the direction of the PGM data pin
void N51PGM_dat_dir(uint8_t state);

// Releases all PGM pins and sets them to high-z.
// The purpose for this is to avoid the pins being left in a high state
// and unable to be controlled by other programs/devices.
void N51PGM_release_pins(void);

// Releases the RST pin only
void N51PGM_release_rst(void);

// Device-specific sleep function
uint32_t N51PGM_usleep(uint32_t usec);

// Device-specific get time function, in microseconds
uint64_t N51PGM_get_time(void);

// Device-specific print function
void N51PGM_print(const char *msg);


#ifdef __cplusplus
}

#endif