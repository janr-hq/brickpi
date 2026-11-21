# Driver

Raspberry Pi side driver for the board.

## Today

The board is protocol-compatible with BrickPi3, so the original DexterInd driver works
unchanged: [DexterInd/BrickPi3 – Software](https://github.com/DexterInd/BrickPi3/tree/master/Software)
(Python, C++, …). It only needs `spidev`, therefore it also runs on a Raspberry Pi 5
(RPi.GPIO/pigpio/wiringPi are not needed by the driver itself).

## Plan

- Rust core implementing [docs/PROTOCOL.md](../docs/PROTOCOL.md) over `/dev/spidev0.1`, with
  timeouts, retries and clear errors (the original protocol has none).
- Python bindings (PyO3/maturin) with a `brickpi3`-compatible API, installable with `pip`.
- Board detection via `/proc/device-tree/compatible` (Pi 3, 4, 5, CM5, Pi 500) instead of
  revision-code tables.
- Installer without `curl | sudo bash`, without default users/credentials, using
  `/boot/firmware/config.txt` on current Raspberry Pi OS.
- Unit tests against the protocol mock from `simulation/`.
