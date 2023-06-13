#pragma once
#include <stdint.h>
typedef struct _config_flags {
	// config0
	uint8_t unk0_0:1;      // 0:0
	uint8_t LOCK:1;        // 0:1   | lock                            -- 1: unlocked, 0: locked
	uint8_t RPD:1;         // 0:2   | Reset pin enable                -- 1: reset function of P2.0/Nrst pin enabled, 0: disabled, P2.0/Nrst only functions as input-only pin P2.0
	uint8_t unk0_3:1;      // 0:3
	uint8_t OCDEN:1;       // 0:4   | OCD enable                      -- 1: OCD Disabled, 0: OCD Enabled
	uint8_t OCDPWM:1;      // 0:5   | PWM output state under OCD halt -- 1: tri-state pins are used as PWM outputs, 0: PWM continues
	uint8_t reserved0_6:1; // 0:6
	uint8_t CBS:1;         // 0:7   | CONFIG boot select              -- 1: MCU will reboot from APROM after resets except software reset, 0: MCU will reboot from LDROM after resets except software reset
	// config1
	/** 1:3-0 | LDROM size select 
	  111 - No LDROM, APROM is 18k.
	  110 = LDROM is 1K Bytes. APROM is 17K Bytes.
	  101 = LDROM is 2K Bytes. APROM is 16K Bytes. 
	  100 = LDROM is 3K Bytes. APROM is 15K Bytes. 
	  0xx = LDROM is 4K Bytes. APROM is 14K Bytes
	*/
	uint8_t LDS:3;
	uint8_t unk1_3:5;      // 1:5-3
	// config2
	uint8_t unk2_0:2;      // 2:1-0
	uint8_t CBORST:1;      // 2:2   | CONFIG brown-out reset enable   -- 1 = Brown-out reset Enabled, 0 = Brown-out reset Disabled.
	uint8_t BOIAP:1;       // 2:3   | Brown-out inhibiting IAP        -- 1 = IAP erasing or programming is inhibited if VDD is lower than VBOD, 0 = IAP erasing or programming is allowed under any workable VDD.
	uint8_t CBOV:2;        // 2:5-4 | CONFIG brown-out voltage select -- 11 = VBOD is 2.2V; 10 = VBOD is 2.7V; 01 = VBOD is 3.7V; 00 = VBOD is 4.4V.
	uint8_t unk2_6:1;      // 2:6
	uint8_t CBODEN:1;      // 2:7   | CONFIG brown-out detect enable  -- 1 = Brown-out detection circuit on; 0 = Brown-out detection circuit off.
	// config3 - no flags
	uint8_t unk3;       // 3
	// config4
	uint8_t unk4_0:4;   // 4:0-3
	/**
	 * 4:4-7 | WDT enable 
	 * 	1111 = WDT is Disabled. WDT can be used as a general purpose timer via software control
	 *  0101 = WDT is Enabled as a time-out reset timer and it stops running during Idle or Power-down mode.
	 *  Others = WDT is Enabled as a time-out reset timer and it keeps running during Idle or Power-down mode.
	 */
	uint8_t WDTEN:4;    
} config_flags;