# stoich_ui.py - screens + key handling for the TI-84 Evo (ti_draw + ti_system).
# Event driven: App.key(code) updates state and redraws. On the calculator,
# main() feeds it ti_system.wait_key(); the web demo feeds it clicks.
from ti_draw import clear, set_color, fill_rect, draw_line, draw_text
from chemcore import (TEACHER, PRECISE, G, MOL, PT, ChemError,
                      parse_formula, parse_symbols, compound_from_formula,
                      compound_from_counts, elem_mass, molar_mass, check_mass_str,
                      solve, candidates, PTYPES, PSHORT)

# ---------------------------------------------------------------- tunables
W = 320
H = 240
CW = 10          # assumed ti_draw character width  (check with KEYTEST)
CH = 16          # assumed line height
TEXT_DY = 0      # shift if draw_text's y turns out to be the baseline
TIMES = "×"  # multiplication sign; change to "x" if it shows as junk
DOT = "·"    # hydrate dot

# ---------------------------------------------------------------- key codes
# TI-OS GetKey codes as returned by ti_system.wait_key() on the CE Python.
# If KEYTEST shows different numbers on the Evo, edit them here.
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
# Letter printed (green) on each key -> that key's plain code. Letter fields
# read keys through this, so they act as if A-lock is always on.
LETTER_KEYS = {50: "A", 44: "B", 45: "C", 132: "D", 182: "D", 183: "E", 185: "F",
               187: "G", 131: "H", 189: "I", 139: "J", 133: "K", 134: "L", 130: "M",
               193: "N", 149: "O", 150: "P", 151: "Q", 129: "R", 191: "S", 146: "T",
               147: "U", 148: "V", 128: "W", 138: "X", 143: "Y", 144: "Z"}

# ---------------------------------------------------------------- colors
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


# ---------------------------------------------------------------- drawing helpers
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


# ---------------------------------------------------------------- key decoding
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


# ---------------------------------------------------------------- the app
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

    # ----- top level
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

    # ----- element picker (pops up when a letter starts several symbols)
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

    # ----- menu
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

    # ----- help
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

    # ----- formula entry
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

    # ----- lazy entry, step 1: element list (letters only, auto A-lock)
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

    # ----- lazy entry, step 2: counts
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

    # ----- masses / amu override
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

    # ----- Given / Find
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

    # ----- answer: one-line chain (scrolls left/right), both answers pinned below
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
