# Hardware

KiCad 8 project of the board: `brickpi3/BrickPi-Kicad-Project.kicad_pro`.

Schematic sheets:

| Sheet | Content |
| --- | --- |
| `BrickPi-Kicad-Project.kicad_sch` | root: MCU ATSAMD21J18A, Raspberry Pi header, SWD, LEDs, I2C level shifter |
| `motors.kicad_sch` | 4 × motor port (TB6612 drivers, encoder inputs) |
| `sensors.kicad_sch` | 4 × sensor port (NXT/EV3, ADC, I2C, 9 V pin) |
| `power.kicad_sch` | battery input, LM2576 5 V buck, MIC5504 3V3, AP3012 9 V – see [docs/POWER.md](../docs/POWER.md) |

Board: 85.6 × 56.5 mm (Raspberry Pi HAT-like footprint), 2 layers. Board-specific design
rules are in `BrickPi-Kicad-Project.kicad_dru`.

## Revision history

| Date | Change |
| --- | --- |
| 2024-10 | REV2 drawn from the BrickPi3 v3.2.1 reference schematic (DexterInd). |
| 2024-12 | First board fabricated from this revision (tested: motors, colour and distance sensors). |
| 2025-02 | Fixed motor tracks. |
| 2025-04 | Updated I2C connections and motor B/D power lines; 100 µH inductor footprint changed to SDR1806. **Not fabricated yet.** |

## Libraries and 3D models

Symbols and footprints are embedded in the schematic/PCB files, so the project opens without
extra libraries. 3D models from third-party libraries (`${KICAD8_3RD_PARTY}/…`: RJ11
TJ6P6C, SS12D06, SK24A, 0ZCG0200FF2C, VLCF5020T, SBR10E45P5, Grove header) are **not**
included – the 3D view shows those parts without bodies.

## Fabrication files

Gerbers, drill files and BOM are not committed (they go stale). CI exports them from the
current PCB with `kicad-cli` and attaches them as a build artifact (`hardware-fab`).
Locally:

```sh
cd hardware/brickpi3
kicad-cli sch erc --severity-error -o erc.rpt BrickPi-Kicad-Project.kicad_sch
kicad-cli pcb drc --schematic-parity -o drc.rpt BrickPi-Kicad-Project.kicad_pcb
kicad-cli pcb export gerbers -o fab/ BrickPi-Kicad-Project.kicad_pcb
kicad-cli pcb export drill -o fab/ BrickPi-Kicad-Project.kicad_pcb
```

Interactive BOM: `ibom.config.ini` holds the settings for the
[InteractiveHtmlBom](https://github.com/openscopeproject/InteractiveHtmlBom) plugin.

## TODO

- Fix the ERC/DRC findings and make the CI check blocking.
- Silkscreen contains a university logo footprint (`PW:weiti`) – decide whether it stays in
  the public design.
- New power stage for Raspberry Pi 5 (see `docs/POWER.md`).
- Proper BOM with manufacturer part numbers.
