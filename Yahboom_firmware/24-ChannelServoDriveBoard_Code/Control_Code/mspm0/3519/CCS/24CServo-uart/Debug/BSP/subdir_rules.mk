################################################################################
# Automatically-generated file. Do not edit!
################################################################################

SHELL = cmd.exe

# Each subdirectory must supply rules for building sources it contributes
BSP/%.o: ../BSP/%.c $(GEN_OPTS) | $(GEN_FILES) $(GEN_MISC_FILES)
	@echo 'Building file: "$<"'
	@echo 'Invoking: Arm Compiler'
	"D:/ti/ccstheia151/ccs/tools/compiler/ti-cgt-armllvm_4.0.0.LTS/bin/tiarmclang.exe" -c @"syscfg/device.opt"  -march=thumbv6m -mcpu=cortex-m0plus -mfloat-abi=soft -mlittle-endian -mthumb -O2 -I"D:/CCS/24CServo-uart" -I"D:/CCS/24CServo-uart/Debug" -I"D:/ti/mspm0_sdk_2_02_00_05/source/third_party/CMSIS/Core/Include" -I"D:/ti/mspm0_sdk_2_02_00_05/source" -I"D:/CCS/24CServo-uart/BSP" -gdwarf-3 -MMD -MP -MF"BSP/$(basename $(<F)).d_raw" -MT"$(@)" -I"D:/CCS/24CServo-uart/Debug/syscfg"  $(GEN_OPTS__FLAG) -o"$@" "$<"
	@echo 'Finished building: "$<"'
	@echo ' '


