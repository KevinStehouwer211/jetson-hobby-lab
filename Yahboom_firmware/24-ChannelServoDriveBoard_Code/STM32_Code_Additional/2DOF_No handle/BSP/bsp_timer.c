/**
* @par Copyright (C): 2010-2019, Shenzhen Yahboom Tech
* @file         bsp_timer.h	
* @author       
* @version      V1.0
* @date         
* @brief        定时器
* @details      
* @par History  见如下说明
*                 
* version:		
*/

#include "AllHeader.h"



/**
* Function       TIM1_Int_Init
* @author        
* @date             
* @brief         定时器1初始化接口
* @param[in]     arr：自动重装值。psc：时钟预分频数
* @param[out]    void
* @retval        void
* @par History   这里时钟选择为APB1的2倍，而APB1为36M
*/
void TIM1_Int_Init(u16 arr,u16 psc)
{
    TIM_TimeBaseInitTypeDef  TIM_TimeBaseStructure;
	NVIC_InitTypeDef NVIC_InitStructure;

	RCC_APB2PeriphClockCmd(RCC_APB2Periph_TIM1, ENABLE); //时钟使能
	
	//定时器TIM1初始化
	TIM_TimeBaseStructure.TIM_Period = arr; //设置在下一个更新事件装入活动的自动重装载寄存器周期的值	
	TIM_TimeBaseStructure.TIM_Prescaler = (psc-1); //设置用来作为TIMx时钟频率除数的预分频值
	TIM_TimeBaseStructure.TIM_ClockDivision = TIM_CKD_DIV1; //设置时钟分割:TDTS = Tck_tim   //36Mhz
	TIM_TimeBaseStructure.TIM_CounterMode = TIM_CounterMode_Up;  //TIM向上计数模式
	TIM_TimeBaseStructure.TIM_RepetitionCounter = 0;    //重复计数关闭
	TIM_TimeBaseInit(TIM1, &TIM_TimeBaseStructure); //根据指定的参数初始化TIMx的时间基数单位
 
	TIM_ITConfig(TIM1, TIM_IT_Update, ENABLE ); //使能指定的TIM1中断,允许更新中断

	//中断优先级NVIC设置
	NVIC_InitStructure.NVIC_IRQChannel = TIM1_UP_IRQn;  //TIM1中断
	NVIC_InitStructure.NVIC_IRQChannelPreemptionPriority = 0;  //先占优先级0级
	NVIC_InitStructure.NVIC_IRQChannelSubPriority = 3;  //从优先级3级
	NVIC_InitStructure.NVIC_IRQChannelCmd = ENABLE; //IRQ通道被使能
	NVIC_Init(&NVIC_InitStructure);  //初始化NVIC寄存器


	TIM_Cmd(TIM1, ENABLE);  //使能TIMx					 
}
/**
* Function       TIM1_Int_Init
* @author        
* @date             
* @brief         定时器1中断服务程序: 主要控制6路舵机运行
* @param[in]     arr：自动重装值。psc：时钟预分频数
* @param[out]    void
* @retval        void
* @par History   这里时钟选择为APB1的2倍，而APB1为36M
*/
int num = 0;

/* Advance every channel one 20ms frame toward its target, then refresh the
 * pulse table the ISR compares against. Runs once per frame, not per tick. */
static void servo_frame_update(void)
{
	u8 g, c;
	int step;

	if (Servo_Speed == 0)
	{
		step = 180 * 16;                      /* no rate limit: arrive this frame */
	}
	else
	{
		step = ((int)Servo_Speed * 16) / 50;  /* deg/s -> 1/16 deg per 20ms frame */
		if (step < 1) step = 1;               /* never stall at very slow rates */
	}

	for (g = 0; g < GROUP_NUM; g++)
	{
		for (c = 0; c < DUOJI_NUM; c++)
		{
			int target = Angle_J[g][c] * 16;
			int cur    = Angle_Q[g][c];

			if (cur < target)
			{
				cur += step;
				if (cur > target) cur = target;
			}
			else if (cur > target)
			{
				cur -= step;
				if (cur < target) cur = target;
			}
			Angle_Q[g][c] = cur;

			/* pulse us = angle*11 + 500, angle = cur/16 */
			Pulse_T[g][c] = (u16)(((cur * 11) / 16 + 500) / SERVO_TICK_US);
		}
	}
}

void TIM1_UP_IRQHandler(void)   //TIM1中断
{
	if (TIM_GetITStatus(TIM1, TIM_IT_Update) != RESET)  //检查TIM1更新中断发生与否
	{
		TIM_ClearITPendingBit(TIM1, TIM_IT_Update);  //清除TIM1更新中断标志 
		num++;
	

		#ifdef USE_SERVO_J1
		if(num <= Pulse_T[0][0])
		{
			GPIO_SetBits(Servo_J1_PORT, Servo_J1_PIN );		//将舵机接口电平置高
		}
		else
		{
			GPIO_ResetBits(Servo_J1_PORT, Servo_J1_PIN );		//将舵机接口电平置高
		}
		#endif	   	

		#ifdef USE_SERVO_J2
		if(num <= Pulse_T[0][1])
		{
			GPIO_SetBits(Servo_J2_PORT, Servo_J2_PIN );		//将舵机接口电平置高
		}
		else
		{
			GPIO_ResetBits(Servo_J2_PORT, Servo_J2_PIN );		//将舵机接口电平置高
		}
		#endif

		#ifdef USE_SERVO_J3

		if(num <= Pulse_T[0][2])
		{
			GPIO_SetBits(Servo_J3_PORT, Servo_J3_PIN );		//将舵机接口电平置高
		}
		else
		{
			GPIO_ResetBits(Servo_J3_PORT, Servo_J3_PIN );		//将舵机接口电平置高
		}
		#endif

		#ifdef USE_SERVO_J4
		if(num <= Pulse_T[0][3])
		{
			GPIO_SetBits(Servo_J4_PORT, Servo_J4_PIN );		//将舵机接口电平置高
		}
		else
		{
			GPIO_ResetBits(Servo_J4_PORT, Servo_J4_PIN );		//将舵机接口电平置高
		}
		#endif

		#ifdef USE_SERVO_J5
		if(num <= Pulse_T[0][4])
		{
			GPIO_SetBits(Servo_J5_PORT, Servo_J5_PIN );		//将舵机接口电平置高
		}
		else
		{
			GPIO_ResetBits(Servo_J5_PORT, Servo_J5_PIN );		//将舵机接口电平置高
		}
		#endif

		#ifdef USE_SERVO_J6
		if(num <= Pulse_T[0][5])
		{
			GPIO_SetBits(Servo_J6_PORT, Servo_J6_PIN );		//将舵机接口电平置高
		}
		else
		{
			GPIO_ResetBits(Servo_J6_PORT, Servo_J6_PIN );		//将舵机接口电平置高
		}
		#endif
		
		#ifdef USE_SERVO_J7
		if(num <= Pulse_T[0][6])
		{
			GPIO_SetBits(Servo_J7_PORT, Servo_J7_PIN );		//将舵机接口电平置高
		}
		else
		{
			GPIO_ResetBits(Servo_J7_PORT, Servo_J7_PIN );		//将舵机接口电平置高
		}
		#endif
		
		#ifdef USE_SERVO_J8
		if(num <= Pulse_T[0][7])
		{
			GPIO_SetBits(Servo_J8_PORT, Servo_J8_PIN );		//将舵机接口电平置高
		}
		else
		{
			GPIO_ResetBits(Servo_J8_PORT, Servo_J8_PIN );		//将舵机接口电平置高
		}
		#endif
		
		#ifdef USE_SERVO_J9
		if(num <= Pulse_T[1][0])
		{
			GPIO_SetBits(Servo_J9_PORT, Servo_J9_PIN );		//将舵机接口电平置高
		}
		else
		{
			GPIO_ResetBits(Servo_J9_PORT, Servo_J9_PIN );		//将舵机接口电平置高
		}
		#endif
		
		#ifdef USE_SERVO_J10
		if(num <= Pulse_T[1][1])
		{
			GPIO_SetBits(Servo_J10_PORT, Servo_J10_PIN );		//将舵机接口电平置高
		}
		else
		{
			GPIO_ResetBits(Servo_J10_PORT, Servo_J10_PIN );		//将舵机接口电平置高
		}
		#endif
		
		#ifdef USE_SERVO_J11
		if(num <= Pulse_T[1][2])
		{
			GPIO_SetBits(Servo_J11_PORT, Servo_J11_PIN );		//将舵机接口电平置高
		}
		else
		{
			GPIO_ResetBits(Servo_J11_PORT, Servo_J11_PIN );		//将舵机接口电平置高
		}
		#endif
		#ifdef USE_SERVO_J12
		if(num <= Pulse_T[1][3])
		{
			GPIO_SetBits(Servo_J12_PORT, Servo_J12_PIN );		//将舵机接口电平置高
		}
		else
		{
			GPIO_ResetBits(Servo_J12_PORT, Servo_J12_PIN );		//将舵机接口电平置高
		}
		#endif
		
		#ifdef USE_SERVO_J13
		if(num <= Pulse_T[1][4])
		{
			GPIO_SetBits(Servo_J13_PORT, Servo_J13_PIN );		//将舵机接口电平置高
		}
		else
		{
			GPIO_ResetBits(Servo_J13_PORT, Servo_J13_PIN );		//将舵机接口电平置高
		}
		#endif
		#ifdef USE_SERVO_J14
		if(num <= Pulse_T[1][5])
		{
			GPIO_SetBits(Servo_J14_PORT, Servo_J14_PIN );		//将舵机接口电平置高
		}
		else
		{
			GPIO_ResetBits(Servo_J14_PORT, Servo_J14_PIN );		//将舵机接口电平置高
		}
		#endif
		
		#ifdef USE_SERVO_J15
		if(num <= Pulse_T[1][6])
		{
			GPIO_SetBits(Servo_J15_PORT, Servo_J15_PIN );		//将舵机接口电平置高
		}
		else
		{
			GPIO_ResetBits(Servo_J15_PORT, Servo_J15_PIN );		//将舵机接口电平置高
		}
		#endif	
		
		#ifdef USE_SERVO_J16
		if(num <= Pulse_T[1][7])
		{
			GPIO_SetBits(Servo_J16_PORT, Servo_J16_PIN );		//将舵机接口电平置高
		}
		else
		{
			GPIO_ResetBits(Servo_J16_PORT, Servo_J16_PIN );		//将舵机接口电平置高
		}
		#endif	
		
		#ifdef USE_SERVO_J17
		if(num <= Pulse_T[2][0])
		{
			GPIO_SetBits(Servo_J17_PORT, Servo_J17_PIN );		//将舵机接口电平置高
		}
		else
		{
			GPIO_ResetBits(Servo_J17_PORT, Servo_J17_PIN );		//将舵机接口电平置高
		}
		#endif	
				
		#ifdef USE_SERVO_J18
		if(num <= Pulse_T[2][1])
		{
			GPIO_SetBits(Servo_J18_PORT, Servo_J18_PIN );		//将舵机接口电平置高
		}
		else
		{
			GPIO_ResetBits(Servo_J18_PORT, Servo_J18_PIN );		//将舵机接口电平置高
		}
		#endif	
				
						
		#ifdef USE_SERVO_J19
		if(num <= Pulse_T[2][2])
		{
			GPIO_SetBits(Servo_J19_PORT, Servo_J19_PIN );		//将舵机接口电平置高
		}
		else
		{
			GPIO_ResetBits(Servo_J19_PORT, Servo_J19_PIN );		//将舵机接口电平置高
		}
		#endif	
						
		#ifdef USE_SERVO_J20
		if(num <= Pulse_T[2][3])
		{
			GPIO_SetBits(Servo_J20_PORT, Servo_J20_PIN );		//将舵机接口电平置高
		}
		else
		{
			GPIO_ResetBits(Servo_J20_PORT, Servo_J20_PIN );		//将舵机接口电平置高
		}
		#endif	
						
		#ifdef USE_SERVO_J21
		if(num <= Pulse_T[2][4])
		{
			GPIO_SetBits(Servo_J21_PORT, Servo_J21_PIN );		//将舵机接口电平置高
		}
		else
		{
			GPIO_ResetBits(Servo_J21_PORT, Servo_J21_PIN );		//将舵机接口电平置高
		}
		#endif

		#ifdef USE_SERVO_J22
		if(num <= Pulse_T[2][5])
		{
			GPIO_SetBits(Servo_J22_PORT, Servo_J22_PIN );		//将舵机接口电平置高
		}
		else
		{
			GPIO_ResetBits(Servo_J22_PORT, Servo_J22_PIN );		//将舵机接口电平置高
		}
		#endif

		#ifdef USE_SERVO_J23
		if(num <= Pulse_T[2][6])
		{
			GPIO_SetBits(Servo_J23_PORT, Servo_J23_PIN );		//将舵机接口电平置高
		}
		else
		{
			GPIO_ResetBits(Servo_J23_PORT, Servo_J23_PIN );		//将舵机接口电平置高
		}
		#endif		
		
		#ifdef USE_SERVO_J24
		if(num <= Pulse_T[2][7])
		{
			GPIO_SetBits(Servo_J24_PORT, Servo_J24_PIN );		//将舵机接口电平置高
		}
		else
		{
			GPIO_ResetBits(Servo_J24_PORT, Servo_J24_PIN );		//将舵机接口电平置高
		}
		#endif	

		if(num >= SERVO_FRAME_TICKS) //SERVO_FRAME_TICKS * SERVO_TICK_US = 20ms  20ms一个周期
		{
			num = 0;
			servo_frame_update();
		}
		
	}
}
