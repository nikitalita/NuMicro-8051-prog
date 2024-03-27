
#include "n51_pgm.h"
#include "n51_icp.h"

#include <stdio.h>
#ifndef ARDUINO


void test_sleep() {
	N51PGM_init();
	N51PGM_set_trigger(0);
	N51PGM_set_trigger(1);
	uint32_t waited = N51PGM_usleep(300);
	N51PGM_set_trigger(0);
	printf("waited: %d\n", waited);
	N51PGM_deinit(0);
}

void test(){
	printf("testing clock...\n");
	N51PGM_init();
	// gpioDelay(5);
	// N51PGM_set_clk(1);
	// uint32_t result = gpioDelay(200);
	// N51PGM_set_clk(0);
	N51PGM_deinit(0);
	printf("done\n");
	// printf("result: %d\n", result);
}
void test_trigger(){
	N51PGM_init();
	while(1){
		N51PGM_set_trigger(0);
		N51PGM_set_trigger(1);
	}
}



void test_bitsend(uint32_t data, int len, int udelay){
	int i = len;
	N51PGM_dat_dir(1);
	while (i--) {
		N51PGM_set_dat((data >> i) & 1);
		N51PGM_usleep(udelay);
		N51PGM_set_clk(1);
		N51PGM_usleep(udelay);
		N51PGM_set_clk(0);
	}
}

void test_send_command(uint8_t cmd, uint32_t dat)
{
	test_bitsend((dat << 6) | cmd, 24, 1);
}
#define ICP_CMD_MASS_ERASE		0x26

void test_serase(){
	printf("Expected:\n");

	N51PGM_init();
	test_send_command(ICP_CMD_MASS_ERASE, 0x3A5A5);
	test_bitsend(0xff, 8, 1);
	printf("\nActuyal:\n");
	N51ICP_mass_erase();
	printf("\n");
}

void test_speed(){
	N51PGM_init();
	while(1){
		N51PGM_set_trigger(1);
		N51PGM_set_trigger(0);
	}
	N51PGM_deinit(0);
}
int main() {
	printf("testing...");
	// test_serase();
	test_speed();
	return 0;
}
#endif