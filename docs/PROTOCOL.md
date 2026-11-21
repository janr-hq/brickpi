# BrickPi3 SPI protocol

Reference description of the protocol spoken between the Raspberry Pi (SPI master) and the
board MCU (ATSAMD21J18A, SPI slave). Derived from the original DexterInd Python driver
`Software/Python/brickpi3.py` (firmware 1.4.x, MIT, © 2017 Dexter Industries) and cross-checked
with the C++ and Rust drivers. Items marked **(verify)** have not been confirmed on hardware
(logic analyser) yet.

## Transport

| Parameter | Value |
| --- | --- |
| Device | `/dev/spidev0.1` (SPI0, chip select CE1) |
| Clock | 500 kHz |
| Mode | 0 (CPOL = 0, CPHA = 0), MSB first |
| Word | 8 bit |
| Chip select | asserted for the whole frame (`xfer2`) |
| Max frame length | 29 bytes |
| Byte order | big-endian for all multi-byte values |

Board side: SPI slave on SERCOM3 (PA16–PA19, DIPO = 0, DOPO = 2).

## Frame format

Every transaction is a single full-duplex SPI frame:

```text
TX: [ADDR] [TYPE] [P0] [P1] ... [Pn]
RX: [ ?  ] [ ?  ] [ ? ] [0xA5] [D0] [D1] ... [Dn]
     0      1      2     3      4    5
```

- `ADDR` – board address, 1–255, default **1**. Address **0** is a broadcast used only by
  `SET_ADDRESS` (stacking several boards on one Pi).
- `TYPE` – message type (table below).
- Write messages: parameters follow `TYPE`; the reply is ignored.
- Read messages: the master clocks zero bytes; the reply is valid only if `RX[3] == 0xA5`,
  data starts at `RX[4]`. Content of `RX[0..2]` is undefined **(verify)**.
- There is no checksum, no retry and no timeout. A missing `0xA5` is the only error signal
  (the driver raises `IOError("No SPI response")`).

### Port masks

Motor and sensor ports are bit masks. Write messages accept several ports at once (OR the
bits); read messages use one port per message type.

| Port | Mask |
| --- | --- |
| `PORT_1` / `PORT_A` | `0x01` |
| `PORT_2` / `PORT_B` | `0x02` |
| `PORT_3` / `PORT_C` | `0x04` |
| `PORT_4` / `PORT_D` | `0x08` |

## Message types

`len` = total frame length in bytes (TX and RX have the same length). Offsets are frame byte
indices. `u8/u16/u32` unsigned, `i8/i16/i32` signed two's complement, all big-endian.

| # | Name | Dir | len | Request bytes (after `ADDR`, `TYPE`) | Response (`RX[3] = 0xA5`) |
| --- | --- | --- | --- | --- | --- |
| 0 | `NONE` | – | – | unused | – |
| 1 | `GET_MANUFACTURER` | R | 24 | 22 × `0x00` | `[4..23]` ASCII, NUL-terminated, max 20 chars – `"Dexter Industries"` |
| 2 | `GET_NAME` | R | 24 | 22 × `0x00` | `[4..23]` ASCII board name – `"BrickPi3"` |
| 3 | `GET_HARDWARE_VERSION` | R | 8 | 6 × `0x00` | `[4..7]` u32 = major·10⁶ + minor·10³ + patch |
| 4 | `GET_FIRMWARE_VERSION` | R | 8 | 6 × `0x00` | `[4..7]` u32, same encoding; driver requires `1.4.x` |
| 5 | `GET_ID` | R | 20 | 18 × `0x00` | `[4..19]` 16-byte serial number (printed as 32 hex chars) |
| 6 | `SET_LED` | W | 3 | `[2]` i8 brightness 0–100 %, `-1` (`0xFF`) = firmware controls LED | – |
| 7 | `GET_VOLTAGE_3V3` | R | 6 | 4 × `0x00` | `[4..5]` u16 mV |
| 8 | `GET_VOLTAGE_5V` | R | 6 | 4 × `0x00` | `[4..5]` u16 mV |
| 9 | `GET_VOLTAGE_9V` | R | 6 | 4 × `0x00` | `[4..5]` u16 mV |
| 10 | `GET_VOLTAGE_VCC` | R | 6 | 4 × `0x00` | `[4..5]` u16 mV (battery) |
| 11 | `SET_ADDRESS` | W | 19 | sent with `ADDR = 0`; `[2]` u8 new address 1–255, `[3..18]` 16-byte board ID (all zeros = any board **(verify)**) | – |
| 12 | `SET_SENSOR_TYPE` | W | 4–29 | `[2]` port mask, `[3]` sensor type, then type-specific parameters – see [below](#set_sensor_type-12) | – |
| 13 | `GET_SENSOR_1` | R | 6–22 | zeros, length depends on configured type | see [below](#get_sensor_n-1316) |
| 14 | `GET_SENSOR_2` | R | 6–22 | as 13 | as 13 |
| 15 | `GET_SENSOR_3` | R | 6–22 | as 13 | as 13 |
| 16 | `GET_SENSOR_4` | R | 6–22 | as 13 | as 13 |
| 17 | `I2C_TRANSACT_1` | W | 5–21 | `[2]` I2C address (8-bit form, bits 1–7), `[3]` u8 bytes to read, `[4]` u8 bytes to write *n* ≤ 16, `[5..]` *n* bytes | – (result via `GET_SENSOR_1`) |
| 18 | `I2C_TRANSACT_2` | W | 5–21 | as 17 | – (via `GET_SENSOR_2`) |
| 19 | `I2C_TRANSACT_3` | W | 5–21 | as 17 | – (via `GET_SENSOR_3`) |
| 20 | `I2C_TRANSACT_4` | W | 5–21 | as 17 | – (via `GET_SENSOR_4`) |
| 21 | `SET_MOTOR_POWER` | W | 4 | `[2]` port mask, `[3]` i8 power −100…100 %, `-128` = float | – |
| 22 | `SET_MOTOR_POSITION` | W | 7 | `[2]` port mask, `[3..6]` i32 target position (degrees) | – |
| 23 | `SET_MOTOR_POSITION_KP` | W | 4 | `[2]` port mask, `[3]` u8 Kp (default 25) | – |
| 24 | `SET_MOTOR_POSITION_KD` | W | 4 | `[2]` port mask, `[3]` u8 Kd (default 70) | – |
| 25 | `SET_MOTOR_DPS` | W | 5 | `[2]` port mask, `[3..4]` i16 target speed (degrees/s) | – |
| 26 | `SET_MOTOR_DPS_KP` | W | ? | not used by any driver – format unknown, probably as 23 **(verify)** | – |
| 27 | `SET_MOTOR_DPS_KD` | W | ? | not used by any driver – format unknown, probably as 24 **(verify)** | – |
| 28 | `SET_MOTOR_LIMITS` | W | 6 | `[2]` port mask, `[3]` u8 power limit % (0 = none), `[4..5]` u16 speed limit dps (0 = none) | – |
| 29 | `OFFSET_MOTOR_ENCODER` | W | 7 | `[2]` port mask, `[3..6]` i32 offset subtracted from the encoder (offset = current position → zero) | – |
| 30 | `GET_MOTOR_A_ENCODER` | R | 8 | 6 × `0x00` | `[4..7]` i32 position (degrees) |
| 31 | `GET_MOTOR_B_ENCODER` | R | 8 | as 30 | as 30 |
| 32 | `GET_MOTOR_C_ENCODER` | R | 8 | as 30 | as 30 |
| 33 | `GET_MOTOR_D_ENCODER` | R | 8 | as 30 | as 30 |
| 34 | `GET_MOTOR_A_STATUS` | R | 12 | 10 × `0x00` | `[4]` u8 flags, `[5]` i8 PWM power %, `[6..9]` i32 encoder, `[10..11]` i16 speed dps |
| 35 | `GET_MOTOR_B_STATUS` | R | 12 | as 34 | as 34 |
| 36 | `GET_MOTOR_C_STATUS` | R | 12 | as 34 | as 34 |
| 37 | `GET_MOTOR_D_STATUS` | R | 12 | as 34 | as 34 |

Motor status flags (`[4]` of 34–37):

| Bit | Name | Meaning |
| --- | --- | --- |
| 0 (`0x01`) | `LOW_VOLTAGE_FLOAT` | motors disabled (floating) because the battery voltage is too low |
| 1 (`0x02`) | `OVERLOADED` | motor is not close to its target (position / dps control) |

Open questions: does power `0` brake or float **(verify)**; which address does the board use
after reset when it was changed with `SET_ADDRESS` **(verify)**.

## Sensor types

| Value | Name | Value | Name |
| --- | --- | --- | --- |
| 1 | `NONE` | 15 | `EV3_GYRO_ABS` |
| 2 | `I2C` | 16 | `EV3_GYRO_DPS` |
| 3 | `CUSTOM` | 17 | `EV3_GYRO_ABS_DPS` |
| 4 | `TOUCH` (auto NXT/EV3) | 18 | `EV3_COLOR_REFLECTED` |
| 5 | `NXT_TOUCH` | 19 | `EV3_COLOR_AMBIENT` |
| 6 | `EV3_TOUCH` | 20 | `EV3_COLOR_COLOR` |
| 7 | `NXT_LIGHT_ON` | 21 | `EV3_COLOR_RAW_REFLECTED` |
| 8 | `NXT_LIGHT_OFF` | 22 | `EV3_COLOR_COLOR_COMPONENTS` |
| 9 | `NXT_COLOR_RED` | 23 | `EV3_ULTRASONIC_CM` |
| 10 | `NXT_COLOR_GREEN` | 24 | `EV3_ULTRASONIC_INCHES` |
| 11 | `NXT_COLOR_BLUE` | 25 | `EV3_ULTRASONIC_LISTEN` |
| 12 | `NXT_COLOR_FULL` | 26 | `EV3_INFRARED_PROXIMITY` |
| 13 | `NXT_COLOR_OFF` | 27 | `EV3_INFRARED_SEEK` |
| 14 | `NXT_ULTRASONIC` | 28 | `EV3_INFRARED_REMOTE` |

Value 0 is not a valid type (used by the driver as "not configured").

### `SET_SENSOR_TYPE` (12)

| Sensor type | Frame |
| --- | --- |
| `CUSTOM` | `[ADDR, 12, mask, 3, flags_hi, flags_lo]` – u16 flags, see below (len 6) |
| `I2C` | `[ADDR, 12, mask, 2, settings, speed_us]` – u8 settings flags, u8 target clock period in µs (len 6) |
| `I2C` with `SAME` flag | as `I2C` + `[6..9]` u32 delay between transactions (µs), `[10]` I2C address, `[11]` u8 bytes to read, `[12]` u8 bytes to write *n*, `[13..]` *n* bytes (len 13 + *n* ≤ 29) |
| all other types | `[ADDR, 12, mask, type]` (len 4) |

`CUSTOM` flags (u16):

| Flag | Value | Meaning |
| --- | --- | --- |
| `PIN1_9V` | `0x0002` | 9 V out on pin 1 (NXT ultrasonic) |
| `PIN5_OUT` | `0x0010` | pin 5 as output (input otherwise) |
| `PIN5_STATE` | `0x0020` | pin 5 output high |
| `PIN6_OUT` | `0x0100` | pin 6 as output |
| `PIN6_STATE` | `0x0200` | pin 6 output high |
| `PIN1_ADC` | `0x1000` | ADC on pin 1 (NXT analog sensors) |
| `PIN6_ADC` | `0x4000` | ADC on pin 6 |

`I2C` settings (u8):

| Flag | Value | Meaning |
| --- | --- | --- |
| `MID_CLOCK` | `0x01` | extra clock pulse between write and read (NXT ultrasonic) |
| `PIN1_9V` | `0x02` | 9 V pull-up on pin 1 |
| `SAME` | `0x04` | firmware repeats the same transaction continuously |
| `ALLOW_STRETCH_ACK` | `3` (!) | clock stretching – value in `brickpi3.py` is an enumeration index, not a bit mask; likely a driver bug **(verify)** |
| `ALLOW_STRETCH_ANY` | `4` (!) | as above; collides with `SAME` |

I2C payload is limited to 16 bytes (`I2C_LENGTH_LIMIT`); the Python driver silently truncates
longer writes.

### `GET_SENSOR_n` (13–16)

Common reply header: `RX[3] = 0xA5`, `RX[4]` = sensor type reported by firmware (must equal the
configured type; `TOUCH` accepts `NXT_TOUCH`/`EV3_TOUCH`), `RX[5]` = sensor state, data from
`RX[6]`.

| State | Value |
| --- | --- |
| `VALID_DATA` | 0 |
| `NOT_CONFIGURED` | 1 |
| `CONFIGURING` | 2 |
| `NO_DATA` | 3 |
| `I2C_ERROR` | 4 |

| Sensor types | len | Data |
| --- | --- | --- |
| `TOUCH`, `NXT_TOUCH`, `EV3_TOUCH`, `NXT_ULTRASONIC`, `EV3_COLOR_REFLECTED`, `EV3_COLOR_AMBIENT`, `EV3_COLOR_COLOR`, `EV3_ULTRASONIC_LISTEN`, `EV3_INFRARED_PROXIMITY` | 7 | `[6]` u8 |
| `NXT_LIGHT_ON`, `NXT_LIGHT_OFF`, `NXT_COLOR_RED/GREEN/BLUE/OFF` | 8 | `[6..7]` u16 |
| `EV3_GYRO_ABS`, `EV3_GYRO_DPS` | 8 | `[6..7]` i16 |
| `EV3_ULTRASONIC_CM`, `EV3_ULTRASONIC_INCHES` | 8 | `[6..7]` u16 in tenths (value / 10) |
| `EV3_COLOR_RAW_REFLECTED` | 10 | `[6..7]` u16 red reflected, `[8..9]` u16 unknown (raw ambient?) |
| `EV3_GYRO_ABS_DPS` | 10 | `[6..7]` i16 angle, `[8..9]` i16 rate |
| `CUSTOM` | 10 | `[6]` bit 0 = pin 5 digital, bit 1 = pin 6 digital; pin 6 ADC (12 bit, 3.3 V) = `[7] << 4 \| [8] >> 4`; pin 1 ADC (12 bit, 5 V) = `([8] & 0x0F) << 8 \| [9]` |
| `NXT_COLOR_FULL` | 12 | `[6]` colour; red/green/blue/ambient 10 bit = `[7..10] << 2` + 2 low bits packed in `[11]` (bits 7–6 red, 5–4 green, 3–2 blue, 1–0 ambient) |
| `EV3_COLOR_COLOR_COMPONENTS` | 14 | `[6..13]` 4 × u16: red, green, blue, unknown |
| `EV3_INFRARED_SEEK` | 14 | `[6..13]` 4 channels × (i8 heading −25…25, i8 distance −128 or 0…100) |
| `EV3_INFRARED_REMOTE` | 10 | `[6..9]` u8 button code per channel (0–11, mapping in `brickpi3.py`) |
| `I2C` | 6 + *in* | `[6..]` bytes read (*in* = bytes to read from the last transaction) |

## Known issues in existing drivers

- Rust driver (upstream): `NXT_COLOR_FULL` reads 8 bytes instead of 12; no I2C support.
- C++ driver: I2C `SAME` delay truncated to `uint8_t`.
- Python driver: `ALLOW_STRETCH_*` flag values (see above).

## MCU pin usage (ATSAMD21J18A)

| Function | Pins |
| --- | --- |
| SPI slave to Raspberry Pi | SERCOM3, PA16–PA19 |
| UART | SERCOM1, PA00/PA01 |
| I2C | SERCOM5, PA22/PA23 |
| ADC reference | VREFA ≈ 1.40 V derived from the 5 V rail |
| Free GPIO | PA02, PA09 |
