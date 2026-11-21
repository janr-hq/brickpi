#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy>=1.24", "matplotlib>=3.7"]
# ///
"""Assert key simulation results stay inside expected ranges (regression guard).

Usage:  uv run simulation/power/check.py [01] [02] [04]

Reads the raw ngspice output in out/ (run `run.sh --only <prefix> --no-report`
first). Families whose data are missing are skipped; exit code is 1 if any check
fails or if nothing could be checked. Ranges are wide (about +-4 points around the
current model values) - they catch broken models, not small drifts.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run  # noqa: E402  (module guarded by __main__, safe to import)

results: list[tuple[bool, str]] = []


def expect(label: str, value: float, lo: float, hi: float) -> None:
    ok = lo <= value <= hi
    results.append((ok, label))
    print(f"{'ok  ' if ok else 'FAIL'} {label}: {value:.4g} (expected {lo:g}..{hi:g})")


def have(prefix: str) -> bool:
    return (run.OUT / prefix / "data.txt").exists()


def check_01() -> bool:
    if not all(have(f"01_lm_v12_i{i}") for i in range(1, 6)):
        return False
    rows = {r["iout_A"]: r for r in run.analyse_sweep("01_lm", (12.0,), "lm")}
    expect("01 LM2576 12 V / 1 A efficiency (%)", 100 * rows[1]["eff_incl_sw_est"], 82, 87)
    expect("01 LM2576 12 V / 3 A efficiency (%)", 100 * rows[3]["eff_incl_sw_est"], 75, 82)
    expect("01 LM2576 12 V / 4 A efficiency (%)", 100 * rows[4]["eff_incl_sw_est"], 72, 79)
    expect("01 LM2576 12 V / 3 A total loss (W)", rows[3]["loss_total_W"], 3.3, 4.9)
    expect("01 LM2576 12 V / 3 A Vout (V)", rows[3]["vout_V"], 4.95, 5.15)
    expect("01 LM2576 12 V / 5 A Vout (V, current limit)", rows[5]["vout_V"], 3.0, 4.4)
    expect("01 LM2576 12 V / 5 A IL peak (A, switch limit)", rows[5]["il_peak_A"], 5.4, 6.2)
    return True


def check_02() -> bool:
    if not (run.OUT / "02_dc" / "data_25.txt").exists():
        return False
    d = run.load("02_dc", "data_25.txt")
    k = int(abs(d["v-sweep"] - 3.0).argmin())
    expect("02 D15 loss @ 3 A, 25 C (W)", 3.0 * d["vf_d15"][k], 1.4, 1.9)
    expect("02 P-MOSFET loss @ 3 A, 25 C (W)", 3.0 * d["vf_pfet"][k], 0.05, 0.2)
    return True


def check_04() -> bool:
    if not all(have(f"04_sb_v12_i{i}") for i in range(1, 6)):
        return False
    rows = {r["iout_A"]: r for r in run.analyse_sweep("04_sb", (12.0,), "sb")}
    expect("04 sync buck 12 V / 3 A efficiency (%)", 100 * rows[3]["eff_incl_sw_est"], 94, 98)
    expect("04 sync buck 12 V / 5 A efficiency (%)", 100 * rows[5]["eff_incl_sw_est"], 93, 98)
    expect("04 sync buck 12 V / 5 A Vout (V)", rows[5]["vout_V"], 4.9, 5.1)
    expect("04 sync buck 12 V / 5 A ripple (mV p-p)", rows[5]["ripple_mVpp"], 2, 25)
    return True


def main() -> int:
    families = sys.argv[1:] or ["01", "02", "04"]
    checkers = {"01": check_01, "02": check_02, "04": check_04}
    checked = 0
    for fam in families:
        if checkers[fam]():
            checked += 1
        else:
            print(f"skip {fam}: no simulation data in out/")
    bad = [label for ok, label in results if not ok]
    print(f"{len(results) - len(bad)}/{len(results)} checks passed")
    if not checked:
        print("nothing was checked", file=sys.stderr)
        return 1
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
