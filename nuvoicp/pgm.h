// Description: Header file for the PGM interface.
#pragma once


#ifdef __cplusplus
#pragma message "HALDO!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
extern "C" {

#endif

// Initialize the PGM interface.
int pgm_init(void);

/**
 * Deinitializes pgm interface.
 * 
 * Sets RST to high and sets DAT and CLK pins to INPUT mode, and terminates GPIO mode.
 * To allow RST to be set by other devices (or an onboard RST button), call pgm_release_pins() or pgm_release_rst().
 */
void pgm_deinit(void);

// Set the PGM data pin to the given value.
void pgm_set_dat(unsigned char val);

// Get the current value of the PGM data pin.
unsigned char pgm_get_dat(void);

// Set the PGM reset pin to the given value.
void pgm_set_rst(unsigned char val);

// Set the PGM clock pin to the given value.
void pgm_set_clk(unsigned char val);

// Sets the PGM trigger pin to the given value.
void pgm_set_trigger(unsigned char val);

// Sets the direction of the PGM data pin
void pgm_dat_dir(unsigned char state);

// Releases all PGM pins by setting them to INPUT mode.
// The purpose for this is to avoid the pins being left in a high state
// and unable to be controlled by other programs/devices.
void pgm_release_pins(void);

// Releases the RST pin only
void pgm_release_rst(void);


/**
 * Sets the delay between each bit of the CMD sequence sent to the device.
 * Only functional on RasPi; NOP on other targets
 * 
 * @param delay_us Delay in microseconds
*/
void pgm_set_cmd_bit_delay(int delay_us);
/**
 * Sets the delay between each bit read from the device during `icp_read_byte()`
 * Only functional on RasPi; NOP on other targets
 * 
 * @param delay_us Delay in microseconds
*/
void pgm_set_read_bit_delay(int delay_us);
/**
 * Sets the delay between each bit written to the device during `icp_write_byte()`
 * Only functional on RasPi; NOP on other targets
 * 
 * @param delay_us Delay in microseconds
*/
void pgm_set_write_bit_delay(int delay_us);

/**
 * Gets the delay between each bit written to the device during `icp_write_byte()`
 * 
 * @return Delay in microseconds
*/
int pgm_get_cmd_bit_delay();

/**
 * Gets the delay between each bit read from the device during `icp_read_byte()`
 * 
 * @return Delay in microseconds
*/
int pgm_get_read_bit_delay();

/**
 * Gets the delay between each bit of the CMD sequence sent to the device.
 * 
 * @return Delay in microseconds
*/
int pgm_get_write_bit_delay();

// Device-specific sleep function
void pgm_usleep(unsigned long usec);

// Device-specific print function
void pgm_print(const char *msg);

// This is only used by the raspi; for microcontrollers, this isn't enabled as the delays are determined by the clock speed.
#ifndef DYNAMIC_DELAY
extern int CMD_SEND_BIT_DELAY;
extern int READ_BIT_DELAY;
extern int WRITE_BIT_DELAY;
#else
#define CMD_SEND_BIT_DELAY pgm_get_cmd_bit_delay()
#define READ_BIT_DELAY pgm_get_read_bit_delay()
#define WRITE_BIT_DELAY pgm_get_write_bit_delay()
#endif

#ifdef __cplusplus
}

#endif