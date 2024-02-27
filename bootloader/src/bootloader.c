// #include <intrins.h>
#include <stdio.h>
// #include <absacc.h>
#include <string.h>
#include <stdint.h>

#include "N76E003.h"
#include "Common.h"
#include "SFR_Macro.h"
#include "Function_define.h"
#include "isp_uart0.h"
#include "isp_common.h"


// bootloader-specific constants
#define FW_VERSION           0xD0     // Supports extended commands
#define APROM_SIZE           16*1024
#define LDROM_SIZE           2*1024
#define APROM_PAGE_COUNT APROM_SIZE/PAGE_SIZE
#define LDROM_ADDRESS APROM_SIZE

// How long to wait for an ISP connection before booting into APROM
#define Timer0Out_Counter    200 // About 1 second


__bit BIT_TMP;
volatile uint8_t  __xdata uart_rcvbuf[64]; 
volatile uint8_t  __xdata uart_txbuf[64];
volatile uint8_t  __data  bufhead;
volatile uint16_t __data  current_address; 
volatile uint16_t __data  AP_size;
volatile uint8_t  __data  g_timer1Counter;
volatile uint8_t  __data  count; 
volatile uint16_t __data  g_timer0Counter;
volatile uint32_t __data  g_checksum;
volatile uint32_t __data  g_totalchecksum;
volatile __bit   bUartDataReady;
volatile __bit   g_timer0Over;
volatile __bit   g_timer1Over;
volatile __bit   g_programflag;
volatile __bit   g_dumpflag;

#define UCID_LENGTH 0x30
#define UID_LENGTH 12
unsigned char CID;
unsigned char CONF[5];
unsigned char DPID[4];

void UART0_ini_115200(void)
{
    P06_Quasi_Mode;    
    P07_Quasi_Mode;
  
    SCON = 0x52;     //UART0 Mode1,REN=1,TI=1
    TMOD |= 0x20;    //Timer1 Mode1
    
    set_SMOD;        //UART0 Double Rate Enable
    set_T1M;
    clr_BRCK;        //Serial port 0 baud rate clock source = Timer1

    TH1 = (unsigned char)(256 - (1037500/115200));  /* ISP Rom is always 16.6 MHz */
    set_TR1;
    ES=1;
    EA=1;
}

void MODIFY_HIRC_16588(void)
{
    UINT8 hircmap0,hircmap1;
    UINT16 trimvalue16bit;
    hircmap0 = RCTRIM0;
    hircmap1 = RCTRIM1;
    trimvalue16bit = ((hircmap0<<1)+(hircmap1&0x01));
    trimvalue16bit = trimvalue16bit - 14;
    hircmap1 = trimvalue16bit&0x01;
    hircmap0 = trimvalue16bit>>1;
    TA=0XAA;
    TA=0X55;
    RCTRIM0 = hircmap0;
    TA=0XAA;
    TA=0X55;
    RCTRIM1 = hircmap1;
/* Clear power on flag */
    PCON &= CLR_BIT4;
}

void MODIFY_HIRC_16(void)
{
    unsigned char __data hircmap0,hircmap1;
    IAPAH = 0x00;
    IAPAL = 0x30;
    IAPCN = READ_UID;
    set_IAPGO;
    hircmap0 = IAPFD;
    IAPAL = 0x31;
    set_IAPGO;
    hircmap1 = IAPFD;

    TA=0XAA;
    TA=0X55;
    RCTRIM0 = hircmap0;
    TA=0XAA;
    TA=0X55;
    RCTRIM1 = hircmap1;
}
void BYTE_READ_FUNC(uint8_t cmd, uint8_t start, uint8_t len, uint8_t *buf)
{
    uint8_t i;
    IAPCN = cmd;
    IAPAH = 0x00;
    IAPAL = start;
    for (i = 0; i < len-1; i++)
    {
        set_IAPGO;
        buf[i] = IAPFD;
        IAPAL++;
    }
    // get the last one
    set_IAPGO;
    buf[i] = IAPFD;
}


void READ_DEVICE_ID(void)
{
    BYTE_READ_FUNC(BYTE_READ_ID, 0x00, 4, DPID);
}
void READ_CONFIG(void)
{
    BYTE_READ_FUNC(BYTE_READ_CONFIG, 0x00, 5, CONF);
}

void READ_COMPANY_ID(void){
    BYTE_READ_FUNC(READ_CID, 0x00, 1, &CID);
}

void TM0_ini(void)
{
  TH0=TL0=0;     // Interrupt timer 140us
  set_TR0;       // Start timer0
  set_PSH;       // Serial port 0 interrupt level2
  set_ET0;
}

void Package_checksum(void)
{
  g_checksum=0;
   for(count=0;count<64;count++)
  {
    g_checksum =g_checksum+ uart_rcvbuf[count];    
  }
  uart_txbuf[0]=g_checksum&0xff;
  uart_txbuf[1]=(g_checksum>>8)&0xff;
  uart_txbuf[4]=uart_rcvbuf[4]+1;
  uart_txbuf[5]=uart_rcvbuf[5];
  if(uart_txbuf[4]==0x00)
  uart_txbuf[5]++;

}


void Send_64byte_To_UART0(void)
{
   for(count=0;count<64;count++)
  {
     TI = 0;  
     SBUF = uart_txbuf[count];
     while(TI==0);
     set_WDCLR;
  }
}

void Serial_ISR (void) __interrupt 4 
{
    if (RI == 1)
    {   
      uart_rcvbuf[bufhead++]=  SBUF;    
      clr_RI;                                           // Clear RI (Receive Interrupt).
    }
    if (TI == 1)
    {       
        clr_TI;                                         // Clear TI (Transmit Interrupt).
    }
    if(bufhead ==1)
    {
      g_timer1Over=0;
      g_timer1Counter=90; // Set timeout for UART idle checking.
    }
    if(bufhead == 64)
    {
      
      bUartDataReady = TRUE;
      g_timer1Counter=0;
      g_timer1Over=0;
      bufhead = 0;
    }    
}

void Timer0_ISR (void) __interrupt 1
{
if(g_timer0Counter)
  {
  g_timer0Counter--;
    if(!g_timer0Counter)
    {
    g_timer0Over=1;
    }
  }
  
  if(g_timer1Counter)
  {
  g_timer1Counter--;
    if(!g_timer1Counter)
    {
    g_timer1Over=1;
    }
  }
}  




//#define  isp_with_wdt


#ifdef isp_with_wdt
//set_IAPGO_WDCLR not defined
#define ISP_SET_IAPGO set_IAPGO
#else
#define ISP_SET_IAPGO set_IAPGO
#endif


#define set_IAPTRG_IAPGO_WDCLR   BIT_TMP=EA;EA=0;set_WDCON_WDCLR;TA=0xAA;TA=0x55;IAPTRG|=0x01;EA=BIT_TMP

unsigned int __xdata start_address,end_address;


void dump(){
  uint16_t addr;
  for(count=8;count<64;count++)
  {
    addr = current_address >= LDROM_ADDRESS ? current_address - LDROM_ADDRESS : current_address;
    IAPCN = current_address >= LDROM_ADDRESS ? BYTE_READ_LD : BYTE_READ_AP;
    IAPAL = addr&0xff;
    IAPAH = (addr>>8)&0xff;
    ISP_SET_IAPGO;
    uart_txbuf[count]=IAPFD;
    // g_totalchecksum+=uart_txbuf[count];
    if(++current_address==end_address)
    {
       g_dumpflag=0;
      goto END_DUMP;
    }
  }
END_DUMP:
  Package_checksum();
  Send_64byte_To_UART0();
}

void update(uint8_t start_count){
  for(count=start_count;count<PACKSIZE;count++)
  {
    // g_timer0Counter=Timer0Out_Counter;
    IAPCN = BYTE_PROGRAM_AP;          // Program byte
    IAPAL = current_address&0xff;
    IAPAH = (current_address>>8)&0xff;
    IAPFD = uart_rcvbuf[count];
    
    ISP_SET_IAPGO;

    IAPCN = BYTE_READ_AP;              // Verify program byte

    if(IAPFD!=uart_rcvbuf[count])      // if not correct
      while(1); // Error state, loop forever
      // if (CHPCON==0x43)              //if error flag set, program error stop ISP
      // while(1);
    
    g_totalchecksum=g_totalchecksum+uart_rcvbuf[count];
    current_address++;

    if(current_address==end_address)
    {
        g_programflag=0;
        // Specification implies that this shouldn't boot the APROM after programming.
        // if (start_count != INITIAL_UPDATE_PKT_START){
        //   g_timer0Over =1; // boot APROM
        // }
        goto END_UPDATE;
    }
  } 
END_UPDATE:
  Package_checksum();
  uart_txbuf[8]=g_totalchecksum&0xff;
  uart_txbuf[9]=(g_totalchecksum>>8)&0xff;
  Send_64byte_To_UART0();
}

void set_addrs(){
  start_address = uart_rcvbuf[8];
  start_address |= ((uart_rcvbuf[9]<<8)&0xFF00);
  AP_size = uart_rcvbuf[12];
  AP_size |= ((uart_rcvbuf[13]<<8)&0xFF00);
  current_address = start_address;
  end_address = AP_size + start_address;
}

void finish_read_config() {
  READ_CONFIG();
  Package_checksum();
  uart_txbuf[8] =CONF[0];
  uart_txbuf[9] =CONF[1];
  uart_txbuf[10]=CONF[2];
  uart_txbuf[11]=CONF[3];
  uart_txbuf[12]=CONF[4];
  uart_txbuf[13]=0xff;
  uart_txbuf[14]=0xff;
  uart_txbuf[15]=0xff;
  Send_64byte_To_UART0();

}

void erase_ap(uint16_t addr, uint16_t page_count){
  set_APUEN;
  IAPFD = 0xFF;          //Erase must set IAPFD = 0xFF
  IAPCN = PAGE_ERASE_AP;
  for(;addr<page_count;addr+=PAGE_SIZE)
  {        
    IAPAL = LOBYTE(addr);
    IAPAH = HIBYTE(addr);
    ISP_SET_IAPGO;
  }
}

void main (void)
{

  set_IAPEN;
  MODIFY_HIRC_16588();
#ifdef  isp_with_wdt
  TA=0x55;TA=0xAA;WDCON=0x07;
#endif
  // Always use 115200 baud rate to maintain compatibility with other ISP programs
  UART0_ini_115200();
  TM0_ini();
	EA  =1 ;
  g_timer0Over=0;
  g_timer0Counter=Timer0Out_Counter;
  g_programflag=0;
  g_dumpflag=0;

while(1)
{
        if(bUartDataReady == TRUE)
        {
          EA=0; // Disable all interrupts
          if (g_dumpflag==1)
          {
            dump();
          }
          else if(g_programflag==1)
          {
            update(8);
          }
            
          switch(uart_rcvbuf[0])
          {
            case CMD_CONNECT:
            case CMD_SYNC_PACKNO:
            {
              Package_checksum();
              Send_64byte_To_UART0();    
              g_timer0Counter=0; // ISP connection made, stop ISP connection timeout
              g_timer0Over=0;
              break;
            }

            case CMD_GET_FWVER:
            {
              Package_checksum();
              uart_txbuf[8]=FW_VERSION;
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
              uart_txbuf[8]=DPID[0];  
              uart_txbuf[9]=DPID[1];  
              uart_txbuf[10]=0x00;
              uart_txbuf[11]=0x00;
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
              uart_txbuf[8]=CID;
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
            // case CMD_GET_BANDGAP:
            // {
            //   BYTE_READ_FUNC(READ_UID, 0x0C, 2, &uart_txbuf[8]);
            //   Package_checksum();
            //   Send_64byte_To_UART0();
            //   break;
            // }
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
              erase_ap(0x0000, APROM_PAGE_COUNT);
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
              set_CFUEN;                  // Erase CONFIG
              IAPCN = PAGE_ERASE_CONFIG;
              IAPAL = 0x00;
              IAPAH = 0x00;
              IAPFD = 0xFF;
              ISP_SET_IAPGO;

              IAPCN = BYTE_PROGRAM_CONFIG;  // Program CONFIG
              
              IAPFD=uart_rcvbuf[8];
              for (count=9;count<13;count++)
              {
                ISP_SET_IAPGO;
                IAPFD=uart_rcvbuf[count];
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
              g_dumpflag=1;
              dump();
              break;
            }
            case CMD_UPDATE_APROM:
            {
              // g_timer0Counter=Timer0Out_Counter;
              set_addrs();
              // TODO: check if the mask is correct (should be 0xFF80 since page size is 128)
              erase_ap((start_address&0xFF80), end_address);
              g_totalchecksum = 0;
              g_programflag = 1;

              update(16);          
              break;
            }
            case CMD_ISP_PAGE_ERASE:
            {
              set_addrs();
              erase_ap((start_address&0xFF80), 1);
              Package_checksum();
              Send_64byte_To_UART0();  
              break;
            }
          }  
          bUartDataReady = FALSE;
          bufhead = 0;

          EA=1;
      }
      // ISP connection timeout
      if(g_timer0Over==1)
      {
        nop;
        goto _APROM;
      }
      
      // uart has timed out or there was a buffer error
       if(g_timer1Over==1)
      {
       if((bufhead<64)&&(bufhead>0)||(bufhead>64))
         {
             bufhead=0;
         }
      }  
}   

_APROM:
    MODIFY_HIRC_16();
    clr_IAPEN;
    TA = 0xAA; TA = 0x55; CHPCON = 0x80;  // Software reset, enable boot from APROM
    /* Trap the CPU */
    while(1);  
}


