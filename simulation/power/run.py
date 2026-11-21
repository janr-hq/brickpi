#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy>=1.24", "matplotlib>=3.7"]
# ///
"""Run the brickpi power-stage ngspice simulations and write results/.

Usage:  uv run simulation/power/run.py [--only PREFIX] [--force] [--jobs N]

Each case renders a netlist from cir/ (overriding .param values), runs
`ngspice -b` in out/<case>/ and post-processes the data into
results/*.csv and results/*.png. Raw data in out/ is not committed;
cases whose rendered netlist and model library did not change are reused.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import csv
import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
CIR, MODELS, OUT, RES = HERE / "cir", HERE / "models", HERE / "out", HERE / "results"
LIB = MODELS / "brickpi_power.lib"

# Analytic switching-transition loss added on top of the switching models
# (ideal switch edges): P = 0.5 * Vin * I * TSW * FSW (+ gate drive).
LM_TSW, LM_FSW = 100e-9, 52e3
SB_TSW, SB_FSW, SB_PDRV = 20e-9, 500e3, 0.05
LM_DCR, SB_DCR = 0.12, 0.008
PI_UV = 4.63  # Raspberry Pi under-voltage warning threshold (approx.)


# --------------------------------------------------------------------------
# case definitions
# --------------------------------------------------------------------------
def fmt(v: float) -> str:
    return f"{v:g}"


def cases() -> list[tuple[str, str, dict]]:
    c: list[tuple[str, str, dict]] = []
    for vin in (9.0, 12.0):
        for i in (1, 2, 3, 4, 5):
            c.append((f"01_lm_v{fmt(vin)}_i{i}", "01_lm2576_load.cir", {"VIN": vin, "ILOAD": i}))
    for i in (1, 2, 3, 4, 5):  # same, inductor that does not saturate
        c.append((f"01_lmL10_v12_i{i}", "01_lm2576_load.cir", {"VIN": 12.0, "ILOAD": i, "ISAT": 10}))
    for vin in (9.0, 12.0):
        for i in (1, 2, 3, 4, 5):
            c.append((f"04_sb_v{fmt(vin)}_i{i}", "04_syncbuck_load.cir", {"VIN": vin, "ILOAD": i}))
    c.append(("02_dc", "02_d15_pfet_dc.cir", {}))
    for ta in (25, 50):
        for i in (2.0, 2.5, 3.0, 3.5, 4.0, 5.0):
            c.append((f"02_ptc_ta{ta}_i{fmt(i)}", "02_ptc_thermal.cir", {"ILOAD": i, "TA": ta, "TSTOP": 300}))
    c.append(("02_ptc_stairs", "02_ptc_thermal.cir", {"PROFILE": 1, "TSTOP": 300}))
    for pi, soc in ((3, 0.5), (3, 0.1)):
        c.append((f"03_step_pi{pi}_soc{fmt(soc)}", "03_load_step.cir", {"PI_I": pi, "SOC": soc}))
    # sensitivity: 3x faster assumed LM2576 compensation, and a non-saturating L1
    c.append(("03_step_pi3_soc0.5_gm3", "03_load_step.cir", {"PI_I": 3, "SOC": 0.5, "GM_EA": 3e-3}))
    c.append(("03_step_pi3_soc0.5_l10", "03_load_step.cir", {"PI_I": 3, "SOC": 0.5, "ISAT": 10}))
    for pi, soc in ((3, 0.5), (5, 0.5), (5, 0.1)):
        c.append((f"04b_step_pi{pi}_soc{fmt(soc)}", "04_improved_step.cir", {"PI_I": pi, "SOC": soc}))
    for src, chem, ns, cah in (("2S", 1, 2, 2.6), ("3S", 1, 3, 2.6), ("8AA", 2, 8, 2.0)):
        for topo in (1, 2):
            for pi, i5 in (("pi5", 2.0), ("pi4", 1.2)):
                c.append((f"05_bat_{src}_t{topo}_{pi}", "05_battery.cir",
                          {"CHEM": chem, "NS": ns, "CAH": cah, "TOPO": topo, "I5": i5, "TSTOP": 18000}))
    return c


# --------------------------------------------------------------------------
# running ngspice
# --------------------------------------------------------------------------
def render(cir: str, params: dict) -> str:
    text = (CIR / cir).read_text()
    text = text.replace("../models/", f"{MODELS}/")
    lines = text.splitlines()
    for key, val in params.items():
        hit = False
        for n, line in enumerate(lines):
            if line.lower().startswith(".param"):
                new = re.sub(rf"(?<![\w]){key}=\S+", f"{key}={fmt(val)}", line)
                hit |= new != line or f"{key}={fmt(val)}" in line
                lines[n] = new
        if not hit:
            raise ValueError(f"{cir}: no .param {key}")
    return "\n".join(lines) + "\n"


def run_case(name: str, cir: str, params: dict, force: bool) -> str:
    d = OUT / name
    d.mkdir(parents=True, exist_ok=True)
    net = render(cir, params)
    digest = hashlib.sha256((net + LIB.read_text()).encode()).hexdigest()
    stamp = d / "hash"
    datafiles = list(d.glob("data*.txt"))
    if not force and datafiles and stamp.exists() and stamp.read_text() == digest:
        return f"{name}: cached"
    for f in datafiles:
        f.unlink()
    (d / "case.cir").write_text(net)
    with open(d / "ngspice.log", "w") as log:
        rc = subprocess.run(["ngspice", "-b", "case.cir"], cwd=d, stdout=log,
                            stderr=subprocess.STDOUT, timeout=3600).returncode
    if rc != 0 or not list(d.glob("data*.txt")):
        tail = (d / "ngspice.log").read_text()[-1500:]
        raise RuntimeError(f"{name}: ngspice failed (rc={rc})\n{tail}")
    stamp.write_text(digest)
    return f"{name}: ok"


def load(name: str, file: str = "data.txt") -> dict[str, np.ndarray]:
    path = OUT / name / file
    with open(path) as f:
        header = f.readline().split()
    data = np.loadtxt(path, skiprows=1, ndmin=2)
    return {h: data[:, k] for k, h in enumerate(header)}


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
_trapz = getattr(np, "trapezoid", None) or np.trapz


def tavg(t: np.ndarray, y: np.ndarray) -> float:
    return float(_trapz(y, t) / (t[-1] - t[0]))


def window(d: dict, t0: float) -> dict:
    m = d["time"] >= t0
    return {k: v[m] for k, v in d.items()}


def first_cross_below(t: np.ndarray, y: np.ndarray, level: float, after: float = 0.0) -> float | None:
    idx = np.nonzero((y < level) & (t >= after))[0]
    return float(t[idx[0]]) if idx.size else None


def write_csv(name: str, rows: list[dict]) -> None:
    RES.mkdir(exist_ok=True)
    with open(RES / name, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow({k: (f"{v:.4g}" if isinstance(v, float) else v) for k, v in r.items()})


def md_table(rows: list[dict], cols: list[str]) -> str:
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for r in rows:
        out.append("| " + " | ".join(f"{r[c]:.3g}" if isinstance(r[c], float) else str(r[c]) for c in cols) + " |")
    return "\n".join(out)


# --------------------------------------------------------------------------
# plotting (light theme, fixed categorical order, single y-axis per panel)
# --------------------------------------------------------------------------
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"


def plt_setup():
    os.environ.setdefault("MPLCONFIGDIR", str(OUT / ".mpl"))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "figure.facecolor": SURF, "axes.facecolor": SURF, "savefig.facecolor": SURF,
        "axes.edgecolor": GRID, "axes.labelcolor": INK2, "axes.titlecolor": INK,
        "axes.titlesize": 10, "axes.labelsize": 9, "font.size": 9,
        "xtick.color": INK2, "ytick.color": INK2, "axes.grid": True,
        "grid.color": GRID, "grid.linewidth": 0.6, "axes.spines.top": False,
        "axes.spines.right": False, "legend.frameon": False, "legend.fontsize": 8,
        "lines.linewidth": 1.5, "lines.markersize": 5,
    })
    return plt


def label_end(ax, x, y, text, color_idx=0, dy=0.0):
    ax.annotate(text, (x[-1], y[-1]), xytext=(4, dy), textcoords="offset points",
                fontsize=8, color=INK2, va="center")


# --------------------------------------------------------------------------
# 01 / 04: converter efficiency sweeps
# --------------------------------------------------------------------------
def analyse_sweep(prefix: str, vins, kind: str, isat_tag: str = "") -> list[dict]:
    rows = []
    for vin in vins:
        for i in (1, 2, 3, 4, 5):
            name = f"{prefix}_v{fmt(vin)}_i{i}"
            d = load(name)
            period = 1 / (LM_FSW if kind == "lm" else SB_FSW)
            n_cyc = 260 if kind == "lm" else 200
            w = window(d, d["time"][-1] - n_cyc * period)
            t = w["time"]
            pin = tavg(t, w["v(vin)"] * w["i(vi_in)"])
            vout = tavg(t, w["v(out)"])
            pout = vout * i
            p_sw_node = tavg(t, w["v(sw)"] * w["i(vi_sw)"])
            p_ic = pin - p_sw_node
            dcr = LM_DCR if kind == "lm" else SB_DCR
            if prefix.startswith("01_lmL10"):
                dcr = LM_DCR
            p_l = dcr * tavg(t, w["i(vi_l)"] ** 2)
            p_d = tavg(t, -w["v(sw)"] * w["i(vi_d)"]) if "i(vi_d)" in w else 0.0
            if kind == "lm":
                p_est = 0.5 * vin * i * LM_TSW * LM_FSW
            else:
                p_est = 0.5 * vin * i * SB_TSW * SB_FSW + SB_PDRV
            p_other = pin - pout - p_ic - p_l - p_d
            rows.append({
                "vin_V": vin, "iout_A": i, "vout_V": vout,
                "eff_model": pout / pin, "eff_incl_sw_est": pout / (pin + p_est),
                "pin_W": pin + p_est, "pout_W": pout, "loss_total_W": pin + p_est - pout,
                "loss_ic_W": p_ic, "loss_catch_diode_W": p_d, "loss_inductor_dcr_W": p_l,
                "loss_sw_est_W": p_est, "loss_other_W": p_other,
                "ripple_mVpp": 1e3 * (w["v(out)"].max() - w["v(out)"].min()),
                "il_peak_A": float(w["i(vi_l)"].max()), "il_min_A": float(w["i(vi_l)"].min()),
            })
    return rows


def report_01_04() -> dict:
    lm = analyse_sweep("01_lm", (9.0, 12.0), "lm")
    lm10 = analyse_sweep("01_lmL10", (12.0,), "lm")
    sb = analyse_sweep("04_sb", (9.0, 12.0), "sb")
    write_csv("01_lm2576_sweep.csv", lm)
    write_csv("01_lm2576_sweep_isat10A.csv", lm10)
    write_csv("04_syncbuck_sweep.csv", sb)
    plt = plt_setup()
    # efficiency
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    series = [
        ("LM2576, 12 V in, L1 Isat 2 A (assumed; = green up to 4 A)", [r for r in lm if r["vin_V"] == 12.0]),
        ("LM2576, 9 V in", [r for r in lm if r["vin_V"] == 9.0]),
        ("LM2576, 12 V in, non-saturating L1", lm10),
        ("Sync buck 5 V/5 A, 12 V in", [r for r in sb if r["vin_V"] == 12.0]),
    ]
    notes = []
    for k, (lab, rows) in enumerate(series):
        ok = [r for r in rows if r["vout_V"] > 4.9]
        lost = [r for r in rows if r["vout_V"] <= 4.9]
        ax.plot([r["iout_A"] for r in ok], [100 * r["eff_incl_sw_est"] for r in ok],
                color=SERIES[k], marker="o", label=lab)
        notes += [f"{lab.split(',')[0]} {r['vin_V']:g} V in, {r['iout_A']} A: current limit, "
                  f"5 V falls to {r['vout_V']:.1f} V (not plotted)" for r in lost]
    if notes:
        ax.text(0.99, 0.6, "\n".join(notes), transform=ax.transAxes, ha="right", va="top",
                fontsize=8, color=INK2)
    ax.set_xlabel("Output current (A)")
    ax.set_ylabel("Efficiency (%)")
    ax.set_title("5 V regulator efficiency (incl. estimated switching loss)", loc="left")
    ax.set_xticks([1, 2, 3, 4, 5])
    ax.legend(loc="lower left")
    fig.tight_layout()
    fig.savefig(RES / "01_efficiency.png", dpi=110)
    plt.close(fig)
    # loss breakdown (12 V), stacked bars LM2576 vs sync buck
    fig, axs = plt.subplots(1, 2, figsize=(8.5, 3.8), sharey=True)
    parts = [("loss_ic_W", "Regulator IC (switch / FETs, Iq)"), ("loss_catch_diode_W", "Catch diode D13"),
             ("loss_inductor_dcr_W", "Inductor DCR"), ("loss_sw_est_W", "Switching (estimate) + other")]
    for ax, (title, rows) in zip(axs, (("LM2576-5 (current board)", series[0][1]),
                                       ("Synchronous buck (proposed)", series[3][1]))):
        x = np.array([r["iout_A"] for r in rows], dtype=float)
        bottom = np.zeros_like(x)
        for k, (key, lab) in enumerate(parts):
            vals = np.array([r[key] + (r["loss_other_W"] if key == "loss_sw_est_W" else 0.0) for r in rows])
            ax.bar(x, vals, bottom=bottom, width=0.6, color=SERIES[k], edgecolor=SURF, linewidth=1.5, label=lab)
            bottom += vals
        for xi, b in zip(x, bottom):
            ax.annotate(f"{b:.1f} W", (xi, b), xytext=(0, 2), textcoords="offset points",
                        ha="center", fontsize=8, color=INK2)
        ax.set_title(f"{title}, 12 V in", loc="left")
        ax.set_xlabel("Output current (A)")
        ax.set_xticks(x)
    axs[0].set_ylabel("Power loss (W)")
    axs[0].legend(loc="upper left")
    fig.tight_layout()
    fig.savefig(RES / "01_losses.png", dpi=110)
    plt.close(fig)
    # waveforms at 3 A / 12 V: inductor current and output ripple
    fig, axs = plt.subplots(1, 2, figsize=(8.5, 3.4))
    for k, (name, lab) in enumerate((("01_lm_v12_i3", "L1 Isat 2 A (assumed)"),
                                     ("01_lmL10_v12_i3", "non-saturating L1"))):
        d = load(name)
        w = window(d, d["time"][-1] - 100e-6)
        t_us = (w["time"] - w["time"][0]) * 1e6
        axs[0].plot(t_us, w["i(vi_l)"], color=SERIES[k], label=lab)
        axs[1].plot(t_us, 1e3 * (w["v(out)"] - w["v(out)"].mean()), color=SERIES[k], label=lab)
    axs[0].set_title("LM2576 inductor current, 3 A load", loc="left")
    axs[0].set_ylabel("Current (A)")
    axs[1].set_title("Output ripple (AC), 3 A load", loc="left")
    axs[1].set_ylabel("Voltage (mV)")
    for ax in axs:
        ax.set_xlabel("Time (µs)")
    axs[0].legend(loc="upper right")
    fig.tight_layout()
    fig.savefig(RES / "01_waveforms.png", dpi=110)
    plt.close(fig)
    cols = ["vin_V", "iout_A", "eff_incl_sw_est", "loss_total_W", "loss_ic_W", "loss_catch_diode_W",
            "loss_inductor_dcr_W", "ripple_mVpp", "il_peak_A"]
    return {"01": md_table(lm, cols), "01L10": md_table(lm10, cols), "04": md_table(sb, cols)}


# --------------------------------------------------------------------------
# 02: D15 vs P-MOSFET, PTC
# --------------------------------------------------------------------------
def report_02() -> dict:
    d25, d75 = load("02_dc", "data_25.txt"), load("02_dc", "data_75.txt")
    i = d25["v-sweep"]
    rows = []
    for cur in (0.5, 1.0, 2.0, 3.0, 4.0, 5.0):
        k = int(np.argmin(abs(i - cur)))
        rows.append({"i_A": cur,
                     "vf_d15_25C_V": d25["vf_d15"][k], "p_d15_25C_W": cur * d25["vf_d15"][k],
                     "vf_d15_75C_V": d75["vf_d15"][k], "p_d15_75C_W": cur * d75["vf_d15"][k],
                     "vds_pfet_25C_V": d25["vf_pfet"][k], "p_pfet_25C_W": cur * d25["vf_pfet"][k],
                     "vds_pfet_75C_V": d75["vf_pfet"][k], "p_pfet_75C_W": cur * d75["vf_pfet"][k]})
    write_csv("02_d15_vs_pfet.csv", rows)
    plt = plt_setup()
    fig, axs = plt.subplots(1, 2, figsize=(8.5, 3.6))
    for k, (dd, key, lab) in enumerate(((d25, "vf_d15", "D15 SK24A, 25 °C"), (d75, "vf_d15", "D15 SK24A, 75 °C"),
                                        (d25, "vf_pfet", "P-MOSFET 12 mΩ, 25 °C"),
                                        (d75, "vf_pfet", "P-MOSFET, 75 °C"))):
        axs[0].plot(i, dd[key], color=SERIES[k], label=lab)
        axs[1].plot(i, i * dd[key], color=SERIES[k], label=lab)
    axs[0].set_title("Forward drop vs current", loc="left")
    axs[0].set_ylabel("Voltage (V)")
    axs[1].set_title("Dissipated power vs current", loc="left")
    axs[1].set_ylabel("Power (W)")
    for ax in axs:
        ax.set_xlabel("Current (A)")
    axs[0].legend(loc="center right")
    fig.tight_layout()
    fig.savefig(RES / "02_d15_vs_pfet.png", dpi=110)
    plt.close(fig)

    ptc = []
    for ta in (25, 50):
        for cur in (2.0, 2.5, 3.0, 3.5, 4.0, 5.0):
            d = load(f"02_ptc_ta{ta}_i{fmt(cur)}")
            t, vf, vpi, tj, ii = d["time"], d["v(vf)"], d["v(vpi)"], d["v(tj)"], d["i(vi_f)"]
            r = (5.0 - vf) / np.maximum(ii, 1e-9)
            trip = first_cross_below(t, -r, -1.0)  # first time R > 1 ohm
            k10 = int(np.argmin(abs(t - 10.0)))
            ptc.append({"ta_C": ta, "i_A": cur, "trip_time_s": trip if trip is not None else "no trip (300 s)",
                        "drop_ptc_at_10s_V": 5.0 - vf[k10], "p_ptc_at_10s_W": (5.0 - vf[k10]) * ii[k10],
                        "vpi_at_10s_V": vpi[k10], "t_ptc_max_C": float(tj.max())})
    write_csv("02_ptc_trip.csv", ptc)
    d = load("02_ptc_stairs")
    fig, axs = plt.subplots(1, 2, figsize=(8.5, 3.4))
    axs[0].plot(d["time"], d["v(vpi)"], color=SERIES[0])
    axs[0].axhline(PI_UV, color=INK2, linewidth=0.8, linestyle="--")
    axs[0].annotate("Pi under-voltage ~4.63 V", (5, PI_UV), xytext=(0, 3), textcoords="offset points",
                    fontsize=8, color=INK2)
    axs[0].set_ylim(0, 5.2)
    axs[0].set_title("Pi supply voltage after F1 + header", loc="left")
    axs[0].set_ylabel("Voltage (V)")
    axs[1].plot(d["time"], d["v(tj)"], color=SERIES[1])
    axs[1].set_title("F1 PTC body temperature", loc="left")
    axs[1].set_ylabel("Temperature (°C)")
    for ax in axs:
        ax.set_xlabel("Time (s); load 1 → 2 → 2.5 → 3 → 3.5 A every 60 s")
    fig.tight_layout()
    fig.savefig(RES / "02_ptc_staircase.png", dpi=110)
    plt.close(fig)
    return {"02dc": md_table(rows, list(rows[0].keys())),
            "02ptc": md_table(ptc, list(ptc[0].keys()))}


# --------------------------------------------------------------------------
# 03 / 04b: load steps
# --------------------------------------------------------------------------
def cycle_avg(t: np.ndarray, y: np.ndarray, period: float) -> np.ndarray:
    dt = np.median(np.diff(t))
    n = max(1, int(round(period / dt)))
    k = np.ones(n) / n
    padded = np.pad(y, (n // 2, n - 1 - n // 2), mode="edge")
    return np.convolve(padded, k, mode="valid")


def report_steps() -> dict:
    rows = []
    named = {}
    for name, period, label in (("03_step_pi3_soc0.5", 1 / LM_FSW, "current board"),
                                ("03_step_pi3_soc0.1", 1 / LM_FSW, "current board"),
                                ("03_step_pi3_soc0.5_gm3", 1 / LM_FSW, "current board, 3x faster loop"),
                                ("03_step_pi3_soc0.5_l10", 1 / LM_FSW, "current board, non-saturating L1"),
                                ("04b_step_pi3_soc0.5", 1 / SB_FSW, "proposed"),
                                ("04b_step_pi5_soc0.5", 1 / SB_FSW, "proposed"),
                                ("04b_step_pi5_soc0.1", 1 / SB_FSW, "proposed")):
        d = load(name)
        t = d["time"]
        named[name] = d
        pi = 5 if "_pi5" in name else 3
        soc = 0.1 if "soc0.1" in name else 0.5
        before = t < 8e-3
        after_pi = (t >= 8e-3) & (t < 20e-3)
        after_mot = t >= 20e-3
        vpi_avg = cycle_avg(t, d["v(vpi)"], period)
        il_avg = cycle_avg(t, d["i(vi_l)"], period)
        dtt = np.median(np.diff(t))
        rows.append({
            "case": name, "stage": label, "pi_step_A": pi, "soc": soc,
            "vpi_before_V": float(np.mean(d["v(vpi)"][(t > 7e-3) & before])),
            "vpi_min_pi_step_V": float(d["v(vpi)"][after_pi].min()),
            "vpi_settled_V": float(np.mean(d["v(vpi)"][(t > 18e-3) & after_pi])),
            "vpi_min_motor_step_V": float(d["v(vpi)"][after_mot].min()),
            "vout5_min_V": float(d["v(out)"][t >= 8e-3].min()),
            "time_vpi_below_4.63V_ms": 1e3 * dtt * float(np.sum((vpi_avg < PI_UV) & (t >= 8e-3))),
            "vcc_min_V": float(d["v(vcc)"][t >= 8e-3].min()),
            "il_peak_A": float(d["i(vi_l)"].max()),
            "il_avg_settled_A": float(np.mean(il_avg[(t > 30e-3)])),
            "ibat_peak_A": float(d["i(vi_bat)"].max()),
            "imotor_each_end_A": float(d["i(v.xm1.vim)"][-1]),
        })
    write_csv("03_04_load_steps.csv", rows)
    # downsampled waveforms (10 us) for the two main cases
    for name in ("03_step_pi3_soc0.5", "04b_step_pi3_soc0.5", "04b_step_pi5_soc0.5"):
        d = named[name]
        t = d["time"]
        period = 1 / LM_FSW if name.startswith("03") else 1 / SB_FSW
        grid = np.arange(0, t[-1], 10e-6)
        cols = {"time_s": grid}
        for key in ("v(bat)", "i(vi_bat)", "v(vcc)", "v(out)", "v(vpi)", "i(vi_l)"):
            cols[key + "_avg"] = np.interp(grid, t, cycle_avg(t, d[key], period))
        with open(RES / f"{name}_waveforms.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(cols.keys())
            for r in zip(*cols.values()):
                w.writerow([f"{v:.5g}" for v in r])
    plt = plt_setup()
    fig, axs = plt.subplots(3, 1, figsize=(8, 7.5), sharex=True)
    for k, (name, lab) in enumerate((("03_step_pi3_soc0.5", "Current board: D15 + LM2576 + F1, 1 header pin"),
                                     ("04b_step_pi3_soc0.5", "Proposed: P-MOSFET + sync buck, 2 header pins"))):
        d = named[name]
        t = d["time"] * 1e3
        period = 1 / LM_FSW if name.startswith("03") else 1 / SB_FSW
        axs[0].plot(t, cycle_avg(d["time"], d["v(vpi)"], period), color=SERIES[k], label=lab)
        axs[1].plot(t, cycle_avg(d["time"], d["v(vcc)"], period), color=SERIES[k], label=lab)
        axs[2].plot(t, cycle_avg(d["time"], d["i(vi_bat)"], period), color=SERIES[k], label=lab)
    axs[0].axhline(PI_UV, color=INK2, linewidth=0.8, linestyle="--")
    axs[0].annotate("Pi under-voltage ~4.63 V", (0.5, PI_UV), xytext=(0, -10), textcoords="offset points",
                    fontsize=8, color=INK2)
    axs[0].set_title("Raspberry Pi supply (cycle-averaged)", loc="left")
    axs[0].set_ylabel("Voltage (V)")
    axs[1].set_title("VCC (motor / regulator input)", loc="left")
    axs[1].set_ylabel("Voltage (V)")
    axs[2].set_title("Battery current (3S Li-ion, 50 % SOC)", loc="left")
    axs[2].set_ylabel("Current (A)")
    axs[2].set_xlabel("Time (ms); Pi load 0 → 3 A at 8 ms, two stalled motors at 20 ms")
    axs[0].legend(loc="lower right")
    fig.tight_layout()
    fig.savefig(RES / "03_load_step.png", dpi=110)
    plt.close(fig)
    cols = list(rows[0].keys())
    return {"03": md_table(rows, cols)}


# --------------------------------------------------------------------------
# 05: battery run time
# --------------------------------------------------------------------------
def report_05() -> dict:
    rows = []
    curves = {}
    for src, ns, cut, cut_rec in (("2S", 2, 3.0, 3.2), ("3S", 3, 3.0, 3.2), ("8AA", 8, 1.0, 1.0)):
        for topo in (1, 2):
            for pi in ("pi5", "pi4"):
                name = f"05_bat_{src}_t{topo}_{pi}"
                d = load(name)
                t, vb, ib, vpi, soc = d["time"], d["v(bat)"], d["i(vi_bat)"], d["v(vpi)"], d["v(soc)"]
                t_cut = first_cross_below(t, vb / ns, cut)
                t_rec = first_cross_below(t, vb / ns, cut_rec)
                t_rail = first_cross_below(t, vpi, 4.75)
                ends = [x for x in (t_cut, t_rail) if x is not None]
                t_end = min(ends) if ends else float(t[-1])
                k_end = int(np.argmin(abs(t - t_end)))
                reason = "rail < 4.75 V" if (t_rail is not None and t_end == t_rail) else (
                    "cell cut-off" if t_cut is not None else "end of sim")
                k1 = int(np.argmin(abs(t - 600)))
                p_bat = vb[k1] * ib[k1]
                i5 = 2.0 if pi == "pi5" else 1.2
                p_mot = 0.3 * d["v(vcc)"][k1]
                rows.append({
                    "source": src, "stage": "current" if topo == 1 else "proposed", "load": pi,
                    "p_battery_W_at_10min": float(p_bat),
                    "p_pi_W": float(vpi[k1] * i5),
                    "eff_5V_path_at_10min": float(vpi[k1] * i5 / (p_bat - p_mot)),
                    "runtime_h": t_end / 3600, "ends_by": reason,
                    "soc_left_at_end": float(max(soc[k_end], 0.0)),
                    "t_to_recommended_cutoff_h": (t_rec / 3600) if t_rec is not None else float("nan"),
                })
                curves[name] = (t, vb, vpi, t_end)
    write_csv("05_battery_runtime.csv", rows)
    plt = plt_setup()
    labels = {"2S": "2S Li-ion 18650", "3S": "3S Li-ion 18650", "8AA": "8×AA NiMH"}
    for key, fname, ylab, ylim, title in (
            ("vpi", "05_battery_pi_voltage.png", "Voltage at the Pi (V)", (4.0, 5.1), "Pi 5 supply voltage"),
            ("cell", "05_battery_cells.png", "Loaded voltage per cell (V)", None, "Battery voltage per cell")):
        fig, axs = plt.subplots(1, 2, figsize=(9, 3.8), sharey=True)
        for ax, topo, stage in ((axs[0], 1, "Current board"), (axs[1], 2, "Proposed stage")):
            for k, src in enumerate(("2S", "3S", "8AA")):
                t, vb, vpi, t_end = curves[f"05_bat_{src}_t{topo}_pi5"]
                ns = {"2S": 2, "3S": 3, "8AA": 8}[src]
                m = t <= t_end
                y = vpi if key == "vpi" else vb / ns
                ax.plot(t[m] / 3600, y[m], color=SERIES[k], label=labels[src])
                ax.plot([t[m][-1] / 3600], [y[m][-1]], marker="o", color=SERIES[k], markeredgecolor=SURF)
            if key == "vpi":
                ax.axhline(4.75, color=INK2, linewidth=0.8, linestyle="--")
                ax.annotate("4.75 V", (0.02, 4.75), xytext=(0, -10), textcoords="offset points",
                            fontsize=8, color=INK2)
            ax.set_title(f"{stage}: {title}", loc="left")
            ax.set_xlabel("Time (h); dot = end of run")
            if ylim:
                ax.set_ylim(*ylim)
        axs[0].set_ylabel(ylab)
        axs[0].legend(loc="lower left")
        fig.suptitle("Pi 5 at 2 A + board 3V3/9V + motors 0.3 A average", x=0.01, ha="left",
                     fontsize=9, color=INK2)
        fig.tight_layout()
        fig.savefig(RES / fname, dpi=110)
        plt.close(fig)
    return {"05": md_table(rows, list(rows[0].keys()))}


# --------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", default="", help="run only cases whose name starts with this prefix")
    ap.add_argument("--force", action="store_true", help="re-run cached cases")
    ap.add_argument("--jobs", type=int, default=os.cpu_count() or 2)
    ap.add_argument("--no-report", action="store_true", help="only run ngspice")
    args = ap.parse_args()
    todo = [c for c in cases() if c[0].startswith(args.only)]
    # longest first
    todo.sort(key=lambda c: c[1].startswith(("05", "02")))
    failed = 0
    with cf.ThreadPoolExecutor(max_workers=args.jobs) as ex:
        futs = {ex.submit(run_case, n, cir, p, args.force): n for n, cir, p in todo}
        for f in cf.as_completed(futs):
            try:
                print(f.result(), flush=True)
            except Exception as e:  # noqa: BLE001
                failed += 1
                print(f"FAILED {e}", file=sys.stderr, flush=True)
    if failed:
        return 1
    if args.no_report or args.only:
        return 0
    RES.mkdir(exist_ok=True)
    tables = {}
    tables.update(report_01_04())
    tables.update(report_02())
    tables.update(report_steps())
    tables.update(report_05())
    with open(OUT / "tables.md", "w") as f:
        for k, v in tables.items():
            f.write(f"## {k}\n\n{v}\n\n")
    print(f"results written to {RES.relative_to(HERE.parent.parent)}/, tables in out/tables.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
