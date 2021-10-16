#include <Arduino.h>

/* Lolin(WeMOS) D1 mini */
/* 80MHz: 1 cycle = 12.5ns */
#define DAT   D1
#define CLK   D2
#define RST   D3

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
  pgm_set_rst(1);
}

void pgm_usleep(unsigned long usec)
{
  delayMicroseconds(usec);
}

} // extern "C"
