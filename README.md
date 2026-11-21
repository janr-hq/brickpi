# brickpi

Open hardware Raspberry Pi controller for LEGO® MINDSTORMS® NXT/EV3 modular robots:
4 motor ports (with encoders), 4 sensor ports, own power supply. A from-scratch KiCad
re-implementation of the [BrickPi3](https://github.com/DexterInd/BrickPi3) by Dexter Industries
(MIT), developed as a bachelor's thesis project ("Sterownik z mikrokomputerem Raspberry Pi
dla robotów modułowych LEGO Mindstorms") and now continued as an open project.

> Polski skrót: sterownik dla robotów LEGO Mindstorms oparty na Raspberry Pi 3/4/5 – klon
> BrickPi3 (MIT). Repo zawiera projekt płytki (KiCad 8), opis protokołu SPI i zasilania,
> a w kolejnych etapach sterownik, firmware, obudowę i robota.

## Status

Version **0.1.0-dev** – repository bootstrap. Nothing here is a finished product yet.

| Area | State |
| --- | --- |
| Hardware (`hardware/`) | KiCad 8 project, REV2. A first board was fabricated (Dec 2024) and tested with motors, colour and distance sensors; the design was fixed afterwards (motor tracks, I2C level shifter, motor B/D power, inductor footprint) – the current revision is **not yet fabricated**. |
| Driver (`driver/`) | Planned. Today the original DexterInd Python driver works unchanged (spidev only). |
| Firmware (`firmware/`) | Planned. Today the original DexterInd binary v1.4.8 (ATSAMD21J18A) is flashed over SWD. |
| Enclosure (`enclosure/`) | FreeCAD case for board + Raspberry Pi 5 (prototype). |
| Simulation (`simulation/`) | Power-stage SPICE simulation (ngspice) available, see [docs/SIMULATION.md](docs/SIMULATION.md); protocol mock and robot simulation planned. |
| Robot (`robot/`) | Planned. |

## Raspberry Pi compatibility

| Board | Logic / SPI | Power from brickpi | Notes |
| --- | --- | --- | --- |
| Pi 3 B/B+ | ✅ | ✅ | Original BrickPi3 target. |
| Pi 4 B | ✅ | ✅ (≤ ~2 A) | |
| Pi 5 | ✅ (spidev) | ❌ | Needs 5 V / 5 A; the LM2576 + PTC stage is limited to ~2 A. See [docs/POWER.md](docs/POWER.md). Flashing over SWD needs the `rpi5.cfg` OpenOCD interface. |

The SPI protocol is documented in [docs/PROTOCOL.md](docs/PROTOCOL.md).

## Repository layout

| Path | Content |
| --- | --- |
| [`hardware/`](hardware/) | KiCad 8 schematic + PCB |
| [`docs/`](docs/) | Protocol, power analysis, design notes |
| [`driver/`](driver/) | Raspberry Pi driver (plan: Rust core + Python bindings) |
| [`firmware/`](firmware/) | MCU firmware (plan: Rust/Embassy, protocol-compatible) |
| [`enclosure/`](enclosure/) | Case (FreeCAD today, parametric later) |
| [`robot/`](robot/) | Reference robot built on the board |
| [`simulation/`](simulation/) | Board/robot simulation and protocol mock |

## Contributing

Branch from `develop`, open pull requests against `develop`, use
[Conventional Commits](https://www.conventionalcommits.org/) and add an entry to
[CHANGELOG.md](CHANGELOG.md). Details: [CLAUDE.md](CLAUDE.md).

## License and attribution

MIT – see [LICENSE](LICENSE). Based on BrickPi3 by Dexter Industries (MIT, © 2017 Dexter
Industries); see [NOTICE](NOTICE). This project is not affiliated with Dexter Industries or the
LEGO Group. LEGO® and MINDSTORMS® are trademarks of the LEGO Group.
