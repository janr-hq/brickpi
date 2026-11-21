# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Power-stage SPICE simulation with ngspice (`simulation/power/`): behavioural models
  (LM2576-5, synchronous buck, PTC electro-thermal, saturating inductor, P-MOSFET,
  TB6612 + motor, Li-ion / NiMH packs), netlists for efficiency, D15 / PTC losses,
  load steps and battery run time, `run.sh` / `run.py` producing CSV + PNG results.
- `docs/SIMULATION.md` – simulator comparison (ngspice / LTspice / Qucs-S), model
  licences, assumptions and limits; `simulation/RESULTS.md` – results and
  recommendations for the power-stage redesign.

## [0.1.0-dev] - 2026-11-21

### Added

- Repository structure: `hardware/`, `docs/`, `driver/`, `firmware/`, `enclosure/`, `robot/`,
  `simulation/` with README files describing the plan.
- KiCad 8 project of the board (REV2, latest revision from April 2025: fixed motor tracks,
  I2C level-shifter wiring, motor B/D power lines, SDR1806 inductor footprint) in
  `hardware/brickpi3/`. Absolute Windows paths removed from the project and 3D model references.
- FreeCAD enclosure prototype for the board with a Raspberry Pi 5 in `enclosure/freecad/`.
- `docs/PROTOCOL.md` – SPI protocol with all message types 0–37 and byte layouts.
- `docs/POWER.md` – power supply analysis and Raspberry Pi 5 requirements.
- `NOTICE` with Dexter Industries (MIT) attribution and trademark notes.
- `CLAUDE.md` – working rules (branches, Conventional Commits, changelog).
- `.gitattributes` (LF, binary CAD formats), `.gitignore` (KiCad backups, caches, temp files).
- CI: markdown lint, secret scan (gitleaks + `scripts/check-repo.sh`), KiCad ERC/DRC and
  Gerber/drill export with `kicad-cli` (reports as artifacts, not blocking yet).

[Unreleased]: https://github.com/janr-hq/brickpi/compare/v0.1.0-dev...HEAD
[0.1.0-dev]: https://github.com/janr-hq/brickpi/releases/tag/v0.1.0-dev
