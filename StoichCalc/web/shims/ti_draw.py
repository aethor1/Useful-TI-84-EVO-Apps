# Browser shim for TI's ti_draw: forwards to JS canvas functions (web/evo.js).
import js

_c = [0, 0, 0]


def clear():
    js.tiClear()


def set_color(r, g, b):
    _c[0], _c[1], _c[2] = int(r), int(g), int(b)
    js.tiColor(_c[0], _c[1], _c[2])


def fill_rect(x, y, w, h):
    js.tiFillRect(int(x), int(y), int(w), int(h))


def draw_rect(x, y, w, h):
    js.tiDrawRect(int(x), int(y), int(w), int(h))


def draw_line(x1, y1, x2, y2):
    js.tiLine(int(x1), int(y1), int(x2), int(y2))


def draw_text(x, y, s):
    js.tiText(int(x), int(y), str(s))


def show_draw():
    pass
