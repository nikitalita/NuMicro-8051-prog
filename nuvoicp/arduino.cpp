#include <Arduino.h>

#include "pgm.h"
/* Lolin(WeMOS) D1 mini */
/* 80MHz: 1 cycle = 12.5ns */
#ifndef ARDUINO_AVR_MEGA2560
#define DAT   11
#define CLK   12
#define RST   13
#else
#define DAT   52
#define CLK   50
#define RST   48
#endif
extern "C" {

int pgm_init(void)
{
  pinMode(CLK, OUTPUT);
  pinMode(DAT, INPUT);
  pinMode(RST, OUTPUT);
  digitalWrite(CLK, LOW);

  return 0;
}

void pgm_set_dat(uint8_t val)
{
  digitalWrite(DAT, val);
}

uint8_t pgm_get_dat(void)
{
  return digitalRead(DAT);
}

void pgm_set_rst(uint8_t val)
{
  digitalWrite(RST, val);
}

void pgm_set_clk(uint8_t val)
{
  digitalWrite(CLK, val);
}

void pgm_dat_dir(uint8_t state)
{
  pinMode(DAT, state ? OUTPUT : INPUT);
}

void pgm_release_pins(void)
{
  pinMode(CLK, INPUT);
  pinMode(DAT, INPUT);
  pinMode(RST, INPUT);
}

void pgm_set_trigger(uint8_t val)
{
  /* not implemented */
}

void pgm_release_rst(void)
{
  pinMode(RST, INPUT);
}

void pgm_deinit(uint8_t leave_reset_high)
{
  pinMode(CLK, INPUT);
  pinMode(DAT, INPUT);
  if (leave_reset_high){
    pgm_set_rst(1);
  } else {
    pinMode(RST, INPUT);
  }
}


#ifdef _DEBUG
void pgm_debug_outputf(const char *s, ...)
{
  char buf[160];
  va_list ap;
  va_start(ap, s);
  vsnprintf(buf, 160, s, ap);
  pgm_print(buf);

  va_end(ap);
}

#define DEBUG_OUTPUTF(s, ...) pgm_debug_outputf(s, ##__VA_ARGS__)
#else
#define DEBUG_OUTPUTF(s, ...)
#endif
uint32_t pgm_usleep(uint32_t usec)
{
  if (usec < 1000) {
    delayMicroseconds(usec);
    // not printing for short delays to avoid potentially destructive overhead
  } else {
    uint32_t msec = usec / 1000;
    uint32_t lusec = usec % 1000;
    DEBUG_OUTPUTF("usleep(%u): ", usec);
    DEBUG_OUTPUTF("delaying %u ms, ", msec); 
    DEBUG_OUTPUTF("%u us\n", lusec);
    delay(msec);
    delayMicroseconds(lusec);
  }
  return usec;
}

uint64_t pgm_get_time(){
    return micros();
}

void pgm_print(const char * msg){
    Serial2.print(msg);
}

} // extern "C"
