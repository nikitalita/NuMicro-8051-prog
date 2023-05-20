#include <Arduino.h>

/* Lolin(WeMOS) D1 mini */
/* 80MHz: 1 cycle = 12.5ns */
#ifndef ARDUINO_AVR_MEGA2560
#define DAT   11
#define CLK   12
#define RST   13
extern int CMD_DELAY = 1
extern int READ_DELAY = 1
#else
#define DAT   52
#define CLK   50
#define RST   48
extern int CMD_DELAY = 0
extern int READ_DELAY = 0
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

void pgm_set_dat(int val)
{
  digitalWrite(DAT, val);
}

int pgm_get_dat(void)
{
  return digitalRead(DAT);
}

void pgm_set_rst(int val)
{
  digitalWrite(RST, val);
}

void pgm_set_clk(int val)
{
  digitalWrite(CLK, val);
}

void pgm_dat_dir(int state)
{
  pinMode(DAT, state ? OUTPUT : INPUT);
}

void pgm_deinit(void)
{
  /* release reset */
  pinMode(CLK, INPUT);
  pinMode(DAT, INPUT);
  pgm_set_rst(1);
  pinMode(RST, INPUT);
}

void pgm_usleep(unsigned long usec)
{
  delayMicroseconds(usec);
}

void device_print(const char * msg){
  if (Serial1.available())
    Serial1.print(msg);
}

} // extern "C"
