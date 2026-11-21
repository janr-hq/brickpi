# Simulation

Develop and test software without the physical board.

## Plan

- Protocol mock: a software SPI slave implementing [docs/PROTOCOL.md](../docs/PROTOCOL.md)
  (motors with encoder model, sensor values from scripts) used by driver unit tests in CI.
- Robot simulation (e.g. Webots or Gazebo) of the reference robot from `robot/` driven by the
  same driver API.
- Power budget model (currents per motor/sensor/Pi, battery run time) to support the power
  stage redesign in `docs/POWER.md`.

## Power stage (SPICE) – available

`power/` contains ngspice netlists and behavioural models of the board power supply
(current REV2 and the proposed Pi 5 stage). Run `power/run.sh`; see
[docs/SIMULATION.md](../docs/SIMULATION.md) for tools, models and assumptions and
[RESULTS.md](RESULTS.md) for the results.
