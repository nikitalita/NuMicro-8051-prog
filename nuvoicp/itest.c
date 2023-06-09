#ifdef RPI
#include "pgm.h"
#include <pigpio.h>
#include <stdio.h>
#include <pigpio.h>

void test_clk(){
	for (int i = 0; i < 1000; i++){
		pgm_set_clk(0);
		gpioDelay(200);
		pgm_set_clk(1);
		gpioDelay(200);
	}
}
void test_sleep() {
	pgm_init();
	pgm_set_trigger(0);
	pgm_set_trigger(1);
	uint32_t waited = pgm_usleep(300);
	pgm_set_trigger(0);
	printf("waited: %d\n", waited);
	pgm_deinit(0);
}

void test(){
	printf("testing clock...\n");
	pgm_init();
	gpioDelay(100000);
	test_clk();
	// gpioDelay(5);
	// pgm_set_clk(1);
	// uint32_t result = gpioDelay(200);
	// pgm_set_clk(0);
	pgm_deinit(0);
	printf("done\n");
	// printf("result: %d\n", result);
}


void test_trigger(){
	pgm_init();
	while(1){
		pgm_set_trigger(0);
		pgm_set_trigger(1);
	}
}

int main() {
	test_trigger();
	return 0;
}
#endif