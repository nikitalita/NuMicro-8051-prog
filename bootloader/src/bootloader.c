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

unsigned char PID_highB,PID_lowB,DID_highB,DID_lowB,CONF0,CONF1,CONF2,CONF3,CONF4;
unsigned char recv_CONF0,recv_CONF1,recv_CONF2,recv_CONF3,recv_CONF4;

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

void READ_ID(void)
{
//    set_CHPCON_IAPEN;
    IAPCN = BYTE_READ_ID;
    IAPAH = 0x00;
    IAPAL = 0x00;
    set_IAPGO;
    DID_lowB = IAPFD;
    IAPAL = 0x01;
    set_IAPGO;
    DID_highB = IAPFD;
    IAPAL = 0x02;
    set_IAPGO;
    PID_lowB = IAPFD;
    IAPAL = 0x03;
    set_IAPGO;
    PID_highB = IAPFD;
}
void READ_CONFIG(void)
{
    IAPCN = BYTE_READ_CONFIG;
    IAPAH = 0x00;
    IAPAL = 0x00;
    set_IAPGO;
    CONF0 = IAPFD;
    IAPAL = 0x01;
    set_IAPGO;
    CONF1 = IAPFD;
    IAPAL = 0x02;
    set_IAPGO;
    CONF2 = IAPFD;
    IAPAL = 0x03;
    set_IAPGO;
    CONF3 = IAPFD;
    IAPAL = 0x04;
    set_IAPGO;
    CONF4 = IAPFD;
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

while(1)
{
        if(bUartDataReady == TRUE)
        {
          EA=0; //DISABLE ALL INTERRUPT
          if(g_programflag==1)
          {
            for(count=8;count<64;count++)
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
                 g_timer0Over =1;
                 goto END_2;
              }
            } 
END_2:
            Package_checksum();
            uart_txbuf[8]=g_totalchecksum&0xff;
            uart_txbuf[9]=(g_totalchecksum>>8)&0xff;
            Send_64byte_To_UART0();
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
            
            case CMD_RUN_APROM:
            {
              goto _APROM;
              break;
            }

            //please for ISP programmer GUI, ID always use following rule to transmit.
            case CMD_GET_DEVICEID:
            {
              READ_ID();
              Package_checksum();
              uart_txbuf[8]=DID_lowB;  
              uart_txbuf[9]=DID_highB;  
              uart_txbuf[10]=0x00;  
              uart_txbuf[11]=0x00;
              Send_64byte_To_UART0();  
              break;
            }

            case CMD_ERASE_ALL:
            {
              set_APUEN;
              IAPFD = 0xFF;          //Erase must set IAPFD = 0xFF
              IAPCN = PAGE_ERASE_AP;
              for(flash_address=0x0000;flash_address<APROM_SIZE/PAGE_SIZE;flash_address++)
              {        
                IAPAL = LOBYTE(flash_address*PAGE_SIZE);
                IAPAH = HIBYTE(flash_address*PAGE_SIZE);
              ISP_SET_IAPGO;
              }
              Package_checksum();
              Send_64byte_To_UART0();  
              break;
            }

            case CMD_READ_CONFIG:
            {
              READ_CONFIG();
              Package_checksum();
              uart_txbuf[8]=CONF0;
              uart_txbuf[9]=CONF1;
              uart_txbuf[10]=CONF2;
              uart_txbuf[11]=CONF3;
              uart_txbuf[12]=CONF4;
              uart_txbuf[13]=0xff;
              uart_txbuf[14]=0xff;
              uart_txbuf[15]=0xff;
              Send_64byte_To_UART0();
            break;
            }
            
            case CMD_UPDATE_CONFIG:
            {
              recv_CONF0 = uart_rcvbuf[8];
              recv_CONF1 = uart_rcvbuf[9];
              recv_CONF2 = uart_rcvbuf[10];
              recv_CONF3 = uart_rcvbuf[11];
              recv_CONF4 = uart_rcvbuf[12];

              set_CFUEN;                  /*Erase CONFIG */
              IAPCN = PAGE_ERASE_CONFIG;
              IAPAL = 0x00;
              IAPAH = 0x00;
              IAPFD = 0xFF;
              ISP_SET_IAPGO;
              IAPCN = BYTE_PROGRAM_CONFIG;        /*Program CONFIG*/ 
              IAPFD = recv_CONF0;
              ISP_SET_IAPGO;
              IAPFD = recv_CONF1;
              IAPAL = 0x01;
              ISP_SET_IAPGO;
              IAPAL = 0x02;
              IAPFD = recv_CONF2;
              ISP_SET_IAPGO;
              IAPAL = 0x03;
              IAPFD = recv_CONF3;
              ISP_SET_IAPGO;
              IAPAL = 0x04;
              IAPFD = recv_CONF4;
              ISP_SET_IAPGO;
              clr_CFUEN;

              READ_CONFIG();                        /*Read new CONFIG*/  
              Package_checksum();
              uart_txbuf[8]=CONF0;
              uart_txbuf[9]=CONF1;
              uart_txbuf[10]=CONF2;
              uart_txbuf[11]=CONF3;
              uart_txbuf[12]=CONF4;
              uart_txbuf[13]=0xff;
              uart_txbuf[14]=0xff;
              uart_txbuf[15]=0xff;
              Send_64byte_To_UART0();
              break;
            }

            case CMD_UPDATE_APROM:
            {
//              g_timer0Counter=Timer0Out_Counter;
              set_APUEN;
              IAPFD = 0xFF;          //Erase must set IAPFD = 0xFF
              IAPCN = PAGE_ERASE_AP;
              
              start_address = 0;
              start_address = uart_rcvbuf[8];
              start_address |= ((uart_rcvbuf[9]<<8)&0xFF00);
              AP_size = 0;
              AP_size = uart_rcvbuf[12];
              AP_size |= ((uart_rcvbuf[13]<<8)&0xFF00);

              u16_addr = start_address + AP_size;
              flash_address = (start_address&0xFF00);
 
              while(flash_address< u16_addr)
              {
                IAPAL = LOBYTE(flash_address);
                IAPAH = HIBYTE(flash_address);
                ISP_SET_IAPGO;
                flash_address += PAGE_SIZE;
              }
              
              g_totalchecksum = 0;
              flash_address = start_address;
              g_programflag = 1;

              for(count=16;count<64;count++)
              {
                IAPCN = BYTE_PROGRAM_AP;
                IAPAL = flash_address&0xff;
                IAPAH = (flash_address>>8)&0xff;
                IAPFD = uart_rcvbuf[count];
                ISP_SET_IAPGO;
                IAPCN = BYTE_READ_AP;                //program byte verify
                set_IAPGO;

                if(IAPFD!=uart_rcvbuf[count])
                while(1);
//                if (CHPCON==0x43)                //if error flag set, program error stop ISP
//                while(1);
                
                g_totalchecksum=g_totalchecksum+uart_rcvbuf[count];
                flash_address++;

                if(flash_address==AP_size)
                {
                  g_programflag=0;
                   goto END_1;
                }
              }
END_1:                
              Package_checksum();
              uart_txbuf[8]=g_totalchecksum&0xff;
              uart_txbuf[9]=(g_totalchecksum>>8)&0xff;
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


