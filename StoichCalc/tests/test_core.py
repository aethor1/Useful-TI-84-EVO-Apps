"""PC-side tests for the stoichiometry logic.  Run:  python -m unittest -v"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from chemcore import (TEACHER, PRECISE, G, MOL, PT, ChemError, compound_from_formula,
                      compound_from_counts, parse_formula, parse_symbols, parse_num,
                      fmt_sig, num_text, solve, molar_mass, elem_mass)
from chemdata import SYMS


def run(formula, given, gu, gw, fu, fw, M=None, el=None, mode=TEACHER):
    c = compound_from_formula(formula)
    if M:
        c.mass_ov = M
    if el:
        c.el_ov.update(el)
    return solve(c, mode, given, gu, gw, fu, fw)


# (id, formula, given, gu, gw, fu, fw, M override, element overrides, expected text)
SHEET = [
    (1, "CH4", "3.5E2", MOL, None, MOL, "H", None, None, "1.4x10^3"),
    (2, "Ca(OH)2", "42.5", MOL, None, MOL, "O", None, None, "85.0"),
    (3, "C6H12O6", "4.80", MOL, "C", MOL, None, None, None, "0.800"),
    (4, "C6H12O6", "7.5E24", PT, "H", MOL, None, None, None, "1.0"),
    (7, "KCl", "6.2", MOL, None, G, None, "74.548", None, "4.6x10^2"),
    (8, "H2SO4", "125.0", G, None, MOL, None, "98.08", None, "1.274"),
    (13, "CO2", "2.4E2", G, None, PT, None, "42", None, "3.4x10^24"),
    (14, "Na2SO4", "14.2", G, None, PT, "Na", "142", None, "1.20x10^23"),
    (15, "CaCl2", "0.15", MOL, None, G, "Cl", None, {"Cl": "35.45"}, "11"),
    (16, "NH3", "4.50", G, None, G, "H", "17", {"H": "1.008"}, "0.800"),
    (17, "SO2", "9.03E23", PT, None, MOL, None, None, None, "1.50"),
    (18, "N2O5", "2.3", MOL, None, PT, "O", None, None, "6.9x10^24"),
    (19, "KBr", "1.8E24", PT, None, G, None, "119.00", None, "3.6x10^2"),
    (20, "NH4NO3", "25.0", G, None, G, "N", "80.043", {"N": "14"}, "8.75"),
]


class SheetProblems(unittest.TestCase):
    def test_sheet(self):
        for (pid, f, gv, gu, gw, fu, fw, M, el, exp) in SHEET:
            with self.subTest(problem=pid):
                r = run(f, gv, gu, gw, fu, fw, M, el)
                self.assertEqual(num_text(r["answer"]), exp)
                self.assertEqual(r["unit"], (fu, fw))

    def test_teacher_kbr_mass_without_override(self):
        c = compound_from_formula("KBr")
        self.assertEqual(molar_mass(c, TEACHER)[1], "119.00")

    def test_precise_mode_changes_constants(self):
        r = run("SO2", "9.03E23", PT, None, MOL, None, mode=PRECISE)
        self.assertEqual(r["steps"][0][4], ("6.02214076", 23))
        self.assertEqual(num_text(r["answer"]), "1.50")
        c = compound_from_formula("NH3")
        self.assertEqual(molar_mass(c, PRECISE)[1], "17.031")
        self.assertEqual(molar_mass(c, TEACHER)[1], "17.04")  # 14.01 + 3*1.01

    def test_chain_shape_g_to_g_element(self):
        r = run("NH3", "4.50", G, None, G, "H", "17", {"H": "1.008"})
        units = [(s[2], s[5]) for s in r["steps"]]
        self.assertEqual(units, [((MOL, None), (G, None)),
                                 ((MOL, "H"), (MOL, None)),
                                 ((G, "H"), (MOL, "H"))])
        self.assertEqual(r["steps"][0][4], ("17", None))

    def test_element_to_other_element(self):
        # mol H -> mol O in H2O goes through the compound
        r = run("H2O", "4.0", MOL, "H", MOL, "O")
        self.assertEqual(len(r["steps"]), 2)
        self.assertEqual(num_text(r["answer"]), "2.0")

    def test_same_given_find(self):
        with self.assertRaises(ChemError):
            run("H2O", "1", MOL, None, MOL, None)


class Parser(unittest.TestCase):
    def counts(self, f):
        c, o = parse_formula(f)
        return [(k, c[k]) for k in o]

    def test_ammonium_phosphate(self):
        self.assertEqual(self.counts("(NH4)3PO4"), [("N", 3), ("H", 12), ("P", 1), ("O", 4)])

    def test_aluminum_sulfate(self):
        self.assertEqual(self.counts("Al2(SO4)3"), [("Al", 2), ("S", 3), ("O", 12)])

    def test_calcium_hydroxide(self):
        self.assertEqual(self.counts("Ca(OH)2"), [("Ca", 1), ("O", 2), ("H", 2)])

    def test_hydrate(self):
        self.assertEqual(self.counts("CuSO4*5H2O"),
                         [("Cu", 1), ("S", 1), ("O", 9), ("H", 10)])
        self.assertEqual(self.counts("CuSO4.5H2O"), self.counts("CuSO4*5H2O"))
        c = compound_from_formula("CuSO4*5H2O")
        self.assertEqual(molar_mass(c, TEACHER)[1], "249.71")  # 63.55+32.06+9*16.00+10*1.01

    def test_nested(self):
        self.assertEqual(self.counts("K4[Fe(CN)6]"), [("K", 4), ("Fe", 1), ("C", 6), ("N", 6)])
        self.assertEqual(self.counts("((CH3)3C)2O"), [("C", 8), ("H", 18), ("O", 1)])

    def test_co_vs_CO(self):
        self.assertEqual(self.counts("Co"), [("Co", 1)])
        self.assertEqual(self.counts("CO"), [("C", 1), ("O", 1)])
        self.assertEqual(self.counts("CoCO3"), [("Co", 1), ("C", 1), ("O", 3)])

    def test_bad_input(self):
        bad = ["", "Xx", "CL", "H2O)", "(H2O", "Ca(OH", "H0", "2", "h2o", "H2O#",
               "()", "CuSO4*", "Al2(SO4]3", "5"]
        for f in bad:
            with self.subTest(f=f):
                with self.assertRaises(ChemError):
                    parse_formula(f)

    def test_hint_for_caps(self):
        try:
            parse_formula("NaCL")
        except ChemError as e:
            self.assertIn("Cl", str(e))
        else:
            self.fail("NaCL should fail")

    def test_lazy_symbols(self):
        self.assertEqual(parse_symbols("N H O"), ["N", "H", "O"])
        self.assertEqual(parse_symbols("NHO"), ["N", "H", "O"])
        self.assertEqual(parse_symbols("Co,N"), ["Co", "N"])
        for b in ["", "N2", "NN", "Q"]:
            with self.assertRaises(ChemError):
                parse_symbols(b)

    def test_lazy_compound(self):
        c = compound_from_counts(["N", "H", "O"], {"N": 2, "H": 4, "O": 3})
        self.assertEqual(c.formula, "N2H4O3")
        self.assertEqual(c.ptype, "molecules")


class Numbers(unittest.TestCase):
    def test_sigfigs(self):
        cases = {"4.50": (3, False), "3.5E2": (2, False), "0.0150": (3, False),
                 "350": (2, True), "350.": (3, False), "125.0": (4, False),
                 "7.5E24": (2, False), "100": (1, True), "7": (1, False)}
        for s, (n, amb) in cases.items():
            with self.subTest(s=s):
                v, sf, a, _ = parse_num(s)
                self.assertEqual((sf, a), (n, amb))

    def test_ambiguous_uses_six(self):
        r = run("H2O", "350", MOL, None, MOL, "H")
        self.assertEqual(r["sf"], 6)
        self.assertEqual(num_text(r["answer"]), "700.000")

    def test_long_input_capped_at_six(self):
        r = run("H2O", "1.234567891", MOL, None, MOL, "H")
        self.assertTrue(r["capped"])
        self.assertEqual(num_text(r["answer"]), "2.46914")

    def test_fmt(self):
        self.assertEqual(fmt_sig(462.2, 2), ("4.6", 2))
        self.assertEqual(fmt_sig(10.6, 2), ("11", None))
        self.assertEqual(fmt_sig(460, 3), ("4.60", 2))
        self.assertEqual(fmt_sig(0.000123, 2), ("1.2", -4))
        self.assertEqual(fmt_sig(0.00123, 2), ("0.0012", None))
        self.assertEqual(fmt_sig(9.996, 3), ("10.0", None))

    def test_bad_numbers(self):
        for s in ["", "abc", "1.2.3", "E5", "1E", "1E2E3", "--1"]:
            with self.subTest(s=s):
                with self.assertRaises(ChemError):
                    parse_num(s)


class Table(unittest.TestCase):
    def test_all_118(self):
        self.assertEqual(len(SYMS), 118)
        self.assertEqual(SYMS[0], "H")
        self.assertEqual(SYMS[85], "Rn")
        self.assertEqual(SYMS[-1], "Og")
        self.assertEqual(len(set(SYMS)), 118)

    def test_teacher_rounding(self):
        c = compound_from_formula("NaCl")
        self.assertEqual(elem_mass(c, "Na", TEACHER)[1], "22.99")
        self.assertEqual(elem_mass(c, "Na", PRECISE)[1], "22.98976928")


if __name__ == "__main__":
    unittest.main()
