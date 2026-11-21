# Power-stage simulation (SPICE)

Electrical simulation of the board power supply described in [POWER.md](POWER.md):
which simulator, which models (and their licences), how to run the simulations and
what the models can and cannot tell. Results and recommendations are in
[simulation/RESULTS.md](../simulation/RESULTS.md).

## Simulator choice

| | ngspice | LTspice | Qucs-S |
| --- | --- | --- | --- |
| Licence | Free software, mostly modified BSD (a few parts under other free licences, see ngspice `COPYING`) | Freeware, closed source (Analog Devices EULA) | GPL-2.0-or-later |
| Platforms | Linux, Windows, macOS; Debian/Ubuntu package `ngspice` | Windows, macOS; Linux only via Wine | Linux, Windows, macOS |
| Headless / CI | Yes: `ngspice -b file.cir`, `.control` scripts, `wrdata` text output, shared library for Python | Batch mode exists, but needs Wine in CI; EULA and bundled model licences are restrictive | Qt GUI front end; it drives ngspice/Xyce/Qucsator, so CI would run ngspice anyway |
| Models | SPICE3/PSpice/LTspice-style netlists (compatibility modes `ngbehavior=psa` / `lt`), XSPICE digital/behavioural blocks | Large ADI library, usable only inside LTspice | Uses the backend's models |
| KiCad | Built into the KiCad 8 schematic simulator | – | Can import KiCad netlists |

**Decision: ngspice.** It is free, packaged for Ubuntu (CI runners), scriptable, and it is
the engine already inside KiCad, so the same models can later be attached to the
schematic symbols. Qucs-S is a fine GUI on top of ngspice for interactive work; LTspice is
useful for a quick personal cross-check but not for anything committed or run in CI.
Version used for the results: **ngspice-45.2**.

## Models and licences

Vendor SPICE models are normally licensed for use, not for redistribution, so none are
committed (see [simulation/power/vendor/README.md](../simulation/power/vendor/README.md)
for where to get them for a local cross-check). All models in
`simulation/power/models/brickpi_power.lib` are written for this repository (MIT),
either behavioural or curve-fitted to typical datasheet figures.

The TI models mentioned below are covered by TI's model licence, whose text is included
with each model download and in
[TI's terms of use](https://www.ti.com/legal/terms-conditions/terms-of-use.html)
(link not verified; read the licence shipped with the file you use).

| Part (ref.) | Vendor model | Used here |
| --- | --- | --- |
| LM2576S-5 (IC3) | TI publishes PSpice/TINA-TI models on the product page under the TI model licence (no redistribution) | **Behavioural switching model**: 52 kHz PWM, Darlington switch (Vsat ≈ 1.0 V @ 1 A, 1.4 V @ 3 A), cycle-by-cycle limit 5.8 A, Iq 5 mA, internal 1.23 V reference and divider; plus an averaged model with the same loss terms |
| SK24A (D15), SBR10E45P5 (D13) | Several diode vendors publish `.model` cards; terms vary | **Own diode fits** (`IS`, `N`, `RS`) to typical Vf curves |
| 0ZCG0200FF2C PTC (F1) | No public SPICE model known | **Electro-thermal behavioural model**: R(T) with a steep rise near 125 °C, thermal resistance and capacity calibrated so that 2 A holds and ~3.5 A trips |
| MIC5504-3.3 (IC7) | None used | Behavioural LDO (3.3 V, 0.53 Ω dropout resistance, Iq 38 µA) |
| AP3012 (IC8) | None used | Averaged boost 5 V → 9 V, 80 % efficiency |
| TB6612FNG + LEGO motor | No public SPICE model known | Behavioural H-bridge (0.5 Ω Ron at 100 % duty) + DC motor (R, L, back-EMF, inertia) |
| 5 V / 5–6 A synchronous buck (e.g. TPS56637) | TI PSpice transient model (TI licence) | **Generic behavioural sync buck**: 500 kHz peak-current mode, 25/12 mΩ FETs, dead time with body diodes; not a model of a specific part |
| Reverse-polarity P-MOSFET | – | Level-1 PMOS tuned to ~12 mΩ at Vgs = −10 V, 10 V gate zener |
| L1 100 µH (SDR1806) | – | Inductor with soft saturation (L falls to 20 % well above Isat) and DCR |
| Li-ion 18650, NiMH AA | – | OCV(SOC) table, series R, one RC branch, charge counter |

### Assumed values (to be replaced by measurements / exact datasheet values)

| Parameter | Value | Why it matters |
| --- | --- | --- |
| L1 saturation current (L = 0.9·L0) | **2.0 A** (also run with 10 A = non-saturating) | ripple, peak current, current limit at ≥ 3 A |
| L1 DCR | 0.12 Ω | largest single loss term of the LM2576 stage at high current |
| CP7 ESR | 50 mΩ | output ripple |
| LM2576 switching transition time | 100 ns total (added analytically) | small part of the loss |
| F1 R at 25 °C / thermal resistance / capacity | 35 mΩ / 226 K/W / 0.05 J/K | drop, hold/trip behaviour, trip time |
| Header pin 2 + traces to the Pi | 30 mΩ (one pin), 15 mΩ (two pins) | voltage at the Pi |
| Raspberry Pi input | 47 µF, constant current above 4.2 V | load-step dip |
| Motor | 4.0 Ω + 0.5 Ω driver, 3 mH, Ke 0.49 V·s/rad | ~2 A stall at 9 V |
| 18650 cell | 2.6 Ah, 45 mΩ + 20 mΩ‖2000 F, 30 mΩ wiring/BMS | run time, sag |
| NiMH AA cell | 2.0 Ah, 45 mΩ incl. holder contact | run time, sag |
| Sync buck | 3.3 µH (Isat 9 A, 8 mΩ), 2×22 µF + 220 µF polymer, 20 ns transitions, 50 mW drive | efficiency, transient |

## Running

```bash
sudo apt install ngspice          # or any ngspice >= 40
simulation/power/run.sh           # all 58 cases (≈ 20 min on 4 cores), writes simulation/power/results/
simulation/power/run.sh --only 01_ --no-report   # just run a subset
```

`run.sh` uses `uv run --script` (numpy and matplotlib come from the script header) or,
with `NO_UV=1`, the system `python3`. `simulation/power/check.py` asserts that key results
(efficiencies, losses, current limit) stay in expected ranges; CI runs one sweep per family
plus these checks. Raw data goes to `simulation/power/out/` (ignored by
git); unchanged cases are cached, `--force` re-runs everything. Each netlist in
`simulation/power/cir/` also runs on its own: `cd simulation/power/cir && ngspice -b 01_lm2576_load.cir`
(it writes `data.txt` into the current directory).

| Netlist | What |
| --- | --- |
| `01_lm2576_load.cir` | LM2576 stage, switching, constant load 1–5 A at 9 / 12 V input |
| `02_d15_pfet_dc.cir` | D15 vs P-MOSFET drop and loss, DC sweep 0–5 A at 25 / 75 °C |
| `02_ptc_thermal.cir` | F1 PTC drop, temperature, trip time; staircase load |
| `03_load_step.cir` | Current board from a 3S pack: Pi 0 → 3 A, then two stalled motors |
| `04_syncbuck_load.cir` | Proposed synchronous buck, constant load 1–5 A |
| `04_improved_step.cir` | Proposed stage (P-MOSFET + sync buck + 2 header pins), same steps as 03, also 5 A |
| `05_battery.cir` | Run time on 2S / 3S Li-ion and 8×AA NiMH with averaged models |

### CI

The simulations need ngspice and take minutes, so they are not part of the default CI.
A job can be added later by the maintainer (workflows are a protected path):

```yaml
  power-sim:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v6
      - run: sudo apt-get update && sudo apt-get install -y ngspice
      - run: simulation/power/run.sh
      - uses: actions/upload-artifact@v4
        with:
          name: power-sim
          path: simulation/power/results/
```

## Limits of the models

- Behavioural models reproduce **typical** datasheet behaviour; they are not
  manufacturer-validated and ignore part-to-part spread.
- The LM2576 internal compensation is unknown: a PI error amplifier with ~0.6 kHz
  crossover is assumed. The **size of the load-step dip depends on it**; treat the
  dip as an order of magnitude, not a prediction. With ideal regulation the dip at a
  3 A step would still be ~0.1 V (limited by L1 and CP7).
- Switch edges are ideal; transition losses are added analytically
  (0.5·Vin·I·tsw·fsw). Capacitive (Coss, diode capacitance) losses and core losses
  are not modelled. Temperature only affects the diodes, the MOSFET and the PTC.
- The PTC model is calibrated to the generic 1812 / 2 A hold behaviour, not to the
  exact 0ZCG0200FF2C curves; trip *times* are approximate (± factor 2).
- The battery models use typical OCV curves without temperature or ageing effects.
- The Raspberry Pi is a constant-current load; its real under-voltage behaviour
  (PMIC, firmware throttling) is not modelled.
