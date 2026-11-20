# STOICH: mole conversions for the TI-84 Evo

Converts between grams, moles and particles for a compound or one element in it, and shows the work as dimensional analysis.

## Files
| Path | What |
|---|---|
| `dist/STOICH.py` | **The file that goes on the calculator** (single file, built from `src/`) |
| `src/KEYTEST.py` | Optional checker program for the calc (key codes + font size) |
| `src/chemdata.py` | Periodic table, all 118 elements |
| `src/chemcore.py` | Parser, molar mass, sig figs, conversion chain (no TI code, PC-testable) |
| `src/stoich_ui.py` | Screens + keys (`ti_draw`, `ti_system`) |
| `tests/` | `python -m unittest discover -s tests` |
| `web/` | Clickable Evo demo (Pyodide runs the same `src/*.py`) |
| `build.py` | Rebuilds `dist/STOICH.py` after you edit `src/` |

## Put it on the Evo
1. Plug the Evo into the PC with USB-C.
2. In **Chrome or Edge**, open **https://connectevo.ti.com** (TI Connect Evo). It uses WebUSB, so Firefox won't work. Allow the USB device when asked.
3. **Send Files → Send to Calculator**, then pick `dist/STOICH.py`. Optionally also send `src/KEYTEST.py`.
4. On the calc, open the **Python** app from the icon menu, pick **STOICH**, then **Run**.

If TI Connect Evo won't take a `.py`, send it with TI Connect CE. That tool converts `.py` to a Python AppVar, and TI says Python programs move between the 84 Python and the Evo.

## First run: check two assumptions with KEYTEST
TI doesn't publish the Evo's `wait_key()` codes or its `ti_draw` font size. STOICH uses the CE Python values.
- Run **KEYTEST** and press keys. It shows the code each key sends and what STOICH thinks that key is, including the green letter each key types in letter fields. If one is wrong, change it in the `K_...` / `LETTER_KEYS` block at the top of `src/stoich_ui.py`, then run `python build.py`.
- The red ticks are 10 px apart. If text is clearly narrower or wider than one tick per character, set `CW` (and `CH`) in `stoich_ui.py`.
- If `×` or `·` shows as junk, set `TIMES = "x"` / `DOT = "*"`.

## Using it
- **Menu**: `1` formula entry, `2` lazy entry, `3` key help, `4` quit.
- **Letters**: in letter fields every key types its **green letter**. A-lock is always on, so there's no [alpha]. If a letter starts more than one symbol, a **pick list** pops up, sorted most common first (C → C, Cl, Ca, Cu, …). Up/down + [enter] picks one. **Just keep typing to take the top choice** (the 1-letter element), so `NH4NO3` needs no extra presses.
- **Formula**: the header chip shows **ABC** or **123**, and **[x,t,θ,n] switches** between them. In 123: digits, `( )`, `[ ]`, and [×] = hydrate dot. After `(` it jumps back to ABC by itself, since an element always follows. [del] erases a whole symbol.
- **Lazy**: letters only, and **[x,t,θ,n] = next element**. Then set the counts with up/down to pick, ◄/► for −1/+1, or digit keys.
- **Masses**: type a number on any row to override it (the compound's molar mass or a single element). [del] resets that row. Overrides are marked `*` and count in both answers.
- **Problem**: up/down picks a row, ◄/► (or digits) picks the option, [enter] solves. In the value field, [2nd][EE] or [×] inserts ×10^ and [(−)] gives a negative exponent. f2 **PTCL** cycles molecules / formula units / atoms.
- **Answer**: the work sits on one line, and **◄/► scrolls it**. Pinned below are both answers: **T** = Teacher (6.02×10²³, masses to 2 decimals), **P** = Precise (6.02214076×10²³, full atomic weights), each with its raw value. The chain shows the Teacher numbers. `1` edit, `2` masses, `3` new problem, `5` menu.

**Sig figs** come from the given value. Counts, Avogadro and molar masses (including your overrides) are treated as exact. Ambiguous trailing zeros (`350`) or more than 6 sig figs fall back to 6.

## Web demo
From the `StoichCalc` folder:
```
python -m http.server 8484
```
Then open http://localhost:8484/web/ (needs internet once to load Pyodide from the CDN).

