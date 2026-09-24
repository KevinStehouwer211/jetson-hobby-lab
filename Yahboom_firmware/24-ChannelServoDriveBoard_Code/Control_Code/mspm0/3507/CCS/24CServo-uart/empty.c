#include "ti_msp_dl_config.h"
#include "delay.h"
#include "usart.h"

unsigned char date1,date2,date3;
int  i;

void UART_Servo(unsigned char servonum,unsigned char angle)
{
	servonum = 64 + servonum;
	date1 = angle/100 + 48;
	date2 = (angle%100)/10 + 48;
	date3 = angle%10 + 48;
	USART_SendData(0x24);//发送包头			Sending packet header
	USART_SendData(servonum);//发送舵机编号	Send servo number
	USART_SendData(date1);//发送角度	Send angle
	USART_SendData(date2);//发送角度	Send angle
	USART_SendData(date3);//发送角度	Send angle
	USART_SendData(0x23);//发送包尾		Send packet tail
	delay_ms(100);
}

int main(void)
{
    USART_Init();
    while (1)
    {
		for(i = 0;i<180;i+=5)
		{
			UART_Servo(1,i);
			if(i>180) i=0;
		}
		
    }
}
