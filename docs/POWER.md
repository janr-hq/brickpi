# Power supply

Analysis of the power stage of the current board (KiCad REV2, `hardware/brickpi3/`) and the
requirements for supporting a Raspberry Pi 5. Values marked **(unverified)** come from
datasheets or estimates and have not been measured on the board yet.

## Current power tree

Simplified; the authoritative source is `hardware/brickpi3/power.kicad_sch`.

```text
battery / DC jack (VCC, 9–12.6 V)
  └─ D15 SK24A Schottky (reverse-polarity protection, full current)
       ├─ VCC ─────────────► TB6612 motor drivers (VM), battery voltage monitor
       └─ LM2576-5 buck ──► F1 PTC (~2 A) ──► 5 V rail ──► Raspberry Pi (header pin 2 only)
                                                 ├─ MIC5504 LDO ──► 3V3 (MCU, logic)
                                                 └─ AP3012 boost ──► 9 V (sensor pin 1)
```

## Findings

| Part | Issue | Impact |
| --- | --- | --- |
| D15 SK24A (2 A Schottky) | In series with the whole board current | 1–1.5 W loss; probable hot spot – thermal camera showed ~45 °C at 20 °C ambient |
| LM2576-5 | 77–80 % efficiency | 3–4.5 W of heat at 2–3 A |
| F1 PTC (~2 A) | Placed after the regulator feedback point | limits the 5 V rail to ~2 A and causes voltage drops under load |
| Pi header | Only 5 V pin 2 is connected, pin 4 is not | half of the available contact current capacity |
| L1 (SDR1006 / SDR1806) | saturation current probably < 3 A **(unverified)** | limits the buck output |
| AP3012 9 V | ~0.2 A max | sufficient for sensor pin 1 only |
| MIC5504 3V3 | – | OK |
| TB6612 | VM 4.5–13.5 V, 1.2 A/channel continuous; a stalled NXT/EV3 motor draws ~2 A @ 9 V **(unverified)** | overload on stall; relies on driver thermal shutdown |
| VCC capacitors | 120 µF + 10 µF / 20 V tantalum | at the edge of derating at 12.6 V |
| Voltage measurement | ADC reference derived from the 5 V rail | readings drift with the 5 V rail |

## Raspberry Pi 5

A Pi 5 needs **5 V / 5 A** (USB-PD 5 A negotiation, otherwise USB current is limited).
The LM2576 + PTC stage cannot deliver this. Required changes:

- Synchronous buck 5 V / 5–6 A (e.g. TI TPS56637; for a prototype a Pololu D36V50F5 module).
- Feed both 5 V header pins (2 and 4) with short, wide copper.
- Set `PSU_MAX_CURRENT=5000` in the Pi 5 EEPROM config so it does not limit USB peripherals.
- Replace D15 with a P-MOSFET or an ideal-diode controller.

Raspberry Pi 3 and 4 work with the current stage (≤ ~2 A).

## Batteries

| Option | Verdict |
| --- | --- |
| 2S Li-ion 18650 (6.0–8.4 V) | After D15 and the LM2576 dropout less than ~7 V is left – would need a buck-boost. Not recommended. |
| **3S Li-ion (9.0–12.6 V)** | **Recommended.** Needs a BMS and a low-voltage cut-off around 9.6 V. |
| 8 × AA NiMH (~9.6 V) | Sags under Pi 5 load. |

Expected run time with 3S 18650 at ~13 W average: about 1.4–2 h.

## Measurement improvements

- External voltage reference for the ADC instead of the 5 V rail.
- Cell / pack monitoring: free MCU pins PA02 and PA09 (ADC) or an I2C fuel gauge.

## Next steps

1. Measure the real current and temperatures (D15, LM2576, L1) under motor load.
2. Prototype the Pi 5 supply with a 5 V / 5 A module.
3. Redesign the power stage in KiCad (new revision) and document it in `hardware/README.md`.
