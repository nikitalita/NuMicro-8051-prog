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


__bit BIT_TMP;
volatile uint8_t  __xdata uart_rcvbuf[64]; 
volatile uint8_t  __xdata uart_txbuf[64];
volatile uint8_t  __data  bufhead;
volatile uint16_t __data   flash_address; 
volatile uint16_t __data   AP_size;
volatile uint8_t  __data  g_timer1Counter;
volatile uint8_t  __data  count; 
volatile uint16_t __data   g_timer0Counter;
volatile uint32_t __data   g_checksum;
volatile uint32_t __data   g_totalchecksum;
volatile __bit   bUartDataReady;
volatile __bit   g_timer0Over;
volatile __bit   g_timer1Over;
volatile __bit   g_programflag;
volatile __bit   g_dumpflag;

// unsigned char PID_highB,PID_lowB,DID_highB,DID_lowB,CONF0,CONF1,CONF2,CONF3,CONF4;
unsigned char CID;
unsigned char CONF[5];
unsigned char UID[3];
unsigned char UCID[4];
unsigned char DPID[4];
#define FLASH_SIZE 0x4800
#define APROM_PAGE_COUNT APROM_SIZE/PAGE_SIZE
#define FLASH_PAGE_COUNT FLASH_SIZE/PAGE_SIZE
#define LDROM_ADDRESS APROM_SIZE

void UART0_ini_115200(void)
{
    P06_Quasi_Mode;    
    P07_Quasi_Mode;
  
    SCON = 0x52;     //UART0 Mode1,REN=1,TI=1
    TMOD |= 0x20;    //Timer1 Mode1
    
    set_SMOD;        //UART0 Double Rate Enable
    set_T1M;
    clr_BRCK;        //Serial port 0 baud rate clock source = Timer1

    TH1 = (unsigned char)(256 - (1037500/115200));               /*16 MHz */
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

void READ_UNIQUE_ID(void) {
  BYTE_READ_FUNC(READ_UID, 0x00, 3, UID);
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
  TH0=TL0=0;    //interrupt timer 140us
  set_TR0;      //Start timer0
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
      g_timer1Counter=90; //for check uart timeout using
    }
  if(bufhead == 64)
    {
      
      bUartDataReady = TRUE;
      g_timer1Counter=0;
      g_timer1Over=0;
      bufhead = 0;
    }    
}
// void timer_decrement(uint16_t * timer, uint8_t * timer_over){
//   if(*timer)
//   {
//     (*timer)--;
//     if(!(*timer))
//     {
//       *timer_over=1;
//     }
//   }
// }
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
#define ISP_SET_IAPGO set_IAPGO_WDCLR
#else
#define ISP_SET_IAPGO set_IAPGO
#endif


#define set_IAPTRG_IAPGO_WDCLR   BIT_TMP=EA;EA=0;set_WDCON_WDCLR;TA=0xAA;TA=0x55;IAPTRG|=0x01;EA=BIT_TMP

unsigned int __xdata start_address,u16_addr;


void dump(){
  uint16_t addr;
  for(count=8;count<64;count++)
  {
    addr = flash_address >= LDROM_ADDRESS ? flash_address - LDROM_ADDRESS : flash_address;
    IAPCN = flash_address >= LDROM_ADDRESS ? BYTE_READ_LD : BYTE_READ_AP;
    IAPAL = addr&0xff;
    IAPAH = (addr>>8)&0xff;
    ISP_SET_IAPGO;
    uart_txbuf[count]=IAPFD;
    g_totalchecksum+=uart_txbuf[count];
    if(++flash_address==AP_size)
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
  for(count=start_count;count<64;count++)
  {
//              g_timer0Counter=Timer0Out_Counter;
    IAPCN = BYTE_PROGRAM_AP;          //program byte
    IAPAL = flash_address&0xff;
    IAPAH = (flash_address>>8)&0xff;
    IAPFD=uart_rcvbuf[count];
    
    ISP_SET_IAPGO;

    IAPCN = BYTE_READ_AP;              //program byte verify
    if(IAPFD!=uart_rcvbuf[count])
    while(1);                          
//              if (CHPCON==0x43)              //if error flag set, program error stop ISP
//              while(1);
    
    g_totalchecksum=g_totalchecksum+uart_rcvbuf[count];
    flash_address++;

    if(flash_address==AP_size)
    {
        g_programflag=0;
        if (start_count != 16){
          g_timer0Over =1;
        }
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
  start_address = 0;
  start_address = uart_rcvbuf[8];
  start_address |= ((uart_rcvbuf[9]<<8)&0xFF00);
  AP_size = 0;
  AP_size = uart_rcvbuf[12];
  AP_size |= ((uart_rcvbuf[13]<<8)&0xFF00);

}

void finish_read_config(){
  READ_CONFIG();                        /*Read new CONFIG*/  
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

// ******* MAIN! *******
void main (void)
{

  set_IAPEN;
  MODIFY_HIRC_16588();
#ifdef  isp_with_wdt
  TA=0x55;TA=0xAA;WDCON=0x07;
#endif
//uart initial for ISP programmer GUI, always use 115200 baudrate
  UART0_ini_115200();
  TM0_ini();
	EA  =1 ;
//	P11_PushPull_Mode;
//	CKDIV = 50;					//HIRC devider 160
//	set_CLOEN;
//	while(1);
  g_timer0Over=0;
  g_timer0Counter=Timer0Out_Counter;
  g_programflag=0;
  g_dumpflag=0;

while(1)
{
        if(bUartDataReady == TRUE)
        {
          EA=0; //DISABLE ALL INTERRUPT
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
              g_timer0Counter=0; //clear timer 0 for no reset
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

            //please for ISP programmer GUI, ID always use following rule to transmit.
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
              READ_UNIQUE_ID();
              Package_checksum();
              uart_txbuf[8]=UID[0];  
              uart_txbuf[9]=UID[1];  
              uart_txbuf[10]=UID[2];
              // uart_txbuf[11]=0x00;  
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
              // TODO: figure out how to get this
              Package_checksum();
              uart_txbuf[8]=0xFF;
              uart_txbuf[9]=0xFF;
              uart_txbuf[10]=0xFF;
              uart_txbuf[11]=0xFF;
              Send_64byte_To_UART0();
              break;
            }
            case CMD_GET_FLASHMODE:
            {
              READ_CONFIG();
              Package_checksum();
              // check last bit of first config byte

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
              set_CFUEN;                  /*Erase CONFIG */
              IAPCN = PAGE_ERASE_CONFIG;
              IAPAL = 0x00;
              IAPAH = 0x00;
              IAPFD = 0xFF;
              ISP_SET_IAPGO;

              IAPCN = BYTE_PROGRAM_CONFIG;        /*Program CONFIG*/ 
              
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
            case CMD_DUMP_ROM:
            {
              flash_address = 0;
              start_address = 0;
              AP_size = FLASH_SIZE;
              g_dumpflag=1;
              dump();
              break;
            }
            case CMD_READ_ROM:
            {
              set_addrs();
              g_dumpflag=1;
              dump();
              break;
            }
            case CMD_UPDATE_APROM:
            {
//              g_timer0Counter=Timer0Out_Counter;
              set_addrs();
              u16_addr = start_address + AP_size;
              flash_address = (start_address&0xFF00);

              erase_ap(flash_address, u16_addr);
              
              g_totalchecksum = 0;
              flash_address = start_address;
              g_programflag = 1;

              update(16);          
              break;
            }
            case CMD_ISP_PAGE_ERASE:
            {
              set_addrs();
              flash_address = (start_address&0xFF00);
              erase_ap(flash_address, 1);
              Package_checksum();
              Send_64byte_To_UART0();  
              break;
            }
          }  
          bUartDataReady = FALSE;
          bufhead = 0;

          EA=1;
      }
      /*For connect timer out   */
      if(g_timer0Over==1)
      {
        nop;
        goto _APROM;
      }
      
      /*for uart time out or buffer error  */
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
    TA = 0xAA; TA = 0x55; CHPCON = 0x80;                   //software reset enable boot from APROM
    /* Trap the CPU */
    while(1);  
}


