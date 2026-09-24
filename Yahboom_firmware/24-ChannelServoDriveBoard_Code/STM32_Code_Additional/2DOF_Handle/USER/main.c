#include "AllHeader.h"

u8 grop = 0;
float version = 1.1;


int main(void)
{	
	u8 Dnum;
	u8 Doup;

	//舵机角度初始化
	for(Doup = 0;Doup <GROUP_NUM;Doup++)
	{  
		for(Dnum = 0;Dnum <DUOJI_NUM;Dnum++)
		{
			Angle_J[Doup][Dnum] = 90;
		}
		
	}
	
	bsp_init();//再进行硬件初始化 
	
	while (1)
	{
		dectect_beep();//检测电压
		
		void_jutce(); //检测电流

#if	PS_TWO
		user_douji();	//手柄控制
#endif		
		if(Key1_State(1)==1)//按下只生效一次
		{
			grop++;
			if(grop>2)
			{
				grop = 0; 
			}
				
		}
		
	}
 								    
}


