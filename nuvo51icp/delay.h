#pragma once


#ifndef USER_DEFINED_DEFAULT_DELAY

#ifdef RPI // Raspberry Pi

#ifdef USE_PIGPIO // pigpio
#define DEFAULT_BIT_DELAY 2
#else // gpiod
#define DEFAULT_BIT_DELAY 1
#endif // USE_PIGPIO
#else // Arduino
#ifdef F_CPU
#if F_CPU <= 16000000L // 16MHz
#define DEFAULT_BIT_DELAY 0
#else  // Other, faster Arduinos
#define DEFAULT_BIT_DELAY 1
#endif // F_CPU <= 16000000L
#else  // F_CPU undefined
// unknown target, just set to 2
#define DEFAULT_BIT_DELAY 2
#endif // F_CPU

#endif // RPI
#endif // USER_DEFINED_DEFAULT_DELAY