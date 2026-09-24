
#include <reg52.h>

sbit beep=P2^3;
sbit dula=P2^6;
sbit wela=P2^7;
unsigned char i=100;
unsigned char j,k,temp,key;
unsigned char code table[]={0x3f,0x06,0x5b,0x4f,0x66,0x6d,0x7d,
                        0x07,0x7f,0x6f,0x77,0x7c,0x39,0x5e,0x79,0x71};
unsigned char date1,date2,date3;

void Delay_Us(int i)
{
	while(--i);
}
void delay(unsigned char m)
{
	unsigned char i;
 	while(m--)
	{
		i = 10;
		while(i--)
		{
			Delay_Us(125);
		}
	 	
	}
}
void init(void)				//串口初始化
{
    SCON=0x50;   //UART方式1:8位UART;   REN=1:允许接收 
    PCON=0x00;   //SMOD=0:波特率不加倍 
    TMOD=0x20;   //T1方式2,用于UART波特率 
    TH1=0xFD; 
    TL1=0xFD;   //UART波特率设置:FDFD，9600;FFFF,57600
    TR1=1;	 //允许T1计数 
    EA=1;
}

void send(unsigned char d)		  //发送一个字节的数据，形参d即为待发送数据。
{
	SBUF = d;
	while(!TI);		//发送完为1 
	TI = 0;
}

bit UART_Servo(unsigned char servonum,unsigned char angle)
{
  
  servonum = 64 + servonum;
    date1 = angle/100 + 48;
    date2 = (angle%100)/10 + 48;
    date3 = angle%10 + 48;
    send(0x24);//发送包头
	send(servonum);//发送舵机编号
	send(date1);//发送角度
	send(date2);//发送角度
	send(date3);//发送角度
	send(0x23);//发送包尾
	delay(100);
   	return(1);

}
void display(unsigned char num)
{
         P0=table[num];
         dula=1;
         dula=0;
         P0=0x00;
         wela=1;
         wela=0;
}

void main()
{
	init();
	while(1)
	{ 
		delay(1);
		UART_Servo(1,0);
		delay(1);
		UART_Servo(1,90); 
		delay(1);
		UART_Servo(1,180); 
		delay(1);
	}
}
