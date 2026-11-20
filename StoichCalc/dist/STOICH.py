# STOICH - stoichiometry / mole conversions for the TI-84 Evo
# Built from src/ by build.py - edit the sources, not this file.

# ===== chemdata.py
_PT = (
 "H 1.008 He 4.002602 Li 6.94 Be 9.0121831 B 10.81 C 12.011 N 14.007 "
 "O 15.999 F 18.998403163 Ne 20.1797 Na 22.98976928 Mg 24.305 "
 "Al 26.9815385 Si 28.085 P 30.973761998 S 32.06 Cl 35.45 Ar 39.948 "
 "K 39.0983 Ca 40.078 Sc 44.955908 Ti 47.867 V 50.9415 Cr 51.9961 "
 "Mn 54.938044 Fe 55.845 Co 58.933194 Ni 58.6934 Cu 63.546 Zn 65.38 "
 "Ga 69.723 Ge 72.630 As 74.921595 Se 78.971 Br 79.904 Kr 83.798 "
 "Rb 85.4678 Sr 87.62 Y 88.90584 Zr 91.224 Nb 92.90637 Mo 95.95 Tc 98 "
 "Ru 101.07 Rh 102.90550 Pd 106.42 Ag 107.8682 Cd 112.414 In 114.818 "
 "Sn 118.710 Sb 121.760 Te 127.60 I 126.90447 Xe 131.293 "
 "Cs 132.90545196 Ba 137.327 La 138.90547 Ce 140.116 Pr 140.90766 "
 "Nd 144.242 Pm 145 Sm 150.36 Eu 151.964 Gd 157.25 Tb 158.92535 "
 "Dy 162.500 Ho 164.93033 Er 167.259 Tm 168.93422 Yb 173.045 "
 "Lu 174.9668 Hf 178.49 Ta 180.94788 W 183.84 Re 186.207 Os 190.23 "
 "Ir 192.217 Pt 195.084 Au 196.966569 Hg 200.592 Tl 204.38 Pb 207.2 "
 "Bi 208.98040 Po 209 At 210 Rn 222 Fr 223 Ra 226 Ac 227 Th 232.0377 "
 "Pa 231.03588 U 238.02891 Np 237 Pu 244 Am 243 Cm 247 Bk 247 Cf 251 "
 "Es 252 Fm 257 Md 258 No 259 Lr 262 Rf 267 Db 268 Sg 269 Bh 270 "
 "Hs 269 Mt 278 Ds 281 Rg 282 Cn 285 Nh 286 Fl 289 Mc 290 Lv 293 "
 "Ts 294 Og 294"
)
NONMETALS = ("H He B C N O F Ne Si P S Cl Ar Ge As Se Br Kr Sb Te I Xe "
             "At Rn Ts Og").split()
COMMON = ("H C N O Na Cl K Ca Mg S P Fe Cu Zn Al Br I F Ag Li Ba Mn Cr Co Ni "
          "Pb Sn Hg Au Si He Ne Ar Kr Xe B Be Sr Cs Rb Ti V Cd Pt As Se U Ga "
          "Ge Sb Bi W Mo Rn Ra Fr Pd Zr Tl").split()
SYMS = []
PSTR = {}
_t = _PT.split()
for _i in range(0, len(_t), 2):
    SYMS.append(_t[_i])
    PSTR[_t[_i]] = _t[_i + 1]
del _t, _i
# ===== chemcore.py
TEACHER = 0
PRECISE = 1
AVO = ((6.02e23, "6.02", 23), (6.02214076e23, "6.02214076", 23))
G = "g"
MOL = "mol"
PT = "pt"          # particles
MAX_SF = 6         # cap / fallback sig figs (ambiguous zeros or huge counts)
class ChemError(Exception):
    pass
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
    if gu == G:
        mv, ms, _ = mass(gw)
        steps.append([1.0, ("1", None), (MOL, gw), mv, (ms, None), (G, gw)])
    elif gu == PT:
        steps.append([1.0, ("1", None), (MOL, gw), avo, (avo_m, avo_e), (PT, gw)])
    if gw != fw:
        if gw is not None:
            n = cmp.counts[gw]
            steps.append([1.0, ("1", None), (MOL, None), float(n), (str(n), None), (MOL, gw)])
        if fw is not None:
            n = cmp.counts[fw]
            steps.append([float(n), (str(n), None), (MOL, fw), 1.0, ("1", None), (MOL, None)])
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
# ===== stoich_ui.py
from ti_draw import clear, set_color, fill_rect, draw_line, draw_text
W = 320
H = 240
CW = 10          # assumed ti_draw character width  (check with KEYTEST)
CH = 16          # assumed line height
TEXT_DY = 0      # shift if draw_text's y turns out to be the baseline
TIMES = "×"  # multiplication sign; change to "x" if it shows as junk
DOT = "·"    # hydrate dot
K_RIGHT, K_LEFT, K_UP, K_DOWN, K_ENTER = 1, 2, 3, 4, 5
K_CLEAR, K_DEL = 9, 10
K_F1, K_F2, K_F3, K_F4, K_F5 = 73, 72, 46, 90, 68   # y= window zoom trace graph
K_QUIT = 64
K_SUB, K_MUL = 129, 130
K_LPAR, K_RPAR, K_LBRK, K_RBRK = 133, 134, 135, 136
K_NEG, K_DOT = 140, 141
K_0 = 142                    # K_0..K_9 = 142..151
K_EE = 152
K_A = 154                    # OS alpha letters A..Z = 154..179 (if [alpha] is used)
K_VARX = 180                 # [x,t,theta,n]: 123/ABC toggle, lazy separator
ALPHA_FLAG = 512             # in case wait_key reports alpha as +512 on the base key
LETTER_KEYS = {50: "A", 44: "B", 45: "C", 132: "D", 182: "D", 183: "E", 185: "F",
               187: "G", 131: "H", 189: "I", 139: "J", 133: "K", 134: "L", 130: "M",
               193: "N", 149: "O", 150: "P", 151: "Q", 129: "R", 191: "S", 146: "T",
               147: "U", 148: "V", 128: "W", 138: "X", 143: "Y", 144: "Z"}
BG = (255, 255, 255)
FG = (20, 20, 30)
HDR = (25, 55, 120)
WHITE = (255, 255, 255)
GRAY = (140, 140, 150)
LIGHT = (225, 230, 240)
SEL = (205, 225, 255)
RED = (205, 30, 30)
GREEN = (0, 120, 60)
ANSBG = (220, 245, 228)
YELLOW = (255, 220, 60)
ORANGE = (220, 110, 10)
TEAL = (0, 130, 140)
def col(c):
    set_color(c[0], c[1], c[2])
def box(x, y, w, h, c):
    col(c)
    fill_rect(x, y, w, h)
def txt(x, y, s, c=FG):
    col(c)
    draw_text(x, y + TEXT_DY, s)
def tw(s):
    return len(s) * CW
def segs_w(segs):
    w = 0
    for s in segs:
        w += tw(s[0])
    return w
def draw_segs(x, y, segs):
    for s in segs:
        if s[0]:
            txt(x, y + s[1], s[0], s[2])
        x += tw(s[0])
    return x
def num_segs(t, c=FG):
    m, e = t
    if e is None:
        return [(m, 0, c)]
    return [(m + TIMES + "10", 0, c), (str(e), -6, c)]
def form_segs(f, c=FG):
    """Formula text with subscript counts (coefficients after * stay inline)."""
    out = []
    prev = ""
    for ch in f:
        if ch == "*":
            out.append((DOT, 0, c))
            prev = "*"
            continue
        sub = ch.isdigit() and (prev.isalpha() or (prev != "" and prev in ")]") or
                                (prev.isdigit() and out and out[-1][1] > 0))
        out.append((ch, 5 if sub else 0, c))
        prev = ch
    return out
def entry_num_segs(s, c=FG):
    """Typed number like 3.5E2 -> 3.5 x10^2 while typing."""
    u = s.upper()
    if "E" not in u:
        return [(s, 0, c)]
    k = u.index("E")
    return [(s[:k] + TIMES + "10", 0, c), (s[k + 1:] or "_", -6, c)]
def header(title, chip=""):
    box(0, 0, W, 20, HDR)
    if isinstance(title, list):
        draw_segs(4, 2, [(s[0], s[1], WHITE) for s in title])
    else:
        txt(4, 2, title, WHITE)
    if chip:
        x = W - tw(chip) - 10
        box(x - 4, 2, tw(chip) + 8, 16, YELLOW)
        txt(x, 2, chip, FG)
def softbar(labels):
    box(0, H - 19, W, 19, LIGHT)
    for i in range(5):
        lab = labels[i] if i < len(labels) else ""
        if i:
            col(GRAY)
            draw_line(i * 64, H - 19, i * 64, H - 1)
        if lab:
            txt(i * 64 + (64 - tw(lab)) // 2, H - 18, lab, HDR)
def message(s, c=RED):
    if s:
        txt(4, H - 38, s[:W // CW - 1], c)
def letter_of(k):
    """Letter for a key in a letters-only field (auto A-lock), else None."""
    if K_A <= k < K_A + 26:
        return chr(65 + k - K_A)
    if k >= ALPHA_FLAG:
        k -= ALPHA_FLAG
    return LETTER_KEYS.get(k)
def num_char(k):
    """Character for a key in a number/punctuation context, else None."""
    if K_0 <= k <= K_0 + 9:
        return chr(48 + k - K_0)
    return {K_DOT: ".", K_LPAR: "(", K_RPAR: ")", K_LBRK: "[", K_RBRK: "]",
            K_MUL: "*", K_NEG: "-", K_SUB: "-", K_EE: "E"}.get(k)
def digit(k):
    if K_0 <= k <= K_0 + 9:
        return k - K_0
    return None
def drop_last_symbol(s):
    """Backspace: removes a whole 2-letter symbol at once (NaCl -> Na)."""
    if len(s) >= 2 and s[-1].islower():
        return s[:-2]
    return s[:-1]
MENU = ("Formula entry", "Lazy entry (element list)", "Keys / help", "Quit")
UNIT_NAMES = {G: "g", MOL: "mol"}
PICK_ROWS = 7
class App:
    def __init__(self):
        self.running = True
        self.scr = "menu"
        self.sel = 0
        self.msg = ""
        self.cmp = None
        self.src = "formula"
        self.ftext = ""
        self.fnum = False          # formula field: False = letters (ABC), True = 123
        self.pick = None           # element picker: [candidates, selected index, field]
        self.ltext = ""
        self.lsyms = []
        self.lcounts = {}
        self.lsel = 0
        self.ltyping = False
        self.msel = 0
        self.medit = None
        self.psel = 0
        self.gval = ""
        self.gu, self.gw, self.fu, self.fw = G, None, MOL, None
        self.res = None            # Teacher result (drawn as the chain)
        self.resp = None           # Precise result (answer only)
        self.hscroll = 0
    def key(self, k):
        self.msg = ""
        if k == K_QUIT:
            self.running = False
            return
        if self.pick is not None and self.pick_key(k):
            pass
        else:
            getattr(self, "k_" + self.scr)(k)
        if self.running:
            self.draw()
    def draw(self):
        clear()
        box(0, 0, W, H, BG)
        getattr(self, "d_" + self.scr)()
        if self.pick is not None:
            self.d_pick()
    def go(self, scr):
        self.scr = scr
        self.pick = None
    def letter_typed(self, letter, field):
        c = candidates(letter)
        if not c:
            self.msg = "No element starts with " + letter
        elif len(c) == 1:
            self.add_symbol(c[0], field)
        else:
            self.pick = [c, 0, field]
    def add_symbol(self, sym, field):
        if field == "f":
            self.ftext += sym
        else:
            self.ltext += sym
    def pick_key(self, k):
        """Returns True if the key was fully used by the picker."""
        c, i, field = self.pick
        if k == K_UP:
            self.pick[1] = (i - 1) % len(c)
            return True
        if k == K_DOWN:
            self.pick[1] = (i + 1) % len(c)
            return True
        if k == K_CLEAR or k == K_DEL:
            self.pick = None
            return True
        self.pick = None
        self.add_symbol(c[i], field)
        return k == K_ENTER    # any other key: accept, then handle the key normally
    def pc_lower(self, ch):
        """Demo convenience for a PC keyboard: lowercase letter picks a 2-letter symbol."""
        if self.pick is None:
            return
        c = self.pick[0]
        sym = c[0][0] + ch
        if sym in c:
            self.pick[1] = c.index(sym)
            self.key(K_ENTER)
    def letter_mode(self):
        """True when keys currently type letters (used by the web demo's PC keyboard)."""
        return self.scr == "lazy1" or (self.scr == "formula" and not self.fnum)
    def d_pick(self):
        c, i, field = self.pick
        top = 0
        if i >= PICK_ROWS:
            top = i - PICK_ROWS + 1
        n = min(len(c), PICK_ROWS)
        x, y, w = 214, 24, 100
        box(x - 2, y - 2, w + 4, n * 20 + 26, HDR)
        box(x, y, w, n * 20 + 22, WHITE)
        txt(x + 4, y + 2, "pick " + c[0][0], GRAY)
        for r in range(n):
            j = top + r
            yy = y + 22 + r * 20
            if j == i:
                box(x, yy - 2, w, 20, SEL)
            txt(x + 8, yy, c[j], FG)
        if top > 0:
            txt(x + w - 14, y + 22, "^", GRAY)
        if top + n < len(c):
            txt(x + w - 14, y + 22 + (n - 1) * 20, "v", GRAY)
    def d_menu(self):
        header("STOICH")
        for i in range(len(MENU)):
            y = 34 + i * 28
            if i == self.sel:
                box(2, y - 4, W - 4, CH + 8, SEL)
            txt(10, y, str(i + 1) + ": " + MENU[i], FG)
        txt(10, 168, "arrows/number + enter", GRAY)
        softbar(("", "", "", "", "QUIT"))
    def k_menu(self, k):
        d = digit(k)
        if k == K_UP:
            self.sel = (self.sel - 1) % len(MENU)
        elif k == K_DOWN:
            self.sel = (self.sel + 1) % len(MENU)
        elif k == K_ENTER or (d is not None and 1 <= d <= len(MENU)):
            if d is not None:
                self.sel = d - 1
            self.go(("formula", "lazy1", "help", "quit")[self.sel])
            if self.scr == "quit":
                self.running = False
        elif k == K_F5:
            self.running = False
    def d_help(self):
        header("Keys")
        lines = ("Letter fields: keys type their",
                 "  green letter (no [alpha]).",
                 "Pick list: up/down, [enter],",
                 "  or keep typing = top choice",
                 "[x,t,0,n] formula: ABC <-> 123",
                 "[x,t,0,n] lazy: next element",
                 "123 mode: [x] = hydrate dot",
                 "[2nd][EE]/[x] x10^ in values",
                 "[clear] back   [del] erase",
                 "[2nd][quit]  exit")
        for i in range(len(lines)):
            txt(4, 26 + i * 18, lines[i], FG)
        softbar(("", "", "", "", "BACK"))
    def k_help(self, k):
        self.go("menu")
    def d_formula(self):
        header("Compound: formula", "123" if self.fnum else "ABC")
        txt(6, 30, "Formula:", GRAY)
        box(4, 48, W - 8, 26, LIGHT)
        x = draw_segs(10, 53, form_segs(self.ftext))
        box(x + 1, 52, 2, 18, HDR)          # cursor
        if self.ftext and self.pick is None:
            try:
                cnt, order = parse_formula(self.ftext)
                c = compound_from_formula(self.ftext)
                line = ""
                for s in order:
                    line += s + ":" + str(cnt[s]) + "  "
                txt(6, 84, line[:31], FG)
                txt(6, 104, "M = " + molar_mass(c, TEACHER)[1] + " g/mol", GREEN)
                txt(6, 124, c.ptype, GRAY)
            except ChemError as e:
                s = str(e)
                txt(6, 84, s[:31], RED)
                if len(s) > 31:
                    txt(6, 102, s[31:62], RED)
        txt(6, 150, "[x,t,0,n]: ABC / 123", HDR)
        txt(6, 168, "123: digits ( ) [x]=dot", GRAY)
        message(self.msg)
        softbar(("LAZY", "", "", "MENU", "NEXT"))
    def k_formula(self, k):
        if k == K_ENTER or k == K_F5:
            try:
                c = compound_from_formula(self.ftext)
            except ChemError as e:
                self.msg = str(e)
                return
            self.set_compound(c, "formula")
        elif k == K_F1:
            self.go("lazy1")
        elif k == K_F4:
            self.go("menu")
        elif k == K_CLEAR:
            if self.ftext:
                self.ftext = ""
                self.fnum = False
            else:
                self.go("menu")
        elif k == K_DEL:
            self.ftext = drop_last_symbol(self.ftext)
        elif k == K_VARX:
            self.fnum = not self.fnum
        elif K_A <= k < K_A + 26:                      # explicit [alpha] letter
            self.fnum = False
            self.letter_typed(letter_of(k), "f")
        elif not self.fnum:
            L = letter_of(k)
            if L:
                self.letter_typed(L, "f")
        else:
            ch = num_char(k)
            if ch is not None and ch in "0123456789()[]*" and len(self.ftext) < 24:
                self.ftext += ch
                if ch in "([":
                    self.fnum = False                # an element always follows "("
    def set_compound(self, c, src):
        old = self.cmp
        self.cmp = c
        self.src = src
        if old is None or old.formula != c.formula:
            self.gw = None
            self.fw = None
        else:
            c.mass_ov = old.mass_ov
            c.el_ov = old.el_ov
            c.ptype = old.ptype
        self.msel = 0
        self.medit = None
        self.go("mass")
    def d_lazy1(self):
        header("Lazy entry: elements", "ABC")
        txt(6, 30, "Elements:", GRAY)
        box(4, 48, W - 8, 26, LIGHT)
        x = draw_segs(10, 53, [(self.ltext.replace(",", " "), 0, FG)])
        box(x + 1, 52, 2, 18, HDR)
        if self.ltext and self.pick is None:
            try:
                syms = parse_symbols(self.ltext)
                xx = 6
                for s in syms:
                    box(xx, 84, tw(s) + 8, 20, SEL)
                    txt(xx + 4, 86, s, FG)
                    xx += tw(s) + 14
            except ChemError as e:
                txt(6, 86, str(e)[:31], RED)
        txt(6, 130, "[x,t,0,n] = next element", HDR)
        txt(6, 148, "keys type their green letter", GRAY)
        message(self.msg)
        softbar(("FORM", "", "", "MENU", "NEXT"))
    def k_lazy1(self, k):
        if k == K_ENTER or k == K_F5:
            try:
                syms = parse_symbols(self.ltext)
            except ChemError as e:
                self.msg = str(e)
                return
            counts = {}
            for s in syms:
                counts[s] = self.lcounts.get(s, 1)
            self.lsyms = syms
            self.lcounts = counts
            self.lsel = 0
            self.ltyping = False
            self.go("lazy2")
        elif k == K_F1:
            self.go("formula")
        elif k == K_F4:
            self.go("menu")
        elif k == K_CLEAR:
            if self.ltext:
                self.ltext = ""
            else:
                self.go("menu")
        elif k == K_DEL:
            self.ltext = drop_last_symbol(self.ltext)
        elif k == K_VARX:
            if self.ltext and not self.ltext.endswith(","):
                self.ltext += ","
        else:
            L = letter_of(k)
            if L:
                self.letter_typed(L, "l")
    def d_lazy2(self):
        f = ""
        for s in self.lsyms:
            n = self.lcounts[s]
            f += s + (str(n) if n != 1 else "")
        header([("Lazy: ", 0, FG)] + form_segs(f))
        top = 0
        if self.lsel > 6:
            top = self.lsel - 6
        for i in range(top, min(len(self.lsyms), top + 7)):
            s = self.lsyms[i]
            y = 28 + (i - top) * 24
            if i == self.lsel:
                box(2, y - 3, W - 4, 22, SEL)
            txt(14, y, s, FG)
            v = str(self.lcounts[s])
            box(70, y - 2, 60, 20, WHITE if i != self.lsel else (255, 250, 220))
            txt(76, y, "[" + v + "]", HDR if (i == self.lsel and self.ltyping) else FG)
        txt(150, 30, "up/down: pick", GRAY)
        txt(150, 48, "</>: -1 / +1", GRAY)
        txt(150, 66, "0-9: type it", GRAY)
        message(self.msg)
        softbar(("BACK", "", "", "MENU", "NEXT"))
    def k_lazy2(self, k):
        s = self.lsyms[self.lsel]
        d = digit(k)
        if d is not None:
            if self.ltyping and self.lcounts[s] < 100:
                self.lcounts[s] = self.lcounts[s] * 10 + d
            else:
                self.lcounts[s] = d
            self.ltyping = True
            return
        self.ltyping = False
        if k == K_UP:
            self.lsel = (self.lsel - 1) % len(self.lsyms)
        elif k == K_DOWN:
            self.lsel = (self.lsel + 1) % len(self.lsyms)
        elif k == K_LEFT:
            self.lcounts[s] = max(1, self.lcounts[s] - 1)
        elif k == K_RIGHT:
            self.lcounts[s] = min(999, self.lcounts[s] + 1)
        elif k == K_DEL:
            self.lcounts[s] = 1
        elif k == K_ENTER or k == K_F5:
            try:
                c = compound_from_counts(self.lsyms, self.lcounts)
            except ChemError as e:
                self.msg = str(e)
                return
            self.set_compound(c, "lazy2")
        elif k == K_F1 or k == K_CLEAR:
            self.go("lazy1")
        elif k == K_F4:
            self.go("menu")
    def d_mass(self):
        c = self.cmp
        header(form_segs(c.formula) + [("  masses", 0, WHITE)])
        rows = [("M " + c.formula, molar_mass(c, TEACHER))]
        for s in c.order:
            rows.append((s + " x" + str(c.counts[s]), elem_mass(c, s, TEACHER)))
        top = 0
        if self.msel > 6:
            top = self.msel - 6
        for i in range(top, min(len(rows), top + 7)):
            y = 26 + (i - top) * 23
            lab, (v, s, ov) = rows[i]
            if i == self.msel:
                box(2, y - 3, W - 4, 21, SEL)
            if i == 0:
                draw_segs(8, y, [("M ", 0, FG)] + form_segs(c.formula))
            else:
                txt(8, y, lab, FG)
            if i == self.msel and self.medit is not None:
                box(150, y - 2, 96, 19, (255, 250, 220))
                txt(154, y, self.medit + "_", HDR)
            else:
                txt(154, y, s + (" *" if ov else ""), ORANGE if ov else FG)
            txt(250, y, "g/mol" if i == 0 else "", GRAY)
        txt(6, 190, "0-9: type amu  [del]: reset", GRAY)
        message(self.msg)
        softbar(("BACK", "RESET", "", "MENU", "NEXT"))
    def k_mass(self, k):
        c = self.cmp
        n = len(c.order) + 1
        if self.medit is not None:
            if k == K_ENTER:
                try:
                    v = check_mass_str(self.medit)
                except ChemError as e:
                    self.msg = str(e)
                    return
                if self.msel == 0:
                    c.mass_ov = v
                else:
                    c.el_ov[c.order[self.msel - 1]] = v
                self.medit = None
            elif k == K_CLEAR:
                self.medit = None
            elif k == K_DEL:
                self.medit = self.medit[:-1]
            else:
                ch = num_char(k)
                if ch is not None and ch in "0123456789." and len(self.medit) < 10:
                    self.medit += ch
            return
        ch = num_char(k)
        if ch is not None and ch in "0123456789.":
            self.medit = ch
        elif k == K_UP:
            self.msel = (self.msel - 1) % n
        elif k == K_DOWN:
            self.msel = (self.msel + 1) % n
        elif k == K_DEL:
            if self.msel == 0:
                c.mass_ov = None
            else:
                s = c.order[self.msel - 1]
                if s in c.el_ov:
                    del c.el_ov[s]
        elif k == K_F2:
            c.mass_ov = None
            c.el_ov = {}
        elif k == K_ENTER or k == K_F5:
            self.go("prob")
        elif k == K_F1 or k == K_CLEAR:
            self.go(self.src)
        elif k == K_F4:
            self.go("menu")
    def who_list(self):
        return [None] + self.cmp.order
    def unit_word(self, u, who):
        if u == PT:
            return "atoms" if who is not None else self.cmp.ptype
        return UNIT_NAMES[u]
    def d_prob(self):
        c = self.cmp
        header(form_segs(c.formula) + [("  problem", 0, WHITE)])
        labels = ("Given:", "  unit", "  of", "Find:", "  of")
        ys = (28, 56, 82, 116, 142)
        for i in range(5):
            y = ys[i]
            if i == self.psel:
                box(2, y - 4, W - 4, 24, SEL)
            txt(6, y, labels[i], GRAY if i in (1, 2, 4) else FG)
            x = 84
            if i == 0:
                box(x - 2, y - 2, 180, 20, WHITE)
                x = draw_segs(x, y, entry_num_segs(self.gval))
                if self.psel == 0:
                    box(x + 1, y - 1, 2, 18, HDR)
            elif i in (1, 3):
                cur = self.gu if i == 1 else self.fu
                who = self.gw if i == 1 else self.fw
                for u in (G, MOL, PT):
                    w = self.unit_word(u, who)
                    if u == PT and w != "formula units":   # spelled out on this page
                        w = PSHORT[w]
                    if u == cur:
                        box(x - 3, y - 2, tw(w) + 6, 20, HDR)
                        txt(x, y, w, WHITE)
                    else:
                        txt(x, y, w, FG)
                    x += tw(w) + 14
            else:
                cur = self.gw if i == 2 else self.fw
                for who in self.who_list():
                    segs = form_segs(c.formula) if who is None else [(who, 0, FG)]
                    w = segs_w(segs)
                    if x + w > W - 4:
                        break
                    if who == cur:
                        box(x - 3, y - 2, w + 6, 22, HDR)
                        segs = [(s[0], s[1], WHITE) for s in segs]
                    draw_segs(x, y, segs)
                    x += w + 12
        txt(6, 172, "</>: pick   0-9: shortcut", GRAY)
        message(self.msg)
        softbar(("BACK", "PTCL", "", "MENU", "SOLVE"))
    def k_prob(self, k):
        d = digit(k)
        r = self.psel
        if k == K_UP:
            self.psel = (r - 1) % 5
        elif k == K_DOWN:
            self.psel = (r + 1) % 5
        elif k == K_ENTER or k == K_F5:
            self.resolve()
        elif k == K_F1:
            self.go("mass")
        elif k == K_F2:
            i = PTYPES.index(self.cmp.ptype)
            self.cmp.ptype = PTYPES[(i + 1) % 3]
        elif k == K_F4:
            self.go("menu")
        elif r == 0:
            if k == K_CLEAR:
                if self.gval:
                    self.gval = ""
                else:
                    self.go("mass")
                return
            if k == K_DEL:
                self.gval = self.gval[:-1]
                return
            if k == K_MUL:
                k = K_EE
            ch = num_char(k)
            if ch is None or ch not in "0123456789.E-" or len(self.gval) >= 16:
                return
            if ch == "E" and ("E" in self.gval or not self.gval):
                return
            if ch == "-" and not self.gval.endswith("E"):
                return
            self.gval += ch
        elif r in (1, 3):
            us = (G, MOL, PT)
            cur = self.gu if r == 1 else self.fu
            i = us.index(cur)
            if k == K_LEFT:
                i = (i - 1) % 3
            elif k == K_RIGHT:
                i = (i + 1) % 3
            elif d is not None and 1 <= d <= 3:
                i = d - 1
            elif k == K_CLEAR:
                self.go("mass")
            if r == 1:
                self.gu = us[i]
            else:
                self.fu = us[i]
        else:
            ws = self.who_list()
            cur = self.gw if r == 2 else self.fw
            i = ws.index(cur)
            if k == K_LEFT:
                i = (i - 1) % len(ws)
            elif k == K_RIGHT:
                i = (i + 1) % len(ws)
            elif d is not None and d < len(ws):
                i = d
            elif k == K_CLEAR:
                self.go("mass")
            if r == 2:
                self.gw = ws[i]
            else:
                self.fw = ws[i]
    def resolve(self):
        try:
            args = (self.gval, self.gu, self.gw, self.fu, self.fw)
            self.res = solve(self.cmp, TEACHER, *args)
            self.resp = solve(self.cmp, PRECISE, *args)
        except ChemError as e:
            self.msg = str(e)
            return
        self.hscroll = 0
        self.go("ans")
    def unit_segs(self, u, who, short, c):
        word = self.unit_word(u, who)
        if short and u == PT:
            word = PSHORT[word]
        name = form_segs(self.cmp.formula, c) if who is None else [(who, 0, c)]
        return [(word + " ", 0, c)] + name
    def term_segs(self, num, unit, cancel):
        ucol = GRAY if cancel else FG
        return num_segs(num) + [(" ", 0, FG)] + self.unit_segs(unit[0], unit[1], True, ucol)
    def chain(self):
        """[(x, w, top, bottom, cancel_top)] laid out on one line; total width."""
        PAD = 6
        r = self.res
        g, gunit = r["given"]
        steps = r["steps"]
        items = [(g, gunit, len(steps) > 0, None, None)]
        for i in range(len(steps)):
            st = steps[i]
            items.append((st[1], st[2], i < len(steps) - 1, st[4], st[5]))
        out = []
        x = 0
        for it in items:
            top = self.term_segs(it[0], it[1], it[2])
            bot = self.term_segs(it[3], it[4], True) if it[3] is not None else None
            w = max(segs_w(top), segs_w(bot) if bot else 0) + 2 * PAD
            out.append((x, w, top, bot, it[2]))
            x += w
        eq = [("= ", 0, FG)] + num_segs(r["answer"], GREEN) + [(" ", 0, FG)] + \
            self.unit_segs(r["unit"][0], r["unit"][1], True, GREEN)
        w = segs_w(eq) + 2 * PAD
        out.append((x, w, eq, "EQ", False))
        return out, x + w
    def draw_term(self, x, y, w, top, bot, cancel_top):
        if bot == "EQ":
            draw_segs(x + 6, y + CH // 2 + 2, top)
            return
        tx = x + (w - segs_w(top)) // 2
        xe = draw_segs(tx, y, top)
        if cancel_top:
            ux = xe - segs_w([s for s in top if s[2] == GRAY])
            col(RED)
            draw_line(ux, y + CH // 2, xe - 2, y + CH // 2)
        if bot:
            col(FG)
            draw_line(x + 2, y + CH + 3, x + w - 2, y + CH + 3)
            bx = x + (w - segs_w(bot)) // 2
            be = draw_segs(bx, y + CH + 7, bot)
            ux = be - segs_w([s for s in bot if s[2] == GRAY])
            col(RED)
            draw_line(ux, y + CH + 7 + CH // 2, be - 2, y + CH + 7 + CH // 2)
        col(GRAY)
        draw_line(x + w - 1, y - 2, x + w - 1, y + 2 * CH + 8)
    def max_scroll(self):
        return max(0, self.chain()[1] - (W - 8))
    def d_ans(self):
        c = self.cmp
        mv, ms, ov = molar_mass(c, TEACHER)
        header(form_segs(c.formula) + [("  M=" + ms + ("*" if ov else ""), 0, WHITE)])
        items, total = self.chain()
        y = 34
        for (x, w, top, bot, ct) in items:
            sx = 4 + x - self.hscroll
            if sx + w < 0 or sx > W:
                continue
            self.draw_term(sx, y, w, top, bot, ct)
        if self.hscroll > 0:                              # scroll hints
            box(0, y - 4, 12, 2 * CH + 14, YELLOW)
            txt(1, y + CH // 2, "<", FG)
        if self.hscroll < self.max_scroll():
            box(W - 12, y - 4, 12, 2 * CH + 14, YELLOW)
            txt(W - 11, y + CH // 2, ">", FG)
        col(LIGHT)
        draw_line(0, 86, W, 86)
        rows = ((self.res, "TEACHER", ORANGE, 96), (self.resp, "PRECISE", TEAL, 140))
        for (r, name, cc, yy) in rows:
            box(0, yy - 3, W, 22, ANSBG)
            box(4, yy - 1, 20, 18, cc)
            txt(9, yy, name[0], WHITE)
            for short in (False, True):        # "formula units" -> "f.u." if it won't fit
                segs = [(" = ", 0, FG)] + num_segs(r["answer"], GREEN) + [(" ", 0, FG)] + \
                    self.unit_segs(r["unit"][0], r["unit"][1], short, GREEN)
                if 24 + segs_w(segs) <= W:
                    break
            draw_segs(24, yy, segs)
            draw_segs(28, yy + 21, [("raw ", 0, GRAY)] + num_segs(r["full"], GRAY))
        if self.res["ambiguous"]:
            note = "zeros ambiguous -> 6 s.f."
        elif self.res["capped"]:
            note = "capped at 6 s.f."
        else:
            note = str(self.res["sf"]) + " s.f. (from given)"
        txt(6, 186, note, GRAY)
        if self.max_scroll() > 0:
            txt(6, 202, "</>: scroll the work", GRAY)
        softbar(("EDIT", "MASS", "NEW", "", "MENU"))
    def k_ans(self, k):
        d = digit(k)
        if k == K_F1 or d == 1 or k == K_CLEAR:
            self.go("prob")
        elif k == K_F2 or d == 2:
            self.go("mass")
        elif k == K_F3 or d == 3:
            self.ftext = ""
            self.fnum = False
            self.ltext = ""
            self.gval = ""
            self.go("formula" if self.src == "formula" else "lazy1")
        elif k == K_F5 or d == 5:
            self.go("menu")
        elif k == K_RIGHT:
            self.hscroll = min(self.max_scroll(), self.hscroll + 100)
        elif k == K_LEFT:
            self.hscroll = max(0, self.hscroll - 100)
def main():
    from ti_system import wait_key
    app = App()
    app.draw()
    while app.running:
        app.key(wait_key())
    clear()

main()
