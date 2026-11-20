# chemcore.py - stoichiometry logic. No TI imports, so it runs on a PC too.
# Written for CircuitPython/MicroPython: no f-strings, no str.ljust/rjust,
# no reliance on dict ordering (ordered lists are kept alongside dicts).
from chemdata import SYMS, PSTR, NONMETALS, COMMON

TEACHER = 0
PRECISE = 1
# Avogadro: (value, display mantissa, display exponent)
AVO = ((6.02e23, "6.02", 23), (6.02214076e23, "6.02214076", 23))

G = "g"
MOL = "mol"
PT = "pt"          # particles

MAX_SF = 6         # cap / fallback sig figs (ambiguous zeros or huge counts)


class ChemError(Exception):
    pass


# ---------------------------------------------------------------- numbers
def fmt_mass(v, dec):
    """Format v with up to `dec` decimals, trailing zeros stripped."""
    s = ("%." + str(dec) + "f") % v
    if "." in s:
        while s[-1] == "0":
            s = s[:-1]
        if s[-1] == ".":
            s = s[:-1]
    return s


def parse_num(s):
    """'3.5E2' -> (350.0, sigfigs, ambiguous, (mant_str, exp or None))."""
    t = s.strip()
    if not t:
        raise ChemError("Enter a value")
    up = t.upper()
    if up.count("E") > 1:
        raise ChemError("Bad number: " + t)
    if "E" in up:
        k = up.index("E")
        m, e = t[:k], t[k + 1:]
        if e in ("", "-", "+"):
            raise ChemError("Missing exponent")
        for c in e.lstrip("+-"):
            if not c.isdigit():
                raise ChemError("Bad exponent: " + e)
        exp = int(e)
    else:
        m, exp = t, None
    body = m.lstrip("+-")
    if body == "" or body == "." or body.count(".") > 1:
        raise ChemError("Bad number: " + t)
    for c in body:
        if not (c.isdigit() or c == "."):
            raise ChemError("Bad number: " + t)
    try:
        val = float(m + ("e" + str(exp) if exp is not None else ""))
    except ValueError:
        raise ChemError("Bad number: " + t)
    # sig figs
    amb = False
    if "." in body:
        d = body.replace(".", "").lstrip("0")
        n = len(d) if d else 1
    else:
        d = body.lstrip("0")
        if not d:
            n = 1
        else:
            stripped = d.rstrip("0")
            if len(stripped) < len(d):
                amb = True          # 350 -> ambiguous trailing zero(s)
            n = len(stripped)
    return val, n, amb, (m, exp)


def _digits_exp(x, n):
    s = ("%." + str(n - 1) + "e") % abs(x)
    m, e = s.lower().split("e")
    return m.replace(".", ""), int(e)


def _plain(digits, e):
    if e >= 0:
        ip = digits[:e + 1]
        while len(ip) < e + 1:
            ip += "0"
        fp = digits[e + 1:]
        return ip + ("." + fp if fp else "")
    return "0." + "0" * (-e - 1) + digits


def fmt_sig(x, n):
    """Round x to n sig figs -> (mantissa_str, exp or None for plain)."""
    if x == 0:
        return ("0", None)
    sign = "-" if x < 0 else ""
    digits, e = _digits_exp(x, n)
    ambiguous_int = (e == n - 1 and n > 1 and digits[-1] == "0")
    if -3 <= e < n and not ambiguous_int:
        return (sign + _plain(digits, e), None)
    return (sign + digits[0] + ("." + digits[1:] if len(digits) > 1 else ""), e)


def fmt_full(x):
    """Unrounded display: 10 sig figs, trailing zeros dropped."""
    if x == 0:
        return ("0", None)
    sign = "-" if x < 0 else ""
    digits, e = _digits_exp(x, 10)
    digits = digits.rstrip("0") or "0"
    if -3 <= e < 10:
        return (sign + _plain(digits, e), None)
    return (sign + digits[0] + ("." + digits[1:] if len(digits) > 1 else ""), e)


def num_text(t):
    """(mant, exp) -> flat text such as '1.4x10^3' (for tests / logs)."""
    m, e = t
    return m if e is None else m + "x10^" + str(e)


# ---------------------------------------------------------------- formulas
def _hint_unknown(sym, prev):
    if len(sym) == 1 and prev and len(prev) == 1 and (prev + sym.lower()) in PSTR:
        return ("No element " + sym + ". Meant " + prev + sym.lower() +
                "? Press [x,t,0,n] before " + sym)
    return "Unknown element: " + sym


def _num(s, i):
    j = i
    while j < len(s) and s[j].isdigit():
        j += 1
    if j == i:
        return 1, i
    n = int(s[i:j])
    if n == 0:
        raise ChemError("Count can't be 0")
    return n, j


def _add(cnt, order, sym, n):
    if sym in cnt:
        cnt[sym] += n
    else:
        cnt[sym] = n
        order.append(sym)


def _group(s, i, close):
    cnt = {}
    order = []
    prev = None
    while i < len(s):
        c = s[i]
        if c == "(" or c == "[":
            sub, sorder, i = _group(s, i + 1, ")" if c == "(" else "]")
            n, i = _num(s, i)
            for k in sorder:
                _add(cnt, order, k, sub[k] * n)
            prev = None
        elif c == ")" or c == "]":
            if close != c:
                raise ChemError("Unmatched " + c)
            if not order:
                raise ChemError("Empty ( )")
            return cnt, order, i + 1
        elif "A" <= c <= "Z":
            sym = c
            i += 1
            if i < len(s) and "a" <= s[i] <= "z":
                sym += s[i]
                i += 1
            if sym not in PSTR:
                raise ChemError(_hint_unknown(sym, prev))
            n, i = _num(s, i)
            _add(cnt, order, sym, n)
            prev = sym
        elif "a" <= c <= "z":
            raise ChemError("Lowercase 1st letter: " + c)
        elif c.isdigit():
            raise ChemError("Number in wrong place")
        else:
            raise ChemError("Bad character: " + c)
    if close:
        raise ChemError("Missing " + close)
    return cnt, order, i


def parse_formula(f):
    """'CuSO4*5H2O' -> (counts dict, ordered symbol list)."""
    s = f.replace(" ", "")
    for dot in ("·", "."):
        s = s.replace(dot, "*")
    if not s:
        raise ChemError("Type a formula")
    cnt = {}
    order = []
    for part in s.split("*"):
        if not part:
            raise ChemError("Empty part around *")
        coef, j = _num(part, 0)
        if j == len(part):
            raise ChemError("Coefficient with no formula")
        c2, o2, _ = _group(part[j:], 0, None)
        for k in o2:
            _add(cnt, order, k, c2[k] * coef)
    return cnt, order


def _rank(sym):
    if sym in COMMON:
        return COMMON.index(sym)
    return 1000 + SYMS.index(sym)


def candidates(letter):
    """Elements whose symbol starts with `letter`: the 1-letter one first,
    then most common first.  'C' -> ['C', 'Cl', 'Ca', 'Cu', 'Cr', 'Co', ...]"""
    out = [s for s in SYMS if s[0] == letter]
    out.sort(key=lambda s: (len(s) != 1, _rank(s)))
    return out


def parse_symbols(s):
    """Lazy-mode element list: 'N H O' / 'NHO' / 'Co,N' -> ['N','H','O']."""
    t = s.replace(",", " ").replace(" ", "")
    if not t:
        raise ChemError("Type at least one element")
    out = []
    i = 0
    prev = None
    while i < len(t):
        c = t[i]
        if not ("A" <= c <= "Z"):
            raise ChemError("Elements only (no numbers): " + c)
        sym = c
        i += 1
        if i < len(t) and "a" <= t[i] <= "z":
            sym += t[i]
            i += 1
        if sym not in PSTR:
            raise ChemError(_hint_unknown(sym, prev))
        if sym in out:
            raise ChemError("Listed twice: " + sym)
        out.append(sym)
        prev = sym
    return out


# ---------------------------------------------------------------- compound
class Compound:
    def __init__(self, formula, counts, order):
        self.formula = formula
        self.counts = counts
        self.order = order
        self.ptype = default_ptype(formula, counts, order)
        self.mass_ov = None      # compound molar mass override (string)
        self.el_ov = {}          # element mass overrides {sym: string}

    def n(self, sym):
        return self.counts[sym]


def compound_from_formula(f):
    cnt, order = parse_formula(f)
    return Compound(f.replace(" ", ""), cnt, order)


def compound_from_counts(order, counts):
    f = ""
    for k in order:
        f += k + (str(counts[k]) if counts[k] != 1 else "")
    c = dict()
    for k in order:
        if counts[k] < 1:
            raise ChemError("Count for " + k + " must be >= 1")
        c[k] = counts[k]
    return Compound(f, c, list(order))


PTYPES = ("molecules", "formula units", "atoms")
PSHORT = {"molecules": "molec", "formula units": "f.u.", "atoms": "atoms"}


def default_ptype(formula, counts, order):
    if len(order) == 1 and counts[order[0]] == 1:
        return "atoms"
    if "NH4" in formula:
        return "formula units"
    for k in order:
        if k not in NONMETALS:
            return "formula units"
    return "molecules"


def elem_mass(cmp, sym, mode):
    """-> (value, display string, overridden?)"""
    if sym in cmp.el_ov:
        s = cmp.el_ov[sym]
        return float(s), s, True
    p = PSTR[sym]
    if mode == TEACHER:
        s = "%.2f" % float(p)
        return float(s), s, False
    return float(p), p, False


def molar_mass(cmp, mode):
    """-> (value, display string, overridden?)"""
    if cmp.mass_ov:
        return float(cmp.mass_ov), cmp.mass_ov, True
    tot = 0.0
    for k in cmp.order:
        tot += cmp.counts[k] * elem_mass(cmp, k, mode)[0]
    if mode == TEACHER:
        s = "%.2f" % tot
    else:
        s = fmt_mass(tot, 4)
    return tot, s, False


def check_mass_str(s):
    v, n, a, t = parse_num(s)
    if v <= 0:
        raise ChemError("Mass must be > 0")
    if t[1] is not None:
        raise ChemError("Type a plain number")
    return s.strip()


# ---------------------------------------------------------------- solving
def unit_label(cmp, u, who, short):
    """Unit text like 'g NH3', 'mol H', 'atoms Na', 'molec CO2'."""
    name = cmp.formula if who is None else who
    if u == PT:
        p = "atoms" if who is not None else cmp.ptype
        return (PSHORT[p] if short else p) + " " + name
    return u + " " + name


def solve(cmp, mode, gstr, gu, gw, fu, fw):
    """gu/fu in (G, MOL, PT); gw/fw = None for compound or an element symbol.
    Returns a dict describing the dimensional-analysis chain and answer."""
    val, sf, amb, gtxt = parse_num(gstr)
    if val <= 0:
        raise ChemError("Value must be > 0")
    if gu == fu and gw == fw:
        raise ChemError("Given and Find are the same")
    for w in (gw, fw):
        if w is not None and w not in cmp.counts:
            raise ChemError(w + " is not in " + cmp.formula)
    avo, avo_m, avo_e = AVO[mode]
    steps = []   # each: [num_val, (mant, exp), (u, who), den_val, (mant, exp), (u, who)]

    def mass(who):
        if who is None:
            return molar_mass(cmp, mode)
        return elem_mass(cmp, who, mode)

    # 1) to moles of the given entity
    if gu == G:
        mv, ms, _ = mass(gw)
        steps.append([1.0, ("1", None), (MOL, gw), mv, (ms, None), (G, gw)])
    elif gu == PT:
        steps.append([1.0, ("1", None), (MOL, gw), avo, (avo_m, avo_e), (PT, gw)])
    # 2) switch entity (element <-> compound <-> other element)
    if gw != fw:
        if gw is not None:
            n = cmp.counts[gw]
            steps.append([1.0, ("1", None), (MOL, None), float(n), (str(n), None), (MOL, gw)])
        if fw is not None:
            n = cmp.counts[fw]
            steps.append([float(n), (str(n), None), (MOL, fw), 1.0, ("1", None), (MOL, None)])
    # 3) from moles to the wanted unit
    if fu == G:
        mv, ms, _ = mass(fw)
        steps.append([mv, (ms, None), (G, fw), 1.0, ("1", None), (MOL, fw)])
    elif fu == PT:
        steps.append([avo, (avo_m, avo_e), (PT, fw), 1.0, ("1", None), (MOL, fw)])

    x = val
    for st in steps:
        x = x * st[0] / st[3]
    use = MAX_SF if amb else (sf if sf < MAX_SF else MAX_SF)
    return {
        "given": (gtxt, (gu, gw)),
        "steps": steps,
        "value": x,
        "sf": use,
        "sf_given": sf,
        "ambiguous": amb,
        "capped": (not amb) and sf > MAX_SF,
        "answer": fmt_sig(x, use),
        "full": fmt_full(x),
        "unit": (fu, fw),
    }
