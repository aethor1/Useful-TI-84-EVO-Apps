"""Drive the real UI code headlessly with fake ti_draw/ti_system modules,
pressing keys exactly like on the calculator."""
import os
import sys
import types
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Fake Evo screen: a 320x210 pixel grid, so partial repaints can be compared
# with a from-scratch render. Text paints each character's 10x15 cell.
FB = [None]
COLOR = [None]


def blank():
    return [[None] * 320 for _ in range(210)]


def plot(x0, y0, x1, y1, v):
    x0, y0, x1, y1 = max(x0, 0), max(y0, 0), min(x1, 319), min(y1, 209)
    if x0 > x1:
        return
    for y in range(y0, y1 + 1):
        FB[0][y][x0:x1 + 1] = [v] * (x1 - x0 + 1)


def fake_fill(x, y, w, h):
    # Evo raises tidrawException for a 1-px (or smaller) fill, paints inside the border
    assert w >= 2 and h >= 2, "fill_rect size %r x %r" % (w, h)
    plot(x + 1, y + 1, x + w - 1, y + h - 1, COLOR[0])


def fake_line(x1, y1, x2, y2):
    assert x1 == x2 or y1 == y2, "diagonal line"
    plot(min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2), COLOR[0])


def fake_text(x, y, s):
    for i, ch in enumerate(s):
        plot(x + i * 10, y - 17, x + i * 10 + 9, y - 3, (ch, COLOR[0]))


fake = types.ModuleType("ti_draw")
fake.set_color = lambda r, g, b: COLOR.__setitem__(0, (r, g, b))
fake.fill_rect = fake_fill
fake.draw_line = fake_line
fake.draw_text = fake_text
sys.modules["ti_draw"] = fake
FB[0] = blank()

import stoich_ui as ui  # noqa: E402
from chemcore import num_text, candidates  # noqa: E402

KEY_OF = {}
for code, letter in ui.LETTER_KEYS.items():
    KEY_OF.setdefault(letter, code)
DIG = {str(v): k for k, v in ui.DIGIT_KEYS.items()}
PUNCT = {"(": [ui.K_LPAR], ")": [ui.K_RPAR], "*": [ui.K_DOT], ".": [ui.K_DOT],
         "E": [ui.K_COMMA], "-": [ui.K_NEG], "[": [ui.K_2ND, ui.K_LPAR],
         "]": [ui.K_2ND, ui.K_RPAR]}


def tokens(f):
    out = []
    i = 0
    while i < len(f):
        if f[i].isupper():
            j = i + 1
            if j < len(f) and f[j].islower():
                j += 1
            out.append(f[i:j])
            i = j
        else:
            out.append(f[i])
            i += 1
    return out


def num_keys(text):
    out = []
    for c in text:
        out += PUNCT[c] if c in PUNCT else [DIG[c]]
    return out


class UIFlow(unittest.TestCase):
    def setUp(self):
        self.app = ui.App()
        self.app.draw()
        self.presses = 0

    def press(self, *ks):
        for k in ks:
            self.app.key(k)
            self.presses += 1
            self.check_fits()

    def check_fits(self):
        if not self.app.running:
            return
        for o in ui._shown[0]:
            if o[0] != ui.TXT:
                continue
            x, y, s = o[1], o[2], o[3]   # layout y: glyphs fill y .. y+14
            self.assertGreaterEqual(y, 0, "%s: %r above screen" % (self.app.scr, s))
            self.assertLessEqual(y + 14, ui.H - 1, "%s: %r below screen" % (self.app.scr, s))
            if self.app.scr == "ans" and y < 80:
                continue        # the chain line scrolls; off-screen parts are expected
            self.assertGreaterEqual(x, 0, "%s: %r" % (self.app.scr, s))
            self.assertLessEqual(x + len(s) * ui.CW, ui.W + 1,
                                 "text runs off screen on %s: %r" % (self.app.scr, s))
        # the partial repaint must leave exactly what a full redraw would
        shown = FB[0]
        FB[0] = blank()
        ui.paint((0, 0, ui.W - 1, ui.H - 1), ui._shown[0])
        full = FB[0]
        FB[0] = shown
        for y in range(ui.H):
            if shown[y] != full[y]:
                x = next(i for i in range(ui.W) if shown[y][i] != full[y][i])
                self.fail("%s: stale pixel at (%d, %d): %r vs %r"
                          % (self.app.scr, x, y, shown[y][x], full[y][x]))

    def type_symbol(self, sym):
        self.press(KEY_OF[sym[0]])
        a = self.app
        if a.pick is not None:
            c = a.pick[0]
            while c[a.pick[1]] != sym:
                self.press(ui.K_DOWN)
            if a.pick[1] != 0:
                self.press(ui.K_ENTER)
            # index 0 (the 1-letter element) is accepted by the next key

    def type_formula(self, f):
        a = self.app
        for t in tokens(f):
            if t[0].isupper():
                if a.fnum:
                    self.press(ui.K_VARX)
                self.type_symbol(t)
            else:
                if not a.fnum and a.pick is None:
                    self.press(ui.K_VARX)
                elif a.pick is not None:
                    # accept the default pick by pressing [x,t,0,n] -> switches to 123
                    self.press(ui.K_VARX)
                self.press(*num_keys(t))
        if a.pick is not None:
            self.press(ui.K_ENTER)

    def solve_formula(self, formula, given, gu, gw_idx, fu, fw_idx):
        """gu/fu are unit digits as listed for the compound: 1 g 2 mol 3 molec 4 f.u. 5 atoms"""
        a = self.app
        self.press(DIG["1"])                       # menu -> formula entry
        self.type_formula(formula)
        self.assertEqual(a.ftext, formula)
        self.press(ui.K_ENTER)                     # -> problem
        self.assertEqual(a.scr, "prob", a.msg)
        self.press(*num_keys(given))
        self.press(ui.K_DOWN, DIG[str(gu)])
        self.press(ui.K_DOWN, DIG[str(gw_idx)])
        self.press(ui.K_DOWN, DIG[str(fu)])
        self.press(ui.K_DOWN, DIG[str(fw_idx)])
        self.press(ui.K_ENTER)
        self.assertEqual(a.scr, "ans", a.msg)
        return num_text(a.res["answer"])

    def test_problem_16_through_ui(self):
        # g H in 4.50 g NH3 (precise masses: NH3 17.031, H 1.008; table masses give 0.800)
        self.assertEqual(self.solve_formula("NH3", "4.50", 1, 0, 1, 2), "0.799")

    def test_problem_14_through_ui(self):
        self.assertEqual(self.solve_formula("Na2SO4", "14.2", 1, 0, 3, 1), "1.20x10^23")

    def test_unit_row_lists_every_particle(self):
        a = self.app
        self.press(DIG["1"])
        self.type_formula("H2O")
        self.press(ui.K_ENTER, ui.K_DOWN, DIG["4"])         # given unit: f.u.
        self.assertEqual((a.gu, a.cmp.ptype), (ui.PT, "formula units"))
        self.press(ui.K_RIGHT)                               # -> atoms
        self.assertEqual(a.cmp.ptype, "atoms")
        self.press(ui.K_RIGHT)                               # wraps to g
        self.assertEqual(a.gu, ui.G)
        self.press(ui.K_DOWN, DIG["1"], ui.K_UP)             # of: H -> only g mol atoms
        self.assertEqual(len(a.unit_opts(a.gw)), 3)
        self.press(ui.K_LEFT)                                # g -> atoms
        self.assertEqual(a.gu, ui.PT)
        self.assertEqual(a.unit_word(a.gu, a.gw), "atoms")

    def test_problem_4_through_ui(self):
        self.assertEqual(self.solve_formula("C6H12O6", "7.5E24", 3, 2, 2, 0), "1.0")

    def test_precise_only(self):
        self.solve_formula("SO2", "9.03E23", 3, 0, 2, 0)
        self.assertEqual(self.app.res["steps"][0][4], ("6.02214076", 23))
        self.assertEqual(num_text(self.app.res["answer"]), "1.50")
        shown = " ".join(o[3] for o in ui._shown[0] if o[0] == ui.TXT)
        self.assertIn("M=64.058", shown)                    # full atomic weights
        self.assertNotIn("6.02x10", shown.replace("6.02214076", ""))

    def test_nh4no3_needs_no_picker_enter(self):
        self.press(DIG["1"])
        start = self.presses
        self.type_formula("NH4NO3")
        # N H [x] 4 [x] N O [x] 3 -> 9 presses, no extra [enter]s
        self.assertEqual(self.presses - start, 9)
        self.assertEqual(self.app.ftext, "NH4NO3")

    def test_picker_two_letter(self):
        self.press(DIG["1"])
        self.press(KEY_OF["C"])
        self.assertEqual(self.app.pick[0][:4], ["C", "Cl", "Ca", "Cu"])
        self.press(ui.K_DOWN, ui.K_ENTER)
        self.assertEqual(self.app.ftext, "Cl")

    def test_picker_most_common_first(self):
        self.assertEqual(candidates("A")[:3], ["Al", "Ag", "Au"])
        self.assertEqual(candidates("V"), ["V"])
        self.assertEqual(candidates("J"), [])

    def test_cobalt_vs_carbon_monoxide(self):
        self.press(DIG["1"])
        self.type_formula("CoCl2")
        self.assertEqual(self.app.ftext, "CoCl2")
        self.press(ui.K_CLEAR)
        self.type_formula("CO")
        self.assertEqual(self.app.ftext, "CO")

    def test_parens_and_hydrate(self):
        self.press(DIG["1"])
        self.type_formula("(NH4)3PO4")
        self.press(ui.K_ENTER)
        self.assertEqual(self.app.cmp.counts["H"], 12)
        self.press(ui.K_F1, ui.K_CLEAR)
        self.type_formula("CuSO4*5H2O")
        self.press(ui.K_ENTER)
        self.assertEqual(self.app.cmp.counts["O"], 9)

    def test_backspace_removes_whole_symbol(self):
        self.press(DIG["1"])
        self.type_formula("NaCl")
        self.press(ui.K_DEL)
        self.assertEqual(self.app.ftext, "Na")

    def test_lazy_mode_auto_letters_and_separator(self):
        a = self.app
        self.press(DIG["2"])
        self.type_symbol("N")
        self.press(ui.K_VARX)
        self.type_symbol("H")
        self.press(ui.K_VARX)
        self.press(KEY_OF["O"])           # [7] key types O in lazy mode
        self.press(ui.K_ENTER)            # accept pick
        self.assertEqual(a.ltext, "N,H,O")
        self.press(ui.K_ENTER)
        self.assertEqual(a.lsyms, ["N", "H", "O"])
        self.press(DIG["2"], ui.K_DOWN, DIG["4"], ui.K_DOWN, ui.K_RIGHT, ui.K_RIGHT)
        self.press(ui.K_ENTER)
        self.assertEqual(a.cmp.formula, "N2H4O3")

    def test_answer_scrolls_and_stays_one_line(self):
        self.solve_formula("(NH4)3PO4", "1.2345E-3", 3, 2, 1, 3)
        self.assertGreater(self.app.max_scroll(), 0)
        while self.app.hscroll < self.app.max_scroll():
            self.press(ui.K_RIGHT)
        self.press(ui.K_LEFT)
        self.assertLess(self.app.hscroll, self.app.max_scroll())

    def test_scroll_diff_is_cheap(self):
        # the old diff did ~10k rect checks per scroll click (~1 s on the Evo)
        self.solve_formula("Na2SO4", "14.2", 1, 0, 5, 3)
        calls = [0]
        painted = []
        real, real_paint = ui._hit, ui.paint
        ui._hit = lambda a, b: (calls.__setitem__(0, calls[0] + 1), real(a, b))[1]
        ui.paint = lambda r, ops: (painted.append(r), real_paint(r, ops))
        try:
            self.app.key(ui.K_RIGHT)
        finally:
            ui._hit, ui.paint = real, real_paint
        self.check_fits()
        self.assertLess(calls[0], 1500)
        self.assertTrue(all(r[3] < 79 for r in painted), painted)  # answer rows untouched

    def test_menu_has_no_constants_toggle(self):
        self.assertNotIn("Constants", " ".join(ui.MENU))

    def test_second_key(self):
        self.press(ui.K_2ND, ui.K_2ND)               # toggles off again
        self.assertTrue(self.app.running)
        self.assertFalse(self.app.second)
        self.press(ui.K_ALPHA, DIG["1"])             # [alpha] is ignored
        self.assertEqual(self.app.scr, "formula")
        self.press(ui.K_2ND, ui.K_MODE)              # [2nd][quit]
        self.assertFalse(self.app.running)

    def test_all_screens_draw(self):
        for k in (DIG["2"], ui.K_F1, ui.K_F4):
            self.press(k)
        self.press(DIG["3"])                         # menu 3 = quit
        self.assertFalse(self.app.running)

    def test_moving_cursor_repaints_little(self):
        painted = []
        real = ui.paint
        ui.paint = lambda r, ops: (painted.append(r), real(r, ops))
        try:
            self.app.key(ui.K_DOWN)                  # menu: highlight moves one row
        finally:
            ui.paint = real
        self.check_fits()
        area = sum((r[2] - r[0] + 1) * (r[3] - r[1] + 1) for r in painted)
        self.assertLess(area, ui.W * ui.H // 3, painted)


class Bundle(unittest.TestCase):
    def test_dist_file_runs(self):
        """Build dist/STOICH.py and run it as the calculator would."""
        root = os.path.join(os.path.dirname(__file__), "..")
        sys.path.insert(0, root)
        import build
        path = build.build()
        seq = iter([DIG["1"], KEY_OF["N"], KEY_OF["H"], ui.K_VARX, DIG["3"], ui.K_ENTER]
                   + num_keys("4.50") +
                   [ui.K_DOWN, DIG["1"], ui.K_DOWN, DIG["0"], ui.K_DOWN, DIG["1"],
                    ui.K_DOWN, DIG["2"], ui.K_ENTER, ui.K_RIGHT, ui.K_2ND, ui.K_MODE])
        tis = types.ModuleType("ti_system")
        tis.wait_key = lambda: next(seq)
        sys.modules["ti_system"] = tis
        with open(path, encoding="utf-8") as f:
            src = f.read()
        exec(compile(src, path, "exec"), {"__name__": "__main__"})
        self.assertRaises(StopIteration, next, seq)   # every key consumed


if __name__ == "__main__":
    unittest.main()
