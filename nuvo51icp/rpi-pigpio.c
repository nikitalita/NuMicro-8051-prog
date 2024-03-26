#ifdef RPI
#include <stdio.h>
#include <pigpio.h>

#include "n51_pgm.h"

#ifdef DEBUG
#include "print_caps.h"
#endif

/* GPIO line numbers for RPi, must be changed for other SBCs */
#define GPIO_DAT 20
#define GPIO_RST 21
#define GPIO_CLK 26

#define GPIO_TRIGGER 16
#define MAX_BUSY_DELAY 300

uint8_t is_initialized = 0;

int N51PGM_init(void)
{
    #ifdef DEBUG
    print_caps();
    #endif

    if (gpioInitialise() < 0)
    {
        N51PGM_print("pigpio initialization failed\n");
        return -1;
    }
    is_initialized = 1;
    int ret = gpioSetMode(GPIO_DAT, PI_INPUT);
    ret |= gpioSetMode(GPIO_CLK, PI_OUTPUT);
    ret |= gpioSetMode(GPIO_TRIGGER, PI_OUTPUT);
    ret |= gpioSetMode(GPIO_RST, PI_OUTPUT);
    if (ret != 0)
    {
        N51PGM_print("Setting GPIO modes failed\n");
        return ret;
    }
    ret |= gpioWrite(GPIO_RST, 0);
    ret |= gpioWrite(GPIO_TRIGGER, 0);
    ret |= gpioWrite(GPIO_CLK, 0);
    if (ret != 0)
    {
        N51PGM_print("Setting GPIO values failed\n");
        return ret;
    }
    return 0;
}

uint8_t N51PGM_is_init()
{
    return is_initialized;
}

void N51PGM_set_dat(uint8_t val)
{
    gpioWrite(GPIO_DAT, val);
}

uint8_t N51PGM_get_dat(void)
{
    return gpioRead(GPIO_DAT);
}

void N51PGM_set_rst(uint8_t val)
{
    gpioWrite(GPIO_RST, val);
}

void N51PGM_set_clk(uint8_t val)
{
    gpioWrite(GPIO_CLK, val);
}

void N51PGM_dat_dir(uint8_t state)
{
    if (gpioSetMode(GPIO_DAT, state ? PI_OUTPUT : PI_INPUT) < 0){
        N51PGM_print("Setting data directions failed\n");
    }
}

// There's no "high-z" setting; this just turns them into inputs and sets the pull-up/down resistors to off, so it is effectively high-z
void N51PGM_release_non_reset_pins(void) {
    gpioSetMode(GPIO_DAT, PI_INPUT);
    gpioSetMode(GPIO_CLK, PI_INPUT);
    gpioSetMode(GPIO_TRIGGER, PI_INPUT);
    gpioSetPullUpDown(GPIO_DAT, PI_PUD_OFF);
    gpioSetPullUpDown(GPIO_CLK, PI_PUD_OFF);
    gpioSetPullUpDown(GPIO_TRIGGER, PI_PUD_OFF);
}

void N51PGM_release_rst(void) {
    gpioSetMode(GPIO_RST, PI_INPUT);
    gpioSetPullUpDown(GPIO_TRIGGER, PI_PUD_OFF);
}

void N51PGM_release_pins(void) {
    N51PGM_release_non_reset_pins();
    N51PGM_release_rst();
}

void N51PGM_set_trigger(uint8_t val)
{
    gpioWrite(GPIO_TRIGGER, val);
}

void N51PGM_deinit(uint8_t leave_reset_high)
{
    if (!is_initialized){
        return;
    }
    if (!leave_reset_high) {
        N51PGM_release_pins();
    } else {
        gpioWrite(GPIO_RST, 1);
        N51PGM_release_non_reset_pins();
    }
    N51PGM_release_non_reset_pins();
    gpioTerminate();
    is_initialized = 0;
}

uint32_t N51PGM_usleep(uint32_t usec)
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

uint64_t N51PGM_get_time(){
    return gpioTick();
}

void N51PGM_print(const char *msg)
{
	fprintf(stderr, "%s", msg);
}


#endif // RPI