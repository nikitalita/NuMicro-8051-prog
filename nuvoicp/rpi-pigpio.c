#ifdef RPI
#include <stdio.h>
#include <pigpio.h>

/* GPIO line numbers for RPi, must be changed for other SBCs */
#define GPIO_DAT 20
#define GPIO_RST 21
#define GPIO_CLK 26

int CMD_DELAY = 1;
int READ_DELAY = 1;

int pgm_init(void)
{
    if (gpioInitialise() < 0)
    {
        fprintf(stderr, "pigpio initialization failed\n");
        return -1;
    }

    int ret =  gpioSetMode(GPIO_DAT, PI_INPUT);
    ret |= gpioSetMode(GPIO_RST, PI_OUTPUT);
    ret |= gpioSetMode(GPIO_CLK, PI_OUTPUT);
    if (ret != 0)
    {
        fprintf(stderr, "Setting GPIO modes failed\n");
        return ret;
    }
    ret |= gpioWrite(GPIO_RST, 0);
    ret |= gpioWrite(GPIO_CLK, 0);
    if (ret != 0)
    {
        fprintf(stderr, "Setting GPIO values failed\n");
        return ret;
    }
    return 0;
}

void pgm_set_dat(int val)
{
    gpioWrite(GPIO_DAT, val);
}

int pgm_get_dat(void)
{
    return gpioRead(GPIO_DAT);
}

void pgm_set_rst(int val)
{
    gpioWrite(GPIO_RST, val);
}

void pgm_set_clk(int val)
{
    gpioWrite(GPIO_CLK, val);
}

void pgm_dat_dir(int state)
{
    if (gpioSetMode(GPIO_DAT, state ? PI_OUTPUT : PI_INPUT) < 0){
        fprintf(stderr, "Setting data directions failed\n");
    }
}

void pgm_deinit(void)
{
    gpioWrite(GPIO_RST, 1);
    gpioTerminate();
}

void pgm_usleep(unsigned long usec)
{
    if (usec > 0)
        gpioDelay(usec-1);
}

void device_print(const char *msg)
{
	fprintf(stderr, msg);
}

#endif