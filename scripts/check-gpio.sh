#!/usr/bin/env bash
#
# check-gpio.sh — sanity-check Jetson GPIO/I2C from the *HOST*.
#
# Unlike check-env.sh (which runs inside a container), this must run on the host:
# it needs Jetson.GPIO and direct access to /dev/gpiochip* and /dev/i2c-*.
#
#   ~/jetson-hobby-lab/scripts/check-gpio.sh              # read-only, always safe
#   ~/jetson-hobby-lab/scripts/check-gpio.sh --loopback 18 16   # DRIVES a pin, prompts first
#
# Exit code is non-zero if any required check fails.

# Don't use `set -e`: we want every check to run and report, not stop on the first failure.

PASS=0
FAIL=0
SKIP=0

green() { printf '\033[0;32m%s\033[0m\n' "$1"; }
red()   { printf '\033[0;31m%s\033[0m\n' "$1"; }
yellow(){ printf '\033[0;33m%s\033[0m\n' "$1"; }

# check <label> <command...> — runs the command, prints PASS/FAIL with its output.
check() {
    local label="$1"; shift
    local out
    if out=$("$@" 2>&1); then
        green "  [PASS] $label"
        [ -n "$out" ] && printf '         %s\n' "$(echo "$out" | head -n 2)"
        PASS=$((PASS + 1))
    else
        red "  [FAIL] $label"
        [ -n "$out" ] && printf '         %s\n' "$(echo "$out" | head -n 2)"
        FAIL=$((FAIL + 1))
    fi
}

have() { command -v "$1" >/dev/null 2>&1; }

LOOPBACK_OUT=""
LOOPBACK_IN=""
if [ "$1" = "--loopback" ]; then
    LOOPBACK_OUT="$2"
    LOOPBACK_IN="$3"
    if [ -z "$LOOPBACK_OUT" ] || [ -z "$LOOPBACK_IN" ]; then
        red "usage: $0 --loopback <out_pin> <in_pin>"
        exit 2
    fi
fi

echo "=============================================="
echo " Jetson host GPIO / I2C check"
echo "=============================================="

echo ""
echo "Library:"
if have python3; then
    # GPIO.model proves the device-tree match worked; a wrong/absent match means
    # every pin number below would map to the wrong kernel line.
    check "Jetson.GPIO imports and detects the board" \
        python3 -c "import Jetson.GPIO as G; print('Jetson.GPIO', G.VERSION, '/ model:', G.model)"
else
    yellow "  [SKIP] python3 not found"
    SKIP=$((SKIP + 1))
fi

echo ""
echo "Permissions:"
# The library is useless without these; they're the usual cause of a working
# `sudo python3` and a failing plain one.
if id -nG | tr ' ' '\n' | grep -qx gpio; then
    green "  [PASS] user is in the 'gpio' group"
    PASS=$((PASS + 1))
else
    red "  [FAIL] user not in 'gpio' group — run: sudo usermod -aG gpio \$USER, then re-login"
    FAIL=$((FAIL + 1))
fi
if [ -f /etc/udev/rules.d/99-gpio.rules ]; then
    green "  [PASS] 99-gpio.rules installed"
    PASS=$((PASS + 1))
else
    yellow "  [SKIP] 99-gpio.rules absent — /dev/gpiochip* ownership may not survive reboot"
    SKIP=$((SKIP + 1))
fi
for chip in /dev/gpiochip0 /dev/gpiochip1; do
    if [ -r "$chip" ] && [ -w "$chip" ]; then
        green "  [PASS] $chip readable+writable as $(id -un)"
        PASS=$((PASS + 1))
    else
        red "  [FAIL] $chip not accessible: $(ls -l "$chip" 2>&1)"
        FAIL=$((FAIL + 1))
    fi
done

echo ""
echo "Pin survey (read-only — inputs are high-impedance and drive nothing):"
if have python3; then
    python3 - <<'PYEOF'
import sys
try:
    import Jetson.GPIO as GPIO
except ImportError as e:
    print(f'  [SKIP] Jetson.GPIO not importable: {e}')
    sys.exit(0)

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BOARD)

# The 22 GPIO-capable pins on the 40-pin header, with their default pinmux
# function. Pins 3/5 (I2C) and 8/10 (UART) are omitted: they're not GPIO here.
PINS = {
    7: 'GPIO09', 11: 'UART1_RTS', 12: 'I2S0_SCLK', 13: 'GPIO11',
    15: 'GPIO12/PWM', 16: 'GPIO08', 18: 'GPIO07', 19: 'SPI1_MOSI',
    21: 'SPI1_MISO', 22: 'GPIO17', 23: 'SPI1_SCLK', 24: 'SPI1_CS0',
    26: 'SPI1_CS1', 29: 'GPIO01', 31: 'GPIO11', 32: 'GPIO07/PWM',
    33: 'GPIO13/PWM', 35: 'I2S0_FS', 36: 'UART1_CTS', 37: 'SPI1_MISO',
    38: 'I2S0_SDIN', 40: 'I2S0_SDOUT',
}

high, low, busy = [], [], []
print(f"    {'PIN':>4}  {'FUNCTION':<12} STATE")
for pin, func in sorted(PINS.items()):
    try:
        GPIO.setup(pin, GPIO.IN)
        val = GPIO.input(pin)
        state = 'HIGH' if val else 'low'
        (high if val else low).append(pin)
    except Exception as exc:
        # EBUSY here means another process (or a kernel driver) holds the line.
        state = f'BUSY ({type(exc).__name__})'
        busy.append(pin)
    print(f"    {pin:>4}  {func:<12} {state}")
GPIO.cleanup()

print()
print(f"    HIGH (driven or pulled up externally): {high or 'none'}")
print(f"    low  (floating or grounded)          : {low or 'none'}")
print(f"    BUSY (claimed by a driver/process)   : {busy or 'none'}")
print()
print("    NOTE: 'low' is ambiguous. A floating input and a pin held low by an")
print("    attached board read identically. Do NOT infer a pin is unconnected.")
PYEOF
    PASS=$((PASS + 1))
else
    yellow "  [SKIP] python3 not found"
    SKIP=$((SKIP + 1))
fi

echo ""
echo "I2C buses:"
if have i2cdetect; then
    # Header I2C on Orin Nano is bus 7 (pins 3/5) and bus 1 (pins 27/28).
    # -r uses SMBus read-byte probing, which is the safe mode; -y skips the prompt.
    # 'UU' entries are addresses already claimed by a kernel driver.
    for bus in 7 1; do
        if [ -e "/dev/i2c-$bus" ]; then
            # Strip the header row and each row's "NN:" label before scraping
            # addresses, or the labels get mistaken for detected devices.
            scan=$(timeout 15 i2cdetect -y -r "$bus" 2>/dev/null | tail -n +2 | sed 's/^[0-9a-f]*://')
            found=$(echo "$scan" | grep -oE '\b[0-9a-f]{2}\b' | tr '\n' ' ')
            claimed=$(echo "$scan" | grep -oc 'UU')
            if [ -n "$found" ]; then
                green "  [PASS] bus $bus: devices at $found(+${claimed:-0} kernel-claimed 'UU')"
            else
                yellow "  [INFO] bus $bus: no free devices responded (${claimed:-0} kernel-claimed 'UU')"
            fi
            PASS=$((PASS + 1))
        else
            yellow "  [SKIP] /dev/i2c-$bus does not exist"
            SKIP=$((SKIP + 1))
        fi
    done
else
    yellow "  [SKIP] i2cdetect not installed (apt install i2c-tools)"
    SKIP=$((SKIP + 1))
fi

# ---------------------------------------------------------------------------
# Optional loopback test. This DRIVES a pin, so it is opt-in and prompts first:
# if an expansion board also drives that line, both drivers can be damaged.
# ---------------------------------------------------------------------------
if [ -n "$LOOPBACK_OUT" ]; then
    echo ""
    echo "Loopback test (pin $LOOPBACK_OUT -> pin $LOOPBACK_IN):"
    red   "  WARNING: this DRIVES pin $LOOPBACK_OUT as an output."
    yellow "  Only continue if you are certain nothing else drives that pin."
    yellow "  An expansion board fighting the line can damage the Jetson AND the board."
    yellow "  A jumper wire from pin $LOOPBACK_OUT to pin $LOOPBACK_IN is required for a PASS."
    printf "  Type 'yes' to continue: "
    read -r reply
    if [ "$reply" != "yes" ]; then
        yellow "  [SKIP] loopback declined"
        SKIP=$((SKIP + 1))
    else
        check "loopback $LOOPBACK_OUT -> $LOOPBACK_IN" python3 - "$LOOPBACK_OUT" "$LOOPBACK_IN" <<'PYEOF'
import sys
import time

import Jetson.GPIO as GPIO

out_pin, in_pin = int(sys.argv[1]), int(sys.argv[2])
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BOARD)
GPIO.setup(out_pin, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(in_pin, GPIO.IN)
try:
    results = []
    for level, expected in ((GPIO.HIGH, 1), (GPIO.LOW, 0)):
        GPIO.output(out_pin, level)
        time.sleep(0.05)          # let the line settle before sampling
        results.append(GPIO.input(in_pin) == expected)
    if all(results):
        print(f'pin {out_pin} drove pin {in_pin} both HIGH and LOW')
    else:
        print(f'readback mismatch {results} — jumper missing, or the line is contended')
        sys.exit(1)
finally:
    GPIO.cleanup()
PYEOF
    fi
fi

echo ""
echo "=============================================="
printf " Result: "
green "$PASS passed"
[ "$FAIL" -gt 0 ] && red "         $FAIL failed"
[ "$SKIP" -gt 0 ] && yellow "         $SKIP skipped"
echo "=============================================="

[ "$FAIL" -eq 0 ]
