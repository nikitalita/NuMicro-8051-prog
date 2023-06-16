#define TRUE       1
#define FALSE     0

#define Timer0Out_Counter    800

#define FW_VERSION           0xD0

#include "isp.h"



#define PAGE_ERASE_AP        0x22
#define BYTE_READ_AP         0x00
#define BYTE_PROGRAM_AP      0x21
#define BYTE_READ_ID         0x0C
#define PAGE_ERASE_CONFIG    0xE2
#define BYTE_READ_CONFIG     0xC0
#define BYTE_PROGRAM_CONFIG  0xE1
#define READ_UID             0x04

#define PAGE_ERASE_LD    0x62
#define BYTE_PROGRAM_LD  0x61
#define BYTE_READ_LD     0x40
#define READ_CID        0x0B

#define PAGE_SIZE            128
#define APROM_SIZE           16*1024

 

// extern __bit BIT_TMP;
// extern volatile uint8_t  __xdata uart_rcvbuf[64]; 
// extern volatile uint8_t  __xdata uart_txbuf[64];
// extern volatile uint8_t  __data  bufhead;
// extern volatile uint16_t __data   flash_address; 
// extern volatile uint16_t __data   AP_size;
// extern volatile uint8_t  __data  g_timer1Counter;
// extern volatile uint8_t  __data  count; 
// extern volatile uint16_t __data   g_timer0Counter;
// extern volatile uint32_t __data   g_checksum;
// extern volatile uint32_t __data   g_totalchecksum;
// extern volatile __bit   bUartDataReady;
// extern volatile __bit   g_timer0Over;
// extern volatile __bit   g_timer1Over;
// extern volatile __bit   g_programflag;

// void TM0_ini(void);
// void MODIFY_HIRC_16588(void);
// void MODIFY_HIRC_16(void);
// void Package_checksum(void);
// void Send_64byte_To_UART0(void);
// void UART0_ini_115200(void);
// void MODIFY_HIRC_24(void);
// void MODIFY_HIRC_16(void);
// void READ_DEVICE_ID(void);
// void READ_CONFIG(void);