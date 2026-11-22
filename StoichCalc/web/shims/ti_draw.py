# Browser shim for TI's ti_draw: forwards to JS canvas functions (web/evo.js).
# Mimics the Evo quirks: fill_rect paints only inside its box border, a 1-px
# size errors, and draw_text's y sits below the letters (glyphs at y-17..y-3).
import js


def clear():
    js.tiClear()


def set_color(r, g, b):
    js.tiColor(int(r), int(g), int(b))


def fill_rect(x, y, w, h):
    if w < 2 or h < 2:
        raise ValueError("tidrawException: fill_rect size must be >= 2")
    js.tiFillRect(int(x) + 1, int(y) + 1, int(w) - 1, int(h) - 1)


def draw_line(x1, y1, x2, y2):
    js.tiLine(int(x1), int(y1), int(x2), int(y2))


def draw_text(x, y, s):
    js.tiText(int(x), int(y) - 17, str(s))
