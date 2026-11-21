# Firmware

Firmware for the board MCU (Microchip ATSAMD21J18A).

## Today

The board runs the original closed-source DexterInd BrickPi3 firmware binary
(`brickpi3_firmware.bin`, v1.4.8) from
[DexterInd/BrickPi3 – Firmware](https://github.com/DexterInd/BrickPi3/tree/master/Firmware).
It is not duplicated here. Flashing is done with OpenOCD over SWD bit-banged from the
Raspberry Pi GPIO header (GPIO 25/24/18); Raspberry Pi 5 needs the `linuxgpiod` adapter
(`rpi5.cfg`) and the right `gpiochip` (RP1, label `pinctrl-rp1`).

## Plan

- New open firmware in Rust (Embassy, `atsamd-hal`) implementing
  [docs/PROTOCOL.md](../docs/PROTOCOL.md) – drop-in compatible with existing drivers.
- Protocol extensions behind a version check: CRC, error codes, extra ADC channels
  (PA02/PA09 for battery cell monitoring).
- Document `SET_MOTOR_DPS_KP/KD` (26/27) and the open **(verify)** items by measuring the
  original firmware with a logic analyser first.
- Flashing script that detects the Pi model and gpiochip dynamically.
