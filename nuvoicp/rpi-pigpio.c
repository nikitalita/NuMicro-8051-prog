#ifdef RPI
#include <stdio.h>
#include <pigpio.h>

#include "pgm.h"

/* GPIO line numbers for RPi, must be changed for other SBCs */
#define GPIO_DAT 20
#define GPIO_RST 21
#define GPIO_CLK 26

#define GPIO_TRIGGER 16
#define MAX_BUSY_DELAY 300

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

// There's no "high-z" setting; this just turns them into inputs and sets the pull-up/down resistors to off, so it is effectively high-z
void pgm_release_non_reset_pins(void) {
    gpioSetMode(GPIO_DAT, PI_INPUT);
    gpioSetMode(GPIO_CLK, PI_INPUT);
    gpioSetMode(GPIO_TRIGGER, PI_INPUT);
    gpioSetPullUpDown(GPIO_DAT, PI_PUD_OFF);
    gpioSetPullUpDown(GPIO_CLK, PI_PUD_OFF);
    gpioSetPullUpDown(GPIO_TRIGGER, PI_PUD_OFF);
}

void pgm_release_rst(void) {
    gpioSetMode(GPIO_RST, PI_INPUT);
    gpioSetPullUpDown(GPIO_TRIGGER, PI_PUD_OFF);
}

void pgm_release_pins(void) {
    pgm_release_non_reset_pins();
    pgm_release_rst();
}

void pgm_set_trigger(unsigned char val)
{
    gpioWrite(GPIO_TRIGGER, val);
}

void pgm_deinit(unsigned char leave_reset_high)
{
    if (!leave_reset_high) {
        pgm_release_pins();
    } else {
        gpioWrite(GPIO_RST, 1);
        pgm_release_non_reset_pins();
    }
    pgm_release_non_reset_pins();
    gpioTerminate();
}

unsigned long pgm_usleep(unsigned long usec)
{   
    unsigned long waited = 0;
    if (usec == 0){
        return 0;
    }
    // because of the limitations of the gpioDelay function (>100us sleeps are real sleeps, which can sleep for 60+ additional us), we have to break this up
    if (usec > 101 && usec <= MAX_BUSY_DELAY) {
        for (; usec > 100; usec -= 100){
            waited += gpioDelay(99);
        }
    }
    if (usec > 0){
        // gpioDelay introduces a delay of 1us, so we subtract 1 from the delay
        waited += gpioDelay(usec-1);
    }
    return waited;
}

void pgm_print(const char *msg)
{
	fprintf(stderr, "%s", msg);
}


#endif // RPI