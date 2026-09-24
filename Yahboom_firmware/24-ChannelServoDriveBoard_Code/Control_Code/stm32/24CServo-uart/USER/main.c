#include "sys.h"
#include "delay.h"
#include "usart.h"
#include "usart2.h"
#include "timer.h"  
#include "malloc.h"  

#define usart2_baund  9600//串口2波特率
unsigned char date1,date2,date3;
int  i;
	
//串口发送一个字节
static void MYUSART_SendData(u8 data)
{
	while((USART2->SR&0X40)==0); 
	USART2->DR = data;
}
void UART_Servo(unsigned char servonum,unsigned char angle)
{
  servonum = 64 + servonum;
    date1 = angle/100 + 48;
    date2 = (angle%100)/10 + 48;
    date3 = angle%10 + 48;
  MYUSART_SendData(0x24);//发送包头
	MYUSART_SendData(servonum);//发送舵机编号
	MYUSART_SendData(date1);//发送角度
	MYUSART_SendData(date2);//发送角度
	MYUSART_SendData(date3);//发送角度
	MYUSART_SendData(0x23);//发送包尾
	delay_ms(100);
}

int main(void)
{
	
	//初始化函数
	NVIC_PriorityGroupConfig(NVIC_PriorityGroup_2);//设置系统中断优先级分组2
	delay_init();  	    //初始化延时函数
	uart_init(115200);	//初始化串口1波特率为115200，用于支持USMART
	usart2_init(usart2_baund);//初始化串口2,用于与模块通讯
	mem_init();
	delay_ms(2000); //延迟2s，待控制板正常工作先
	for(i = 0;i<180;i+=5){
		UART_Servo(1,i);
	}
	UART_Servo(1,0);
	
	while(1){
	}

}




