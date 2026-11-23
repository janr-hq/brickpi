# Prior art – open-source survey

Survey of existing open-source work relevant to this project (Raspberry Pi controller for LEGO
Mindstorms motors/sensors, driver, reference robot). Done before building, to avoid reinventing
what already exists.

**Licence rule:** code is taken only from MIT, BSD or Apache-2.0 projects, with attribution
(see [NOTICE](../NOTICE)). GPL projects (e.g. ev3dev) are inspiration only – ideas and public
behaviour, never code.

**Method and caveats:** web search plus reading the repository front pages, 2026-11-23. Licences
are from the repository metadata; "activity" is the best date found. Where a date could not be
confirmed it says so – verify before depending on a project.

## 1. LEGO / Raspberry Pi hardware and drivers

### BrickPi3 (Dexter Industries / Modular Robotics)

- Link: <https://github.com/DexterInd/BrickPi3> (PyPI: `brickpi3`)
- Licence: MIT (LICENSE.md; PyPI lists MIT). Firmware binary is closed.
- Activity: low. Aggregators show last push in early 2023; PyPI shows a signed release in
  Feb 2026 and a Trixie install script, so it is alive but barely developed.
- Does better than us: it exists and works today – Python, C++, Scratch and other bindings,
  tested firmware, large user base, many tutorials.
- Take: the protocol and API shape (already in [PROTOCOL.md](PROTOCOL.md)); keep the
  `brickpi3`-compatible Python API so existing programs run unchanged; its test programs as
  behavioural references.
- Avoid: `curl | sudo bash` installer, default credentials in images, no timeouts/retries/CRC in
  the protocol, RPi-revision lookup tables (break on new boards).

### GoPiGo3 (Dexter Industries)

- Link: <https://github.com/DexterInd/GoPiGo3>
- Licence: MIT (LICENSE.md; SPDX not shown on the page).
- Activity: low/maintenance mode (same vendor as BrickPi3).
- Does better: complete product – a finished robot with docs, a Python `easygopigo3` layer
  and browser-streaming demo.
- Take: the "easy" high-level layer (`drive_cm`, `turn_degrees`, sensor classes) as the model
  for our example API.
- Avoid: bundling the vendor's whole image/DexterOS stack.

### ev3dev and python-ev3dev2

- Links: <https://github.com/ev3dev/ev3dev> (distro, GPL-2.0),
  <https://github.com/ev3dev/ev3dev-lang-python> (MIT).
- Activity: ev3dev meta repo's last commit on `ev3dev-stretch` is Dec 2024, sparse before that;
  389 open issues. Debian Stretch based – effectively frozen. Does not support Pi 5 or the
  BrickPi3 we build.
- Does better: very clean, widely copied API (`Motor`, `MoveTank`, `MoveDifferential`,
  sensor classes, units like `SpeedRPM`, `DistanceCM`); sysfs-style device model.
- Take: the API design and naming (the Python bindings are MIT, so even code may be reused
  with attribution; the distro/kernel is GPL → idea only).
- Avoid: a kernel-driver dependency; a Debian-Stretch-pinned image.

### Pybricks

- Link: <https://github.com/pybricks/pybricks-micropython>
- Licence: MIT, but only for files carrying the SPDX header (check per file before copying).
- Activity: very active – 4.0.0 reported 2026-06 (not confirmed on the official page).
  ev3dev support was dropped in the 4.0 betas.
- Does better: polished, beginner-friendly API; excellent `DriveBase` (gyro-assisted, tuned
  acceleration/stop modes); browser IDE (pybricks-code, Web Bluetooth).
- Take: `DriveBase` semantics (`straight`, `turn`, `curve`, stop modes: coast/brake/hold) as
  the target for our high-level driving layer; the Pybricks API docs as a spec.
- Avoid: copying firmware code into ours (per-file licence, hub-specific); targeting Pybricks
  hubs – it does not run on a Raspberry Pi + our board.

### LEGO Build HAT (`buildhat`)

- Link: <https://github.com/RaspberryPiFoundation/python-build-hat>
  (docs: <https://buildhat.readthedocs.io>)
- Licence: MIT (© Raspberry Pi Foundation / LEGO System A/S per the library docs).
  Build HAT firmware is also open source (RPi news, 2021).
- Activity: active; 0.6.0 added Pi 5 support, 0.7.0 is the latest release I found.
- Does better: official Raspberry Pi product; clean object model (`Motor`, `ColorSensor`,
  `DistanceSensor`, `Hat`), device auto-detection, absolute-position and speed control; works on
  Pi 3/4/5/Zero; supports SPIKE/Technic devices.
- Take: API ideas and the device-detection pattern; **a second target for the same
  application code** (a thin abstraction so a program runs on our board or on a Build HAT).
- Avoid: the Build HAT's power limits as a design reference (needs its own 8 V supply and
  doesn't support NXT/EV3 sensors) – it is not a drop-in alternative for NXT/EV3 parts.

### gpiozero

- Link: <https://github.com/gpiozero/gpiozero>
- Licence: BSD-3-Clause. Activity: active, maintained by Raspberry Pi.
- Does better: tiny, readable device API for Pi (`Robot`, `Motor`, `DistanceSensor`,
  `LineSensor`), pin-factory abstraction that works on Pi 5 (lgpio).
- Take: the `Robot(left, right)` + `forward/backward/left/right/stop` surface and the
  device/pin-factory split – useful as the "beginner" facade over our driver.
- Avoid: using it for SPI to our MCU – plain `spidev` is enough.

## 2. Robot middleware

### ROS 2 on Raspberry Pi (+ ros2_control)

- Links: <https://docs.ros.org/en/jazzy/How-To-Guides/Installing-on-Raspberry-Pi.html>,
  <https://github.com/ros-controls/ros2_controllers> (`diff_drive_controller`),
  community native Jazzy packages for Pi OS (Trixie): see the Open Robotics Discourse thread.
- Licence: Apache-2.0 (ros2_controllers, ROS 2 core).
- Activity: very active (Jazzy LTS to 2029).
- Does better: standard interfaces – `cmd_vel`, `odom`, TF, `diff_drive_controller`,
  `ros2_control` hardware interface, tooling (rviz, rosbag, Nav2, slam_toolbox).
- Take: implement our driver as a **`ros2_control` hardware interface** (position/velocity
  from the board encoders) and reuse `diff_drive_controller` instead of writing odometry;
  `robot/` already plans a ROS 2 node. Apache-2.0 allows code reuse with attribution.
- Avoid: making ROS 2 a base dependency of the driver; running it on Pi OS natively
  (officially Ubuntu 24.04 or Docker; Docker adds SPI/device pass-through work).

## 3. Control from browser or phone

### PiCraftZero

- Link: <https://github.com/WayneKeenan/picraftzero> – MIT, beta, 22 stars.
- Activity: low/likely dormant (activity date not confirmed).
- Does better: complete stack – gamepad + web (mobile-friendly) control, websocket messages,
  camera streaming, gpiozero-style components.
- Take: architecture (websocket control channel + separate video stream, virtual joystick page).
- Avoid: the old stack (Python 2-era tooling, legacy camera API, MJPEG pipeline); depend on it.

### OpenPiRobotics WebRobotControl, other Flask/websocket robots

- Links: <https://github.com/OpenPiRobotics/WebRobotControl>, Dexter's Browser Streaming Robot
  (GoPiGo demo), Wheelchair-Bot (<https://github.com/Wheelchair-Bot>, FastAPI + WebSocket +
  virtual joystick, MIT per org README; repo updated May 2026, tiny community – licence/layout
  of the actual repo to be verified).
- Does better: working phone UIs with virtual joystick and live video, no app install.
- Take: pattern – small server (FastAPI/aiohttp) with a WebSocket for commands and a
  **deadman timeout** (stop motors if no command for ~300 ms), plus an MJPEG/WebRTC stream via
  `libcamera`/`picamera2`.
- Avoid: HTTP polling for control; open unauthenticated access beyond the local network;
  flagging licences of single-author demos as safe without checking.

## 4. Line follower and obstacle avoidance

### ros-line-follower-robot (chrisdalke)

- Link: <https://github.com/chrisdalke/ros-line-follower-robot> – no licence file (all rights
  reserved by default), 37 stars, ROS Noetic (EOL).
- Does better: camera-based line following on a Pi with OpenCV.
- Take: only the idea (threshold → centroid → PID on lateral error).
- Avoid: copying code (no licence); Noetic.

### tdorssers/Robot

- Link: <https://github.com/tdorssers/Robot> – GPL-3.0, archived Dec 2024.
- Take: nothing but ideas (state machine "follow line / avoid obstacle").
- Avoid: GPL code.

### Generic PID line followers and ultrasonic avoidance

- A large number of Arduino/Pico tutorials and student projects (Hackaday, Hackster, university
  pages); licences mostly unstated, quality varies.
- Does better: nothing we need beyond what the algorithm gives.
- Take: the standard recipe – (reflected-light sensor) → PD/PID on error → differential
  speed; for obstacles, a simple state machine (cruise → stop → turn/back-off) with
  hysteresis and timeouts. Write our own (≈50 lines); no code import needed.
- Avoid: blocking `sleep` loops, no sensor timeouts, tuning without logs.

## TOP 5 recommendations (effort / gain)

| # | Recommendation | Effort | Gain |
| --- | --- | --- | --- |
| 1 | Keep the **`brickpi3`-compatible Python API** and test our driver against the original library's behaviour (BrickPi3, MIT). | Low | Very high – every existing BrickPi3 program and tutorial works on our board. |
| 2 | Copy API **naming from python-ev3dev2 / Pybricks `DriveBase`** (units, `straight/turn`, stop modes) for the high-level layer; thin gpiozero-style `Robot` facade for beginners. | Low–medium | High – friendly API without inventing one. |
| 3 | **ROS 2 `ros2_control` hardware interface** + `diff_drive_controller` (Apache-2.0), later Nav2. | Medium | High – odometry, TF, teleop, SLAM for free. |
| 4 | **Phone/browser teleop**: FastAPI + WebSocket, virtual joystick, deadman timeout, `picamera2` stream (pattern from PiCraftZero/others, own code). | Medium | High – demo value and a handy test tool. |
| 5 | **Build HAT as second backend** behind the same application API (and a protocol mock for tests). | Medium | Medium – examples run on both, and a mock enables CI. |

## Rejected

| Project | Reason |
| --- | --- |
| ev3dev (distro/kernel) | GPL-2.0, frozen on Debian Stretch, no Pi 5 – inspiration only. |
| Pybricks firmware | Targets its own hubs; per-file MIT only; no use on Pi + our board. |
| ros-line-follower-robot | No licence, ROS Noetic (EOL). |
| tdorssers/Robot | GPL-3.0, archived, ATmega8. |
| bricktronics and similar Arduino shields | Unclear licence (see [CLAUDE.md](../CLAUDE.md)); different architecture. |
| Dexter's closed firmware binary | Stays external, not copied into the repo (already noted in `firmware/`). |
| Running ROS 2 as a required dependency | Heavy for a basic driver; keep it optional (`robot/`). |
| Single-author web-robot demos (as code) | Licences/quality unverified; take the pattern, write our own. |

## Final recommendation

Do not build from scratch what exists. In order: (1) stay API-compatible with BrickPi3 in the
driver and keep the original library as the compatibility oracle; (2) design the high-level API
after python-ev3dev2/Pybricks `DriveBase`; (3) expose the robot to ROS 2 through
`ros2_control` rather than custom odometry code; (4) add a small WebSocket teleop server for the
reference robot; (5) write line following and obstacle avoidance ourselves (small PID +
state machine) – no suitable permissively licensed code exists to import. Take code only from
MIT/BSD/Apache-2.0 sources and add them to [NOTICE](../NOTICE); treat everything GPL, and
anything without a licence, as read-only inspiration.

## Sources

- <https://github.com/DexterInd/BrickPi3>, <https://pypi.org/project/brickpi3>
- <https://github.com/DexterInd/GoPiGo3>
- <https://github.com/ev3dev/ev3dev>, <https://github.com/ev3dev/ev3dev-lang-python>
- <https://github.com/pybricks/pybricks-micropython>
- <https://github.com/RaspberryPiFoundation/python-build-hat>,
  <https://www.raspberrypi.com/news/build-hat-firmware-now-fully-open-source/>
- <https://github.com/gpiozero/gpiozero>
- <https://docs.ros.org/en/jazzy/How-To-Guides/Installing-on-Raspberry-Pi.html>,
  <https://github.com/ros-controls/ros2_controllers>
- <https://github.com/WayneKeenan/picraftzero>, <https://github.com/OpenPiRobotics/WebRobotControl>
- <https://github.com/chrisdalke/ros-line-follower-robot>, <https://github.com/tdorssers/Robot>
