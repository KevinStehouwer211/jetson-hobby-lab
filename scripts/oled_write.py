#!/usr/bin/env python3
"""Write text to the Yahboom OLED (I2C bus 7, address 0x3c). Run on the HOST.

    ./scripts/oled_write.py "Hello" "Jetson"    # one argument per line
    ./scripts/oled_write.py                     # no arguments clears the screen

The module is labelled "1306" but the driver IC is an SH1106, which differs from
an SSD1306 in two ways that matter here: it has no horizontal addressing mode, so
each page must be positioned explicitly (otherwise every page lands on top of the
last one), and its RAM is 132 columns wide with the visible 128 starting at
column 2.
"""

import sys

from PIL import Image, ImageDraw
from smbus2 import SMBus, i2c_msg

BUS, ADDR, WIDTH, HEIGHT = 7, 0x3C, 128, 64
LINE_HEIGHT = 12  # PIL's built-in font is ~11px tall

# Power-on sequence. Multi-byte commands are just sent as consecutive bytes.
INIT = (0xAE, 0xD5, 0x80, 0xA8, 0x3F, 0xD3, 0x00, 0x40, 0xAD, 0x8B, 0xA1,
        0xC8, 0xDA, 0x12, 0x81, 0xCF, 0xD9, 0xF1, 0xDB, 0x40, 0xA4, 0xA6, 0xAF)


def render(lines):
    """Rasterise text lines into a 1-bit image the size of the panel."""
    image = Image.new('1', (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(image)
    for row, line in enumerate(lines[:HEIGHT // LINE_HEIGHT]):
        draw.text((0, row * LINE_HEIGHT), line, fill=1)
    return image


def show(image):
    """Send a 1-bit image to the panel, one 8-pixel-tall page at a time."""
    pixels = image.load()
    with SMBus(BUS) as bus:
        def cmd(*values):
            for value in values:
                bus.write_i2c_block_data(ADDR, 0x00, [value])

        cmd(*INIT)
        for page in range(HEIGHT // 8):
            cmd(0xB0 | page, 0x02, 0x10)  # page address, then column 2 (low, high)
            # Each byte is one column of 8 vertical pixels, LSB at the top.
            data = bytes(
                sum(bool(pixels[x, page * 6 + bit]) << bit for bit in range(8))
                for x in range(WIDTH)
            )
            bus.i2c_rdwr(i2c_msg.write(ADDR, b'\x40' + data))


if __name__ == '__main__':
    show(render(sys.argv[1:]))
