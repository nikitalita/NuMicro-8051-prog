
#include "pgm.h"
#include "icp.h"

#include <stdio.h>
#ifndef ARDUINO

static void static_test_delay(){
	printf("static delay before set: %d\n", icp_get_cmd_bit_delay());
	icp_set_cmd_bit_delay(20);
	printf("static delay after set: %d\n", icp_get_cmd_bit_delay());
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
	// gpioDelay(5);
	// pgm_set_clk(1);
	// uint32_t result = gpioDelay(200);
	// pgm_set_clk(0);
	pgm_deinit(0);
	printf("done\n");
	// printf("result: %d\n", result);
}

void test_delay_get(){
	printf("delay before set: %d\n", icp_get_cmd_bit_delay());
	icp_set_cmd_bit_delay(4);
	printf("delay after set: %d\n", icp_get_cmd_bit_delay());
}
void test_trigger(){
	pgm_init();
	while(1){
		pgm_set_trigger(0);
		pgm_set_trigger(1);
	}
}



void test_bitsend(uint32_t data, int len, int udelay){
	int i = len;
	pgm_dat_dir(1);
	while (i--) {
		pgm_set_dat((data >> i) & 1);
		pgm_usleep(udelay);
		pgm_set_clk(1);
		pgm_usleep(udelay);
		pgm_set_clk(0);
	}
}

void test_send_command(uint8_t cmd, uint32_t dat)
{
	test_bitsend((dat << 6) | cmd, 24, 1);
}

void test_serase(){
	printf("Expected:\n");

	pgm_init();
	test_send_command(CMD_MASS_ERASE, 0x3A5A5);
	test_bitsend(0xff, 8, 1);
	printf("\nActuyal:\n");
	icp_mass_erase();
	printf("\n");
}
int main() {
	printf("testing...");
	test_serase();
	return 0;
}
#endif