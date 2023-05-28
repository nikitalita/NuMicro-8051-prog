#ifdef RPI
#include <stdio.h>
#include <pigpio.h>

#include "pgm.h"

/* GPIO line numbers for RPi, must be changed for other SBCs */
#define GPIO_DAT 20
#define GPIO_RST 21
#define GPIO_CLK 26

#define GPIO_TRIGGER 16

#ifndef DYNAMIC_DELAY
int CMD_SEND_BIT_DELAY = 1;
int READ_BIT_DELAY = 2;
int WRITE_BIT_DELAY = 2;
#else
static int cmd_bit_delay_val = 1;
static int read_bit_delay_val = 2;
static int write_bit_delay_val = 2;
#endif

int pgm_init(void)
{
    if (gpioInitialise() < 0)
    {
        pgm_print("pigpio initialization failed\n");
        return -1;
    }

    int ret = gpioSetMode(GPIO_DAT, PI_INPUT);
    ret |= gpioSetMode(GPIO_CLK, PI_OUTPUT);
    ret |= gpioSetMode(GPIO_TRIGGER, PI_OUTPUT);
    ret |= gpioSetMode(GPIO_RST, PI_OUTPUT);
    if (ret != 0)
    {
        pgm_print("Setting GPIO modes failed\n");
        return ret;
    }
    ret |= gpioWrite(GPIO_RST, 0);
    ret |= gpioWrite(GPIO_TRIGGER, 0);
    ret |= gpioWrite(GPIO_CLK, 0);
    if (ret != 0)
    {
        pgm_print("Setting GPIO values failed\n");
        return ret;
    }
    return 0;
}

void pgm_set_dat(unsigned char val)
{
    gpioWrite(GPIO_DAT, val);
}

unsigned char pgm_get_dat(void)
{
    return gpioRead(GPIO_DAT);
}

void pgm_set_rst(unsigned char val)
{
    gpioWrite(GPIO_RST, val);
}

void pgm_set_clk(unsigned char val)
{
    gpioWrite(GPIO_CLK, val);
}

void pgm_dat_dir(unsigned char state)
{
    if (gpioSetMode(GPIO_DAT, state ? PI_OUTPUT : PI_INPUT) < 0){
        pgm_print("Setting data directions failed\n");
    }
}

void pgm_release_pins(void){
    gpioSetMode(GPIO_DAT, PI_INPUT);
    gpioSetMode(GPIO_RST, PI_INPUT);
    gpioSetMode(GPIO_CLK, PI_INPUT);
    gpioSetMode(GPIO_TRIGGER, PI_INPUT);
}

void pgm_release_rst(void) {
    gpioSetMode(GPIO_RST, PI_INPUT);
}

void pgm_set_trigger(unsigned char val)
{
    gpioWrite(GPIO_TRIGGER, val);
}

void pgm_deinit(void)
{
    gpioWrite(GPIO_RST, 1);
    pgm_release_pins();
    gpioTerminate();
}

#ifdef DYNAMIC_DELAY
void pgm_set_cmd_bit_delay(int delay_us) {
    cmd_bit_delay_val = delay_us;
}
void pgm_set_read_bit_delay(int delay_us) {
    read_bit_delay_val = delay_us;
}
void pgm_set_write_bit_delay(int delay_us) {
    write_bit_delay_val = delay_us;
}
int pgm_get_cmd_bit_delay(){
    return cmd_bit_delay_val;
}
int pgm_get_read_bit_delay(){
    return read_bit_delay_val;
}
int pgm_get_write_bit_delay(){
    return write_bit_delay_val;
}
#else
void pgm_set_cmd_bit_delay(int delay_us){}
void pgm_set_read_bit_delay(int delay_us){}
void pgm_set_write_bit_delay(int delay_us){}
int pgm_get_cmd_bit_delay(){
    return CMD_SEND_BIT_DELAY;
}
int pgm_get_read_bit_delay(){
    return READ_BIT_DELAY;
}
int pgm_get_write_bit_delay(){
    return WRITE_BIT_DELAY;
}
#endif

void pgm_usleep(unsigned long usec)
{
    if (usec > 0)
        gpioDelay(usec-1);
}

void pgm_print(const char *msg)
{
	fprintf(stderr, msg);
}



#endif