# Vendor SPICE models (not in git)

Manufacturer models are usually licensed for use only, not for redistribution, so they
are **not committed**. Everything in this directory except this file is ignored by git
(`simulation/.gitignore`). The simulations in `../cir/` use the behavioural models from
`../models/brickpi_power.lib` and do not need anything from here.

To cross-check a behavioural model against a vendor model, download it yourself from
the product page, read its licence, and put it here:

All links below are **unverified** (not checked online); product pages may have moved.

| Part | Where to look (unverified) | Notes |
| --- | --- | --- |
| LM2576 | <https://www.ti.com/product/LM2576> → Design & development → Models | PSpice/TINA-TI transient model, TI licence |
| TPS56637 | <https://www.ti.com/product/TPS56637> → Models | PSpice transient model, TI licence |
| MIC5504 | <https://www.microchip.com/en-us/product/MIC5504> | check for a SPICE/Mindi model |
| AP3012 | <https://www.diodes.com/> (search AP3012) | check the SPICE model section |
| SK24A | datasheet manufacturer of the fitted part | many vendors publish diode `.model` cards |
| TB6612FNG | Toshiba product page | no public SPICE model known; IBIS only if any |

Vendor PSpice models often need `set ngbehavior=psa` (ngspice PSpice compatibility),
e.g. in a local `.spiceinit`. Availability was not checked online for this commit.
