/*---------------------------------------------------------------------------------------------------------*/
/*                                                                                                         */
/* SPDX-License-Identifier: Apache-2.0                                                                     */
/* Copyright(c) 2023 Nuvoton Technology Corp. All rights reserved.                                         */
/* Copyright(c) 2023-2024 Nikita Lita. Some rights reserved.                                               */
/*                                                                                                         */
/*---------------------------------------------------------------------------------------------------------*/

#include <stdio.h>
#include <string.h>
#include <stdint.h>

#include "isp_uart0.h"
#include "isp_common.h"

#include "numicro_8051.h"
#define P03_PushPull_Mode P03_PUSHPULL_MODE
#define P12_PushPull_Mode P12_PUSHPULL_MODE
#define P05_PushPull_Mode P05_PUSHPULL_MODE
#define P03_Quasi_Mode P03_QUASI_MODE
#define P05_Quasi_Mode P05_QUASI_MODE
#define P12_Quasi_Mode P12_QUASI_MODE
#define P06_Quasi_Mode P06_QUASI_MODE
#define P07_Quasi_Mode P07_QUASI_MODE

// bootloader-specific constants
#define FW_VERSION 0xD0 // Supports extended commands
#define APROM_SIZE 16 * 1024
#define LDROM_SIZE 2 * 1024
#define APROM_PAGE_COUNT APROM_SIZE / PAGE_SIZE
#define LDROM_ADDRESS APROM_SIZE
#define PAGE_MASK 0xFF80

#define DISCONNECTED_STATE  0
#define CONNECTING_STATE    1
#define COMMAND_STATE       2
#define UPDATING_STATE      3
#define DUMPING_STATE       4

// How long to wait for an ISP connection before booting into APROM
#define Timer0Out_Counter 200 // About 1 second

__bit BIT_TMP;
volatile uint8_t __xdata uart_rcvbuf[64];
volatile uint8_t __xdata uart_txbuf[64];
volatile uint8_t __data bufhead;
volatile uint16_t __data current_address;
volatile uint16_t __data AP_size;
volatile uint8_t __data g_timer1Counter;
volatile uint8_t __data count;
volatile uint16_t __data g_timer0Counter;
volatile uint16_t __data g_checksum; // spec doesn't specify length of checksum, but ISP tools check for a 16-bit number
volatile uint16_t __data g_totalchecksum; // spec doesn't specify length of checksum, but ISP tools check for a 16-bit number
volatile uint8_t __data g_packNo[2] = {0,0};
volatile __bit bUartDataReady;
volatile __bit g_timer0Over;
volatile __bit g_timer1Over;
volatile uint8_t g_state = COMMAND_STATE;

#define UCID_LENGTH 0x30
#define UID_LENGTH 12

unsigned char CID;
unsigned char CONF[5];
unsigned char DPID[4];
unsigned char hircmap[2];

#define set_IAPGO_NO_EA TA=0xAA;TA=0x55;IAPTRG|=SET_BIT0;
#ifdef isp_with_wdt
// set_WDCLR without disabling interrupts
#define set_WDCLR_NO_EA TA=0xAA;TA=0x55;WDCON|=SET_BIT6;
#define set_IAPGO_WDCLR \
  BIT_TMP = EA;         \
  EA = 0;               \
  set_WDCLR_NO_EA;      \
  TA = 0xAA;            \
  TA = 0x55;            \
  IAPTRG |= SET_BIT0;   \
  EA = BIT_TMP
#define set_IAPGO_WDCLR_NO_EA \
  set_IAPGO_NO_EA;            \
  set_WDCLR_NO_EA;     

#define ISP_SET_IAPGO set_IAPGO_WDCLR_NO_EA
#else
// NOTE: This is being done for code-size optimization; currently there are no cases where we need to set IAPGO when interrupts are enabled
// This means that interrupts MUST be disabled before calling ISP_SET_IAPGO
#define ISP_SET_IAPGO set_IAPGO_NO_EA
#endif

// More code-size optimization
// We always use SFR page 0, so no need to switch pages
// NOTE: if any other SFR settings are added, please ensure that they do not need page 1,
// or if so, modify these things accordingly.
// You can tell if they do if the macros have the form `set_SFRS_SFRPAGE;foo&=0x01`
#define clr_BRCK_NO_PG_CLR T3CON&=0xDF
#define set_PSH_NO_PG_CLR  IPH|=0x10


void UART0_ini_115200(void)
{
  P06_Quasi_Mode;
  P07_Quasi_Mode;

  SCON = 0x52;  // UART0 Mode1,REN=1,TI=1
  TMOD |= 0x20; // Timer1 Mode1

  set_SMOD; // UART0 Double Rate Enable
  set_T1M;
  clr_BRCK_NO_PG_CLR; // Serial port 0 baud rate clock source = Timer1

  TH1 = (unsigned char)(256 - (1037500 / 115200)); /* ISP Rom is always 16.6 MHz */
  set_TR1;
  ES = 1;
  EA = 1;
}

void BYTE_READ_FUNC(uint8_t cmd, uint8_t start, uint8_t len, uint8_t *buf)
{
  uint8_t i;
  IAPCN = cmd;
  IAPAH = 0x00;
  IAPAL = start;
  for (i = 0; i < len - 1; i++)
  {
    ISP_SET_IAPGO;
    buf[i] = IAPFD;
    IAPAL++;
  }
  // get the last one
  ISP_SET_IAPGO;
  buf[i] = IAPFD;
}

void READ_HIRCMAP(void){
  BYTE_READ_FUNC(READ_UID, 0x30, 2, hircmap);
}

void SET_HIRCMAP(void){
  TA = 0XAA;
  TA = 0X55;
  RCTRIM0 = hircmap[0];
  TA = 0XAA;
  TA = 0X55;
  RCTRIM1 = hircmap[1];
}

void MODIFY_HIRC_16588(void)
{
  READ_HIRCMAP();
  // trimvalue16bit = ((hircmap[0] << 1) + (hircmap[1] & 0x01));
  // trimvalue16bit = trimvalue16bit - 14;
  // hircmap[1] = trimvalue16bit & 0x01;
  // hircmap[0] = trimvalue16bit >> 1;
  // -7 (111) on the high bits is the same as doing -14 (1110) on the whole number
  hircmap[0] -= 7;
  SET_HIRCMAP();
  /* Clear power on flag */
  PCON &= CLR_BIT4;
}

void MODIFY_HIRC_16(void)
{
  READ_HIRCMAP();
  SET_HIRCMAP();
}
#define READ_DEVICE_ID() BYTE_READ_FUNC(BYTE_READ_ID, 0x00, 4, DPID);

void READ_CONFIG(void)
{
  BYTE_READ_FUNC(BYTE_READ_CONFIG, 0x00, 5, CONF);
}

#define READ_COMPANY_ID() BYTE_READ_FUNC(READ_CID, 0x00, 1, &CID);

void TM0_ini(void)
{
  TH0 = TL0 = 0; // Interrupt timer 140us
  set_TR0;       // Start timer0
  set_PSH_NO_PG_CLR; // Serial port 0 interrupt level2
  set_ET0;
}
#if CHECK_SEQUENCE_NO
uint8_t check_g_packno(void){
  if (g_packNo[0] != uart_rcvbuf[4] || g_packNo[1] != uart_rcvbuf[5]){
    return FALSE;
  }
  return TRUE;
}
#endif
void inc_g_packno(void){
  g_packNo[0]++;
  if (g_packNo[0] == 0x00)
    g_packNo[1]++;
}

void Package_checksum(void)
{
  g_checksum = 0;
  for (count = 0; count < 64; count++)
  {
    g_checksum = g_checksum + uart_rcvbuf[count];
  }
  inc_g_packno();
  uart_txbuf[0] = g_checksum & 0xff;
  uart_txbuf[1] = (g_checksum >> 8) & 0xff;
  uart_txbuf[2] = 0; // just in case they try to read it as a 32-bit number
  uart_txbuf[3] = 0;
  uart_txbuf[4] = g_packNo[0]; // Spec technically has these as 32-bit numbers, so pad with zeros
  uart_txbuf[5] = g_packNo[1];
  uart_txbuf[6] = 0;
  uart_txbuf[7] = 0;
}

void Send_64byte_To_UART0(void)
{
  for (count = 0; count < 64; count++)
  {
    TI = 0;
    SBUF = uart_txbuf[count];
    while (TI == 0)
      ;
    set_WDCLR;
  }
}

void Serial_ISR(void) __interrupt(4)
{
  uint8_t tmp;
  if (TI == 1)
  {
    clr_TI; // Clear TI (Transmit Interrupt).
  }
  if (RI == 1)
  {
    tmp = SBUF;
    uart_rcvbuf[bufhead++] = tmp;
    clr_RI; // Clear RI (Receive Interrupt).
    
    // If we're not yet connected, ignore all bytes until we get a CMD_CONNECT
    if (g_state == DISCONNECTED_STATE) {
      // bufhead is now 1, so tmp holds bufhead[0]
      if (tmp == CMD_CONNECT)
      {
        g_state = CONNECTING_STATE;
      } else { // otherwise, reset
        goto _RESET_BUF;
      }
    } else if (g_state == CONNECTING_STATE) {
      // CMD is 32-bit little endian, CMD_CONNECT is 0x000000ae; if bufhead 1-3 is not 0, reset
      // bufhead == 2 means tmp holds bufhead[1], bufhead == 3 means tmp holds bufhead[2], etc.
      if (bufhead < 5){
        if (tmp != 0) {
          g_state = DISCONNECTED_STATE;
          goto _RESET_BUF;
        }
      } else { // legit packet, start processing
        g_state = COMMAND_STATE;
      }
    }
  }
  if (bufhead == 1)
  {
    g_timer1Over = 0;
    g_timer1Counter = 90; // Set timeout for UART idle checking.
  }
  if (bufhead == 64)
  {
    bUartDataReady = TRUE;
_RESET_BUF:
    g_timer1Counter = 0;
    g_timer1Over = 0;
    bufhead = 0;
  }
}

void Timer0_ISR(void) __interrupt(1)
{
  if (g_timer0Counter)
  {
    g_timer0Counter--;
    if (!g_timer0Counter)
    {
      g_timer0Over = 1;
    }
  }

  if (g_timer1Counter)
  {
    g_timer1Counter--;
    if (!g_timer1Counter)
    {
      g_timer1Over = 1;
    }
  }
}

unsigned int __xdata start_address, end_address;

void dump()
{
  uint16_t addr;
  for (count = 8; count < 64; count++)
  {
    addr = current_address >= LDROM_ADDRESS ? current_address - LDROM_ADDRESS : current_address;
    IAPCN = current_address >= LDROM_ADDRESS ? BYTE_READ_LD : BYTE_READ_AP;
    IAPAL = addr & 0xff;
    IAPAH = (addr >> 8) & 0xff;
    ISP_SET_IAPGO;
    uart_txbuf[count] = IAPFD;
    // g_totalchecksum+=uart_txbuf[count];
    if (++current_address == end_address)
    {
      g_state = COMMAND_STATE;
      break;
    }
  }
  Package_checksum();
  Send_64byte_To_UART0();
}

void update(uint8_t start_count)
{
  for (count = start_count; count < PACKSIZE; count++)
  {
    // g_timer0Counter=Timer0Out_Counter;
    IAPCN = BYTE_PROGRAM_AP; // Program byte
    IAPAL = current_address & 0xff;
    IAPAH = (current_address >> 8) & 0xff;
    IAPFD = uart_rcvbuf[count];

    ISP_SET_IAPGO;

    IAPCN = BYTE_READ_AP; // Verify program byte

    if (IAPFD != uart_rcvbuf[count]) // if not correct
      while (1)
        ; // Error state, loop forever
    // if (CHPCON==0x43)              //if error flag set, program error stop ISP
    // while(1);

    g_totalchecksum = g_totalchecksum + uart_rcvbuf[count];
    current_address++;

    if (current_address == end_address)
    {
      g_state = COMMAND_STATE;
      // Specification implies that this shouldn't boot the APROM after programming.
      // if (start_count != INITIAL_UPDATE_PKT_START){
      //   g_timer0Over =1; // boot APROM
      // }
      break;
    }
  }
  Package_checksum();
  uart_txbuf[8] = g_totalchecksum & 0xff;
  uart_txbuf[9] = (g_totalchecksum >> 8) & 0xff;
  Send_64byte_To_UART0();
}

void set_addrs()
{
  start_address = uart_rcvbuf[8];
  start_address |= ((uart_rcvbuf[9] << 8) & 0xFF00);
  AP_size = uart_rcvbuf[12];
  AP_size |= ((uart_rcvbuf[13] << 8) & 0xFF00);
  current_address = start_address;
  end_address = AP_size + start_address;
}

void finish_read_config()
{
  READ_CONFIG();
  Package_checksum();
  uart_txbuf[8] = CONF[0];
  uart_txbuf[9] = CONF[1];
  uart_txbuf[10] = CONF[2];
  uart_txbuf[11] = CONF[3];
  uart_txbuf[12] = CONF[4];
  uart_txbuf[13] = 0xff;
  uart_txbuf[14] = 0xff;
  uart_txbuf[15] = 0xff;
  Send_64byte_To_UART0();
}

void erase_ap(uint16_t addr, uint16_t end_addr)
{
  set_APUEN;
  IAPFD = 0xFF; // Erase must set IAPFD = 0xFF
  IAPCN = PAGE_ERASE_AP;
  for (; addr < end_addr; addr += PAGE_SIZE)
  {
    IAPAL = LOBYTE(addr);
    IAPAH = HIBYTE(addr);
    ISP_SET_IAPGO;
  }
}

void send_fail_packet(){
  Package_checksum();
  uart_txbuf[0] = ~uart_txbuf[0];
  uart_txbuf[1] = ~uart_txbuf[1];
  Send_64byte_To_UART0();
}
// #define _DEBUG_LEDS 1
#ifdef _DEBUG_LEDS
#define enableLEDs    P03_PushPull_Mode; P12_PushPull_Mode; P05_PushPull_Mode;
#define disableLEDs   P03_Quasi_Mode; P05_Quasi_Mode; P12_Quasi_Mode;
#define set_led_connected(val)  P03 = val
#define set_error_led(val)  P05 = val
#define set_led_online(val)  P12 = val
#define flash_error_led() { \
  for (count = 0; count < 7; count++) { \
    P05 = ~P05;                       \
    for (uint8_t i = 0; i < 255; i++)  \
      for (uint8_t j = 0; j < 255; j++) \
        ; \
  } \
}

#else
#define enableLEDs
#define disableLEDs
#define set_led_connected(val)
#define set_error_led(val)
#define set_led_online(val)
#define flash_error_led()
#endif

void main(void)
{
  enableLEDs;
  set_led_online(0);
  set_led_connected(0);
  set_error_led(0);
  EA = 0;
  clr_SFRS_SFRPAGE; // always use SFR page 0; we don't use any SFRs on page 1.
  set_IAPEN;
  MODIFY_HIRC_16588();
#ifdef isp_with_wdt
  TA = 0x55;
  TA = 0xAA;
  WDCON = 0x07;
#endif
  // Always use 115200 baud rate to maintain compatibility with other ISP programs
  UART0_ini_115200();
  TM0_ini();
  EA = 1;
  g_timer0Over = 0;
  g_timer0Counter = Timer0Out_Counter;
  g_state = COMMAND_STATE;
  set_led_online(1);
  while (1)
  {
    if (bUartDataReady == TRUE)
    {
      EA = 0; // Disable all interrupts
      uint8_t cmd = uart_rcvbuf[0];
      inc_g_packno();
#if CHECK_SEQUENCE_NO
      if (cmd != CMD_CONNECT && cmd != CMD_SYNC_PACKNO && !check_g_packno()){
        Package_checksum();
        Send_64byte_To_UART0();
        g_state = COMMAND_STATE;
        goto _end_of_switch;
      }
#endif
      if (cmd != CMD_FORMAT2_CONTINUATION) {  // Dump/Update over (possibly prematurely)
        g_state = COMMAND_STATE;
      } 
      else if (g_state == DUMPING_STATE)
      {
        dump();
        goto _end_of_switch;
      }
      else if (g_state == UPDATING_STATE)
      {
        update(8);
        goto _end_of_switch;
      }

      switch (cmd)
      {
      case CMD_CONNECT:
        g_packNo[0] = 0;
        g_packNo[1] = 0;
        set_led_connected(1);
        goto _CONN_COMMON;
      case CMD_SYNC_PACKNO:
#if CHECK_SEQUENCE_NO
      // set the pack number to the received pack number
        if (uart_rcvbuf[4] != uart_rcvbuf[8] || uart_rcvbuf[5] != uart_rcvbuf[9])
        {
          g_packNo[0] = 0xFF;
          g_packNo[1] = 0xFF; // So that it rolls over to 0 when we transmit
        }
        else
#endif
        {
          g_packNo[0] = uart_rcvbuf[4];
          g_packNo[1] = uart_rcvbuf[5];
        }
          // fallthrough
_CONN_COMMON:
      {
        Package_checksum();
        Send_64byte_To_UART0();
        g_timer0Counter = 0; // ISP connection made, stop ISP connection timeout
        g_timer0Over = 0;
        break;
      }

      case CMD_GET_FWVER:
      {
        Package_checksum();
        uart_txbuf[8] = FW_VERSION;
        Send_64byte_To_UART0();
        break;
      }

      case CMD_RUN_LDROM:
      {
        Package_checksum();
        Send_64byte_To_UART0();
        break;
      }
      case CMD_RUN_APROM:
      case CMD_RESET:
      {
        goto _APROM;
        break;
      }

      // Always follow this convention for getting the DeviceID for compatibility with ISP programs
      case CMD_GET_DEVICEID:
      {
        READ_DEVICE_ID();
        Package_checksum();
        uart_txbuf[8] = DPID[0];
        uart_txbuf[9] = DPID[1];
        uart_txbuf[10] = 0x00;
        uart_txbuf[11] = 0x00;
        Send_64byte_To_UART0();
        break;
      }
      case CMD_GET_UID:
      {
        BYTE_READ_FUNC(READ_UID, 0, UID_LENGTH, &uart_txbuf[8]);
        Package_checksum();
        Send_64byte_To_UART0();
        break;
      }
      case CMD_GET_CID:
      {
        READ_COMPANY_ID();
        Package_checksum();
        uart_txbuf[8] = CID;
        Send_64byte_To_UART0();
        break;
      }
      case CMD_GET_UCID:
      {
        BYTE_READ_FUNC(READ_UID, 0x20, UCID_LENGTH, &uart_txbuf[8]);
        Package_checksum();
        Send_64byte_To_UART0();
        break;
      }
      case CMD_GET_FLASHMODE:
      {
        READ_CONFIG();
        Package_checksum();
        // Check last bit of first config byte

        uart_txbuf[8] = (CONF[0] & 0x80) ? APMODE : LDMODE;

        Send_64byte_To_UART0();
        break;
      }

      case CMD_ERASE_ALL:
      {
        erase_ap(0x0000, APROM_SIZE);
        Package_checksum();
        Send_64byte_To_UART0();
        break;
      }

      case CMD_READ_CONFIG:
      {
        finish_read_config();
        break;
      }

      case CMD_UPDATE_CONFIG:
      {
        set_CFUEN; // Erase CONFIG
        IAPCN = PAGE_ERASE_CONFIG;
        IAPAL = 0x00;
        IAPAH = 0x00;
        IAPFD = 0xFF;
        ISP_SET_IAPGO;

        IAPCN = BYTE_PROGRAM_CONFIG; // Program CONFIG

        IAPFD = uart_rcvbuf[8];
        for (count = 9; count < 13; count++)
        {
          ISP_SET_IAPGO;
          IAPFD = uart_rcvbuf[count];
          IAPAL++;
        }
        ISP_SET_IAPGO;
        clr_CFUEN;

        finish_read_config();
        break;
      }
      case CMD_READ_ROM:
      {
        set_addrs();
        g_totalchecksum = 0;
        g_state = DUMPING_STATE;
        dump();
        break;
      }
      case CMD_UPDATE_APROM:
      {
        // g_timer0Counter=Timer0Out_Counter;
        set_addrs();
        // Don't try and overwrite the LDROM
        if (end_address > LDROM_ADDRESS){
          // fail
          send_fail_packet();
          break;
        }
        erase_ap((start_address & PAGE_MASK), end_address);
        g_totalchecksum = 0;
        g_state = UPDATING_STATE;
        update(16);
        break;
      }
      case CMD_ISP_PAGE_ERASE:
      {
        set_addrs();
        erase_ap((start_address & PAGE_MASK), (start_address & PAGE_MASK) + PAGE_SIZE);
        Package_checksum();
        Send_64byte_To_UART0();
        break;
      }
      default: // Invalid command (or CMD_RESEND_PACKET, which we can't support because of lack of memory)
      {
          send_fail_packet();
          break;
      }
      } // end of switch
_end_of_switch:
      bUartDataReady = FALSE;
      bufhead = 0;

      EA = 1;
    }
    // ISP connection timeout
    if (g_timer0Over == 1)
    {
      nop;
      flash_error_led();
      goto _APROM;
    }

    // uart has timed out or there was a buffer error
    if (g_timer1Over == 1)
    {
      if ((bufhead != 64))
      {
        bufhead = 0;
      }
    }
  }

_APROM:
  EA = 0; // Disable all interrupts
  MODIFY_HIRC_16();
  set_led_connected(0);
  set_led_online(0);
  disableLEDs;
  clr_IAPEN;
  TA = 0xAA;
  TA = 0x55;
  CHPCON = 0x80; // Software reset, enable boot from APROM
  /* Trap the CPU */
  while (1)
    ;
}
 