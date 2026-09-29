# Yahboom 24-Channel Servo Driver Board — Firmware Rebuild

Vendor source for the Yahboom 24-channel servo control board (STM32F103RCT6), plus
the replacement firmware image built from it.

**Why this folder exists:** the board as shipped would not accept servo commands over
its USB-C port — the firmware echoed that UART's traffic back instead of parsing it. A
one-line patch to the vendor source, rebuilt and flashed, fixed that. The board is now
driven from the Jetson over plain USB.

Working configuration after the reflash:

| | |
|---|---|
| Port | `/dev/ttyUSB0` (onboard CH340, USB-C) |
| Baud | 115200, 8N1 |
| Protocol | `$<channel><angle>#` e.g. `$A090#` |
| Host script | [ServoSimple.py](../python_scripts/servo/ServoSimple.py) |
| Flashed image | [stree_free_ii.hex](stree_free_ii.hex) (70505 bytes, md5 `01e7eb3a9255c80079b01f7eabdb5e01`) |

---

## The problem

Servos would not move, while every sign pointed to a healthy setup:

- The Jetson opened the port and wrote without error.
- The board echoed back every byte sent to it.
- The `7V4` servo-rail LED was lit, so the board was properly powered.

The echo was the misleading part. The board echoes **everything** — `$A090#`, `ZZZZZZ`,
`hello!`, raw null bytes — so a returned frame only proves the link is alive. It says
nothing about whether the command was parsed. The vendor manual describes this as
intended behaviour: *"the servo control board will immediately return the received
information, that is, what is sent back to what is sent back."*

Two other things were ruled out along the way, both worth knowing:

- **Wrong device.** The vendor's sample script opens `/dev/ttyTHS1`, the Jetson's TX3/RX3
  header pins. That UART exists and accepts writes silently, so the script looks like it
  is working while the bytes go out the 40-pin header. Driving the board over USB means
  `/dev/ttyUSB0` instead.
- **Wrong baud.** The 9600 in the vendor docs applies to the `TXD3/RXD3` pin header.
  The USB-C port runs at 115200. Sweeping baud rates made this obvious: only at 115200
  did the echo come back intact, since a real UART re-clocks the reply at its own fixed
  rate while a plain wire loopback would have echoed cleanly at every rate.

With port and baud correct, frames still did not move servos — which left the firmware.

## Root cause

The board has three UARTs. From
`24-ChannelServoDriveBoard_Code/STM32_Code_Additional/2DOF_No handle/BSP/bsp.c`:

```c
USART1_init(115200); // debug serial  -> USB-C (PA9/PA10)
USART3_init(9600);   // host comms    -> RXD/TXD pin header (PC10/PC11, partial remap)
UART5_init(9600);    // Bluetooth module
```

The USART3 and UART5 interrupt handlers in `BSP/bsp_usart.c` both pass received bytes to
`deal_bluetooth()`, the `$...#` servo parser in `APP/user_bluetooth.c`. **USART1 did not.**
In the vendor source it echoed the byte straight back out and did nothing else:

```c
void USART1_IRQHandler(void)
{
    uint8_t Rx1_Temp = 0;
    if (USART_GetITStatus(USART1, USART_IT_RXNE) != RESET)
    {
        Rx1_Temp = USART_ReceiveData(USART1);
        USART1_Send_U8(Rx1_Temp);   // echo only — never reaches the parser
    }
}
```

That single line is the whole bug, and it explains the symptom exactly: USB-C was wired
to a UART whose only job was to repeat back whatever it heard. Every frame looked
accepted and none of them ever reached a servo.

## The fix

One line, in `2DOF_No handle/BSP/bsp_usart.c:79` — route USART1's received bytes into the
servo parser instead of back out the wire:

```c
-       USART1_Send_U8(Rx1_Temp);   // echo the byte back
+       deal_bluetooth(Rx1_Temp);   // feed the byte to the $...# parser
```

This edit is committed in this repository. The untouched vendor original survives in the
sibling `2DOF_Handle` project, so the change can always be recovered with a diff:

```bash
cd "24-ChannelServoDriveBoard_Code/STM32_Code_Additional"
diff "2DOF_No handle/BSP/bsp_usart.c" "2DOF_Handle/BSP/bsp_usart.c"
# 79c79
# <     deal_bluetooth(Rx1_Temp);
# ---
# >     USART1_Send_U8(Rx1_Temp);
```

After the edit all three UARTs feed the same parser, so the board accepts identical
`$A090#` framing over USB-C at 115200, the pin header at 9600, or Bluetooth.

## Rebuilding

The project is `STM32_Code_Additional/2DOF_No handle/USER/steer_freeII.uvprojx`
(target `steer_free_II`, device STM32F103RC, output `stree_free_ii`).

**Toolchain: Keil uVision 5 with ARM Compiler 5.** This is the one real gotcha. The
project is pinned to AC5:

```xml
<pCCUsed>5060960::V5.06 update 7 (build 960)::.\ARMCC</pCCUsed>
<uAC6>0</uAC6>
```

MDK-ARM v5 ships with ARM Compiler 6 by default and AC6 will not build this source.
ARM Compiler 5.06 update 7 must be installed alongside it as a separate download from
Arm, and selected under *Options for Target → Target → ARM Compiler*. A 1-month
evaluation licence from Arm is enough to produce the image.

Build steps:

1. Open `steer_freeII.uvprojx` in Keil uVision 5.
2. Confirm ARM Compiler V5.06 update 7 is the selected compiler for the target.
3. Build. The image lands in `2DOF_No handle/OBJ/stree_free_ii.hex`.

The resulting image is committed at the root of this folder as
[stree_free_ii.hex](stree_free_ii.hex), so the board can be reflashed without a Keil
licence on hand.

## Flashing

Flash the built `.hex` to the STM32F103RCT6. The board provides `BOOT0` and `RESET`
buttons next to the USB-C port for serial bootloader entry.

## Verifying

```bash
python3 ../python_scripts/servo/ServoSimple.py
```

Servos on `S1` and `S2` should move to 90°. If frames go out but nothing moves, check in
this order: the `7V4` LED (servo rail powered, slide switch `ON`, 6–8.4V into the XT60 or
the blue screw terminal), then servo plug orientation — each `S` header is
**yellow = signal, red = VCC, black = GND**, with yellow nearest the `S1`/`S2` label.

## Protocol reference

```
$<channel><angle>#      e.g.  $A090#  = channel S1 to 90°
```

- **channel** — a single letter `A`–`X`, mapping to `S1`–`S24`.
- **angle** — exactly three digits, zero-padded, `000`–`180`. Two digits will not parse;
  the firmware indexes `rxbuff[2..4]` by fixed offset.

The parser clamps out-of-range angles to 0 or 180 and maps the channel to one of three
groups of eight (`Angle_J[group][column]`), which is how the 24 channels are organised
internally.

## Note on the source tree

Apart from the one-line change documented above, this tree is the vendor source as
downloaded. The build itself was done on a Windows machine, so `OBJ/stree_free_ii.hex`
inside the project folder is still the vendor's prebuilt image, **not** the one running on
the board. The image that was actually flashed is the copy at the root of this folder.
