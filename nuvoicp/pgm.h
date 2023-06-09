// Description: Header file for the PGM interface.
#pragma once


#ifdef __cplusplus
extern "C" {

#endif

// Initialize the PGM interface.
int pgm_init(void);

/**
 * Deinitializes pgm interface.
 * 
 * Sets RST to high and sets DAT and CLK pins to high-z, and terminates GPIO mode.
 * To allow RST to be set by other devices (or an onboard RST button), call pgm_release_pins() or pgm_release_rst().
 */
void pgm_deinit(unsigned char leave_reset_high);

// Set the PGM data pin to the given value.
void pgm_set_dat(unsigned char val);

// Get the current value of the PGM data pin.
unsigned char pgm_get_dat(void);

// Set the PGM reset pin to the given value.
void pgm_set_rst(unsigned char val);

// Set the PGM clock pin to the given value.
void pgm_set_clk(unsigned char val);

// Sets the PGM trigger pin to the given value. (Optionally implemented, for glitching purposes)
void pgm_set_trigger(unsigned char val);

// Sets the direction of the PGM data pin
void pgm_dat_dir(unsigned char state);

// Releases all PGM pins and sets them to high-z.
// The purpose for this is to avoid the pins being left in a high state
// and unable to be controlled by other programs/devices.
void pgm_release_pins(void);

// Releases the RST pin only
void pgm_release_rst(void);

// Device-specific sleep function
unsigned long pgm_usleep(unsigned long usec);

// Device-specific print function
void pgm_print(const char *msg);


#ifdef __cplusplus
}

#endif