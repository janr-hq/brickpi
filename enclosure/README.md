# Enclosure

## Today

`freecad/BrickPi3-case.FCStd` – FreeCAD prototype of a case for the board stacked on a
Raspberry Pi 5 (Feb 2025). The board and Pi geometry are imported STEP bodies inside the file.

Not in the repository: STL export (> 100 MB, regenerate from FreeCAD) and the standalone
board/Pi STEP models.

## Plan

- Parametric case in OpenSCAD or CadQuery (text sources, reviewable diffs), generated STL/3MF
  as CI artifacts.
- Variants for Raspberry Pi 3/4/5.
- Integrated holder for a 3S Li-ion pack with BMS (see `docs/POWER.md`).
- LEGO Technic-compatible mounting holes (8 mm grid, 4.8 mm pins).
