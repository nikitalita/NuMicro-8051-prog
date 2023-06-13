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

void pgm_set_dat(unsigned char val)
{
  digitalWrite(DAT, val);
}

unsigned char pgm_get_dat(void)
{
  return digitalRead(DAT);
}

void pgm_set_rst(unsigned char val)
{
  digitalWrite(RST, val);
}

void pgm_set_clk(unsigned char val)
{
  digitalWrite(CLK, val);
}

void pgm_dat_dir(unsigned char state)
{
  pinMode(DAT, state ? OUTPUT : INPUT);
}

void pgm_release_pins(void)
{
  pinMode(CLK, INPUT);
  pinMode(DAT, INPUT);
  pinMode(RST, INPUT);
}

void pgm_set_trigger(unsigned char val)
{
  /* not implemented */
}

void pgm_release_rst(void)
{
  pinMode(RST, INPUT);
}

void pgm_deinit(unsigned char leave_reset_high)
{
  pinMode(CLK, INPUT);
  pinMode(DAT, INPUT);
  if (leave_reset_high){
    pgm_set_rst(1);
  } else {
    pinMode(RST, INPUT);
  }
}


unsigned long pgm_usleep(unsigned long usec)
{
  delayMicroseconds(usec);
  return usec;
}

void pgm_print(const char * msg){
  if (Serial1.available())
    Serial1.print(msg);
}

} // extern "C"
