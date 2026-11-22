# KEYTEST - run on the Evo to check what STOICH assumes:
#  1) key codes from ti_system.wait_key() (TI-BASIC getKey style)
#  2) ti_draw text: 10 px per char, letters sit ABOVE draw_text's y
# Press keys; the code shows on screen. [clear] twice to quit.
from ti_draw import set_color, fill_rect, draw_line, draw_text
from ti_system import wait_key

LETTERS = {41: "A", 42: "B", 43: "C", 51: "D", 52: "E", 53: "F", 54: "G", 55: "H",
           61: "I", 62: "J", 63: "K", 64: "L", 65: "M", 71: "N", 72: "O", 73: "P",
           74: "Q", 75: "R", 81: "S", 82: "T", 83: "U", 84: "V", 85: "W", 91: "X",
           92: "Y", 93: "Z"}
EXPECT = {11: "f1 y=", 12: "f2 window", 13: "f3 zoom", 14: "f4 trace", 15: "f5 graph",
          21: "2nd", 22: "mode", 23: "del", 24: "left", 25: "up", 26: "right",
          34: "down", 31: "alpha", 32: "x,t,0,n", 45: "clear", 62: ",", 63: "(",
          64: ")", 65: "x (times)?", 75: "x or -?", 85: "- or +?", 103: ".",
          104: "(-)", 105: "enter"}
for k, v in {102: 0, 92: 1, 93: 2, 94: 3, 82: 4, 83: 5, 84: 6, 72: 7, 73: 8, 74: 9}.items():
    EXPECT[k] = str(v)
for c in LETTERS:
    EXPECT[c] = EXPECT.get(c, "") + " letter " + LETTERS[c]


def ruler():
    set_color(255, 255, 255)
    fill_rect(-1, -1, 321, 211)
    set_color(0, 0, 0)
    draw_text(0, 17, "0123456789ABCDEFGHIJ")
    draw_text(0, 34, "MMMMMMMMMM iiiiiiiiii")
    set_color(220, 0, 0)
    for x in range(0, 320, 10):
        draw_line(x, 38, x, 44 if x % 50 else 50)
    draw_line(0, 17, 319, 17)
    set_color(0, 0, 0)
    draw_text(0, 70, "red ticks every 10 px")
    try:
        draw_text(0, 88, "× = times sign?  · = dot?")
    except Exception:
        draw_text(0, 88, "unicode glyphs: error")
    draw_text(0, 120, "press keys ([clear] x2 quits)")


ruler()
last = None
while True:
    k = wait_key()
    set_color(255, 255, 255)
    fill_rect(-1, 130, 321, 50)
    set_color(0, 0, 160)
    draw_text(0, 152, "code: " + str(k))
    draw_text(0, 172, "STOICH thinks: " + EXPECT.get(k, "?"))
    if k == 45 and last == 45:
        break
    last = k
