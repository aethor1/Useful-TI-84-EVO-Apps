"""Drive the real UI code headlessly with fake ti_draw/ti_system modules,
pressing keys exactly like on the calculator."""
import os
import sys
import types
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

CALLS = []
fake = types.ModuleType("ti_draw")
fake.clear = lambda: CALLS.clear()
fake.set_color = lambda r, g, b: None
fake.fill_rect = lambda x, y, w, h: None
fake.draw_line = lambda a, b, c, d: None
fake.draw_text = lambda x, y, s: CALLS.append((x, y, s))
sys.modules["ti_draw"] = fake

import stoich_ui as ui  # noqa: E402
from chemcore import num_text, candidates  # noqa: E402

KEY_OF = {}
for code, letter in ui.LETTER_KEYS.items():
    KEY_OF.setdefault(letter, code)
DIG = {str(i): ui.K_0 + i for i in range(10)}
PUNCT = {"(": ui.K_LPAR, ")": ui.K_RPAR, "*": ui.K_MUL, ".": ui.K_DOT, "E": ui.K_EE,
         "-": ui.K_NEG, "[": ui.K_LBRK, "]": ui.K_RBRK}


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
    return [PUNCT[c] if c in PUNCT else DIG[c] for c in text]


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
        for (x, y, s) in CALLS:
            if self.app.scr == "ans" and y < 80:
                continue        # the chain line scrolls; off-screen parts are expected
            self.assertGreaterEqual(x, 0, "%s: %r" % (self.app.scr, s))
            self.assertLessEqual(x + len(s) * ui.CW, ui.W + 1,
                                 "text runs off screen on %s: %r" % (self.app.scr, s))

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

    def solve_formula(self, formula, given, gu, gw_idx, fu, fw_idx, M=None, el=None):
        a = self.app
        self.press(DIG["1"])                       # menu -> formula entry
        self.type_formula(formula)
        self.assertEqual(a.ftext, formula)
        self.press(ui.K_ENTER)                     # -> masses
        self.assertEqual(a.scr, "mass", a.msg)
        if M:
            self.press(*num_keys(M))
            self.press(ui.K_ENTER)
        for sym, v in (el or {}).items():
            idx = a.cmp.order.index(sym) + 1
            while a.msel != idx:
                self.press(ui.K_DOWN)
            self.press(*num_keys(v))
            self.press(ui.K_ENTER)
        self.press(ui.K_ENTER)                     # -> problem
        self.assertEqual(a.scr, "prob")
        self.press(*num_keys(given))
        self.press(ui.K_DOWN, DIG[str(gu)])
        self.press(ui.K_DOWN, DIG[str(gw_idx)])
        self.press(ui.K_DOWN, DIG[str(fu)])
        self.press(ui.K_DOWN, DIG[str(fw_idx)])
        self.press(ui.K_ENTER)
        self.assertEqual(a.scr, "ans", a.msg)
        return num_text(a.res["answer"])

    def test_problem_16_through_ui(self):
        # g H in 4.50 g NH3 (M 17, H 1.008): units 1=g 2=mol 3=particles
        self.assertEqual(self.solve_formula("NH3", "4.50", 1, 0, 1, 2, "17", {"H": "1.008"}), "0.800")

    def test_problem_14_through_ui(self):
        self.assertEqual(self.solve_formula("Na2SO4", "14.2", 1, 0, 3, 1, "142"), "1.20x10^23")

    def test_problem_4_through_ui(self):
        self.assertEqual(self.solve_formula("C6H12O6", "7.5E24", 3, 2, 2, 0), "1.0")

    def test_both_answers(self):
        self.solve_formula("SO2", "9.03E23", 3, 0, 2, 0)
        self.assertEqual(self.app.res["steps"][0][4], ("6.02", 23))
        self.assertEqual(self.app.resp["steps"][0][4], ("6.02214076", 23))
        self.assertEqual(num_text(self.app.resp["answer"]), "1.50")

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

    def test_menu_has_no_constants_toggle(self):
        self.assertNotIn("Constants", " ".join(ui.MENU))

    def test_all_screens_draw(self):
        for k in (DIG["3"], ui.K_CLEAR, DIG["2"], ui.K_F1, ui.K_F4):
            self.press(k)


class Bundle(unittest.TestCase):
    def test_dist_file_runs(self):
        """Build dist/STOICH.py and run it as the calculator would."""
        root = os.path.join(os.path.dirname(__file__), "..")
        sys.path.insert(0, root)
        import build
        path = build.build()
        seq = iter([DIG["1"], KEY_OF["N"], KEY_OF["H"], ui.K_VARX, DIG["3"], ui.K_ENTER,
                    ui.K_ENTER] + num_keys("4.50") +
                   [ui.K_DOWN, DIG["1"], ui.K_DOWN, DIG["0"], ui.K_DOWN, DIG["1"],
                    ui.K_DOWN, DIG["2"], ui.K_ENTER, ui.K_RIGHT, ui.K_QUIT])
        tis = types.ModuleType("ti_system")
        tis.wait_key = lambda: next(seq)
        sys.modules["ti_system"] = tis
        with open(path, encoding="utf-8") as f:
            src = f.read()
        exec(compile(src, path, "exec"), {"__name__": "__main__"})
        self.assertRaises(StopIteration, next, seq)   # every key consumed


if __name__ == "__main__":
    unittest.main()
