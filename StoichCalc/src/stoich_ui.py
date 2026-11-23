# stoich_ui.py - screens + key handling for the TI-84 Evo (ti_draw + ti_system).
# Event driven: App.key(code) updates state and redraws. On the calculator,
# main() feeds it ti_system.wait_key(); the web demo feeds it clicks.
from ti_draw import set_color, fill_rect, draw_line, draw_text
from chemcore import (PRECISE, G, MOL, PT, ChemError,
                      parse_formula, parse_symbols, compound_from_formula,
                      compound_from_counts, molar_mass,
                      solve, candidates, PTYPES, PSHORT)

# ---------------------------------------------------------------- tunables
# Evo ti_draw: drawable area is 320x210, 10 px per character, and draw_text's
# y is BELOW the letters (glyphs fill y-17 .. y-3), hence TEXT_DY.
W = 320
H = 210
CW = 10
CH = 16          # line height used for layout (glyphs are 15 px tall)
TEXT_DY = 17
TIMES = "x"      # ASCII: the Evo font's support for the x-sign glyph is unverified
DOT = "."        # hydrate dot

# ---------------------------------------------------------------- key codes
# Evo ti_system.wait_key() returns TI-BASIC getKey codes (row*10 + column):
# [2nd] and [alpha] come in as their own presses (21, 31), so 2nd is tracked here.
K_F1, K_F2, K_F3, K_F4, K_F5 = 11, 12, 13, 14, 15   # y= window zoom trace graph
K_2ND, K_MODE, K_DEL = 21, 22, 23
K_LEFT, K_UP, K_RIGHT, K_DOWN = 24, 25, 26, 34
K_ALPHA, K_VARX = 31, 32     # [x,t,theta,n]: 123/ABC toggle, lazy separator
K_CLEAR, K_ENTER = 45, 105
K_COMMA, K_LPAR, K_RPAR = 62, 63, 64
K_DOT, K_NEG = 103, 104
DIGIT_KEYS = {102: 0, 92: 1, 93: 2, 94: 3, 82: 4, 83: 5, 84: 6, 72: 7, 73: 8, 74: 9}
K_MUL = 65                   # [x] key
# The Evo moved the operator keys around; which code each one sends is unverified,
# so accept both the 84+ code and the Evo-position code where it's harmless.
TIMES_KEYS = (65, 75)
MINUS_KEYS = (75, 85)
# [2nd] combos become these virtual codes
K_QUIT, K_EE, K_LBRK, K_RBRK = 2022, 2062, 2063, 2064
# Green letter printed on each key (same spots as the 84+). Letter fields read
# keys through this, so they act as if A-lock is always on.
LETTER_KEYS = {41: "A", 42: "B", 43: "C", 51: "D", 52: "E", 53: "F", 54: "G", 55: "H",
               61: "I", 62: "J", 63: "K", 64: "L", 65: "M", 71: "N", 72: "O", 73: "P",
               74: "Q", 75: "R", 81: "S", 82: "T", 83: "U", 84: "V", 85: "W", 91: "X",
               92: "Y", 93: "Z"}

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


# ---------------------------------------------------------------- drawing helpers
# Screens don't draw directly: box/ln/txt build a display list, and present()
# repaints only the rectangles where it differs from what's already on screen
# (redrawing all 320x210 px per key is slow and flashes on the Evo).
BOX, LINE, TXT = 0, 1, 2
_ops = []                # frame being built
_shown = [None]          # ops on screen now; None = unknown, repaint everything
_cur = [None]


def col(c):
    if _cur[0] != c:             # set_color is slow on the Evo: skip repeats
        _cur[0] = c
        set_color(c[0], c[1], c[2])


def box(x, y, w, h, c):
    if w >= 1 and h >= 1:
        _ops.append((BOX, x, y, x + w - 1, y + h - 1, c))


def ln(x1, y1, x2, y2, c):
    # shortcut: lines must be horizontal/vertical, so clipping one to a rect is
    # just its bbox; a diagonal line would need real clipping.
    _ops.append((LINE, min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2), c))


def txt(x, y, s, c=FG):
    if s:
        _ops.append((TXT, x, y, s, c))


def bbox(o):
    if o[0] == TXT:              # glyphs fill y..y+14 here, 10 px per char
        return (o[1], o[2] - 1, o[1] + len(o[3]) * CW - 1, o[2] + CH)
    return o[1:5]


def cells(o, r):
    """Text can't be clipped, but a substring can be drawn: the char cells of
    text op o that rect r touches -> (their bbox, first index, last index)."""
    x = o[1]
    i = max(0, (r[0] - x) // CW)
    j = min(len(o[3]) - 1, (r[2] - x) // CW)
    return (x + i * CW, o[2] - 1, x + j * CW + CW - 1, o[2] + CH), i, j


def _hit(a, b):
    return a[0] <= b[2] and b[0] <= a[2] and a[1] <= b[3] and b[1] <= a[3]


def _join(a, b):
    return (min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3]))


def _merge(rs):
    """Union rects that touch until none do."""
    out = []
    for r in rs:
        i = 0
        while i < len(out):
            if _hit(r, out[i]):
                r = _join(r, out.pop(i))
                i = 0
            else:
                i += 1
        out.append(r)
    return out


def dirty(old, new):
    """Rects to repaint: wherever an op appeared or vanished, merged where they
    touch and grown until no character straddles an edge. Merging first keeps
    this ~linear: scrolling changes ~100 ops, and growing each one separately
    cost ~25k rect checks (about 1 s per key on the Evo)."""
    if old is None:
        return [(0, 0, W - 1, H - 1)]
    so, sn = set(old), set(new)
    scr = (0, 0, W - 1, H - 1)
    rs = [bbox(o) for o in old if o not in sn] + [bbox(o) for o in new if o not in so]
    rs = [r for r in rs if _hit(r, scr)]       # scrolled-off parts need no paint
    texts = [(bbox(o), o) for o in new if o[0] == TXT]
    grew = True
    while grew:
        rs = _merge(rs)
        grew = False
        for k in range(len(rs)):
            r = rs[k]
            for b, t in texts:
                if _hit(r, b):
                    r = _join(r, cells(t, r)[0])
            if r != rs[k]:
                rs[k] = r
                grew = True
    return rs


def _fill(b, c):
    """Exact fill of bbox b. Evo fill_rect paints only inside its box border
    (x+1.., w-1 wide), and errors on a size of 1."""
    col(c)
    fill_rect(b[0] - 1, b[1] - 1, b[2] - b[0] + 2, b[3] - b[1] + 2)


def paint(r, ops):
    """Background, then every op touching r in order, clipped to r (text by
    drawing just the chars inside it; dirty() made r hold whole chars)."""
    x0, y0, x1, y1 = max(r[0], 0), max(r[1], 0), min(r[2], W - 1), min(r[3], H - 1)
    if x0 > x1 or y0 > y1:
        return
    r = (x0, y0, x1, y1)
    _fill(r, BG)
    for o in ops:
        if not _hit(bbox(o), r):
            continue
        if o[0] == TXT:
            c, i, j = cells(o, r)
            col(o[4])
            draw_text(c[0], o[2] + TEXT_DY, o[3][i:j + 1])
            continue
        b = (max(o[1], x0), max(o[2], y0), min(o[3], x1), min(o[4], y1))
        if o[0] == BOX:
            _fill(b, o[5])
        else:
            col(o[5])
            draw_line(b[0], b[1], b[2], b[3])


def present():
    _cur[0] = None
    new = _ops[:]
    del _ops[:]
    for r in dirty(_shown[0], new):
        paint(r, new)
    _shown[0] = new


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
            ln(i * 64, H - 19, i * 64, H - 1, GRAY)
        if lab:
            txt(i * 64 + (64 - tw(lab)) // 2, H - 18, lab, HDR)


MSG_Y = H - 37


def message(s, c=RED):
    if s:
        txt(4, MSG_Y, s[:W // CW - 1], c)


def hint(app, y, s, c=None):
    """Bottom hint line; the error message takes its place when there is one."""
    if not (app.msg and y + CH > MSG_Y):
        txt(6, y, s, c or GRAY)


# ---------------------------------------------------------------- key decoding
def letter_of(k):
    """Letter for a key in a letters-only field (auto A-lock), else None."""
    return LETTER_KEYS.get(k)


def num_char(k):
    """Character for a key in a number/punctuation context, else None."""
    if k in DIGIT_KEYS:
        return str(DIGIT_KEYS[k])
    return {K_DOT: ".", K_LPAR: "(", K_RPAR: ")", K_LBRK: "[", K_RBRK: "]",
            K_NEG: "-", K_EE: "E"}.get(k)


def digit(k):
    return DIGIT_KEYS.get(k)


def drop_last_symbol(s):
    """Backspace: removes a whole 2-letter symbol at once (NaCl -> Na)."""
    if len(s) >= 2 and s[-1].islower():
        return s[:-2]
    return s[:-1]


# ---------------------------------------------------------------- the app
MENU = ("Formula entry", "Lazy entry (element list)", "Quit")
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
        self.psel = 0
        self.gval = ""
        self.gu, self.gw, self.fu, self.fw = G, None, MOL, None
        self.res = None            # solved problem (Precise constants)
        self.hscroll = 0
        self.second = False        # [2nd] was the last key
        self._chain = None
        _shown[0] = None           # new run: screen contents unknown

    # ----- top level
    def key(self, k):
        if k == K_2ND:
            self.second = not self.second
            self.draw()
            return
        if k == K_ALPHA:           # letter fields never need [alpha]
            return
        if self.second:
            self.second = False
            if k in (K_MODE, K_COMMA, K_LPAR, K_RPAR):
                k += 2000          # quit, EE, [, ]
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
        getattr(self, "d_" + self.scr)()
        if self.pick is not None:
            self.d_pick()
        if self.second:                    # '2nd' tag at the top right
            box(W - 40, 0, 40, 20, YELLOW)
            txt(W - 35, 2, "2nd", FG)
        present()

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
            self.go(("formula", "lazy1", "quit")[self.sel])
            if self.scr == "quit":
                self.running = False
        elif k == K_F5:
            self.running = False

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
                txt(6, 80, line[:31], FG)
                txt(6, 98, "M = " + molar_mass(c, PRECISE)[1] + " g/mol", GREEN)
                txt(6, 116, c.ptype, GRAY)
            except ChemError as e:
                s = str(e)
                txt(6, 80, s[:31], RED)
                if len(s) > 31:
                    txt(6, 98, s[31:62], RED)
        txt(6, 136, "[x,t,0,n]: ABC / 123", HDR)
        hint(self, 154, "123: digits ( ) [.]=dot")
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
        elif not self.fnum:
            L = letter_of(k)
            if L:
                self.letter_typed(L, "f")
        else:
            ch = "*" if (k == K_DOT or k in TIMES_KEYS) else num_char(k)
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
            c.ptype = old.ptype
        self.go("prob")

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
        if self.lsel > 5:
            top = self.lsel - 5
        for i in range(top, min(len(self.lsyms), top + 6)):
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

    # ----- Given / Find
    def who_list(self):
        return [None] + self.cmp.order

    def unit_word(self, u, who):
        if u == PT:
            return "atoms" if who is not None else self.cmp.ptype
        return UNIT_NAMES[u]

    def unit_opts(self, who):
        """Unit chips: (unit, label, particle type it sets). An element's
        particles are always atoms; a compound lists every particle type."""
        ps = PTYPES if who is None else ("atoms",)
        return [(G, "g", None), (MOL, "mol", None)] + [(PT, PSHORT[p], p) for p in ps]

    def unit_idx(self, u, who):
        if u != PT:
            return 0 if u == G else 1
        return 2 if who is not None else 2 + PTYPES.index(self.cmp.ptype)

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
                who = self.gw if i == 1 else self.fw
                cur = self.unit_idx(self.gu if i == 1 else self.fu, who)
                opts = self.unit_opts(who)
                for j in range(len(opts)):
                    w = opts[j][1]
                    if j == cur:
                        box(x - 2, y - 2, tw(w) + 4, 20, HDR)
                        txt(x, y, w, WHITE)
                    else:
                        txt(x, y, w, FG)
                    x += tw(w) + 8
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
        hint(self, 170, "</>: pick   0-9: shortcut")
        message(self.msg)
        softbar(("BACK", "", "", "MENU", "SOLVE"))

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
            self.go(self.src)
        elif k == K_F4:
            self.go("menu")
        elif r == 0:
            if k == K_CLEAR:
                if self.gval:
                    self.gval = ""
                else:
                    self.go(self.src)
                return
            if k == K_DEL:
                self.gval = self.gval[:-1]
                return
            if k == K_COMMA:
                k = K_EE
            elif k in MINUS_KEYS:
                k = K_NEG
            ch = num_char(k)
            if ch is None or ch not in "0123456789.E-" or len(self.gval) >= 16:
                return
            if ch == "E" and ("E" in self.gval or not self.gval):
                return
            if ch == "-" and not self.gval.endswith("E"):
                return
            self.gval += ch
        elif r in (1, 3):
            who = self.gw if r == 1 else self.fw
            us = self.unit_opts(who)
            i = self.unit_idx(self.gu if r == 1 else self.fu, who)
            if k == K_LEFT:
                i = (i - 1) % len(us)
            elif k == K_RIGHT:
                i = (i + 1) % len(us)
            elif d is not None and 1 <= d <= len(us):
                i = d - 1
            elif k == K_CLEAR:
                self.go(self.src)
            u, w, p = us[i]
            if p:
                self.cmp.ptype = p
            if r == 1:
                self.gu = u
            else:
                self.fu = u
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
                self.go(self.src)
            if r == 2:
                self.gw = ws[i]
            else:
                self.fw = ws[i]

    def resolve(self):
        try:
            self.res = solve(self.cmp, PRECISE, self.gval, self.gu, self.gw, self.fu, self.fw)
        except ChemError as e:
            self.msg = str(e)
            return
        self.hscroll = 0
        self._chain = None         # layout is cached per result: scrolling reuses it
        self.go("ans")

    # ----- answer: one-line chain (scrolls left/right), the answer pinned below
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
            ln(ux, y + CH // 2, xe - 2, y + CH // 2, RED)
        if bot:
            ln(x + 2, y + CH + 3, x + w - 2, y + CH + 3, FG)
            bx = x + (w - segs_w(bot)) // 2
            be = draw_segs(bx, y + CH + 7, bot)
            ux = be - segs_w([s for s in bot if s[2] == GRAY])
            ln(ux, y + CH + 7 + CH // 2, be - 2, y + CH + 7 + CH // 2, RED)
        ln(x + w - 1, y - 2, x + w - 1, y + 2 * CH + 8, GRAY)

    def max_scroll(self):
        if self._chain is None:
            self._chain = self.chain()
        return max(0, self._chain[1] - (W - 8))

    def d_ans(self):
        c = self.cmp
        header(form_segs(c.formula) + [("  M=" + molar_mass(c, PRECISE)[1], 0, WHITE)])
        self.max_scroll()
        items, total = self._chain
        y = 28
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
        ln(0, 72, W - 1, 72, LIGHT)
        # y >= 82 so exponents (y-6) clear the chain's subscripts (to y 72): if they
        # touched, every scroll would repaint the answer rows too
        r = self.res
        box(0, 79, W, 22, ANSBG)
        for short in (False, True):            # "formula units" -> "f.u." if it won't fit
            segs = [("= ", 0, FG)] + num_segs(r["answer"], GREEN) + [(" ", 0, FG)] + \
                self.unit_segs(r["unit"][0], r["unit"][1], short, GREEN)
            if 6 + segs_w(segs) <= W:
                break
        draw_segs(6, 82, segs)
        draw_segs(10, 102, [("raw ", 0, GRAY)] + num_segs(r["full"], GRAY))
        if r["ambiguous"]:
            note = "zeros ambiguous -> 6 s.f."
        elif r["capped"]:
            note = "capped at 6 s.f."
        else:
            note = str(r["sf"]) + " s.f. (from given)"
        txt(6, 124, note, GRAY)
        if self.max_scroll() > 0:
            txt(6, 142, "</>: scroll the work", GRAY)
        softbar(("EDIT", "", "NEW", "", "MENU"))

    def k_ans(self, k):
        d = digit(k)
        if k == K_F1 or d == 1 or k == K_CLEAR:
            self.go("prob")
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
    try:
        app.draw()
        while app.running:
            app.key(wait_key())
    except Exception as e:                # show it instead of dying silently
        del _ops[:]
        _shown[0] = None
        txt(4, 4, "STOICH error (screen: " + app.scr + ")", RED)
        s = repr(e)
        for i in range(0, min(len(s), 31 * 8), 31):
            txt(4, 24 + i // 31 * CH, s[i:i + 31], FG)
        txt(4, 170, "any key: exit", GRAY)
        present()
        wait_key()
