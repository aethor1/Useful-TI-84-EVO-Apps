# KEYTEST - run on the Evo to check the two things STOICH assumes:
#  1) key codes from ti_system.wait_key()
#  2) ti_draw text size (STOICH assumes 10 px wide, 16 px tall per char)
# Press keys; the code shows on screen. [clear] twice to quit.
from ti_draw import clear, set_color, fill_rect, draw_line, draw_text
from ti_system import wait_key

# What STOICH thinks each code is. Letter fields read a key as its green
# letter, so every key below should show the green letter printed on it.
LETTERS = {50: "A", 44: "B", 45: "C", 132: "D", 182: "D", 183: "E", 185: "F",
           187: "G", 131: "H", 189: "I", 139: "J", 133: "K", 134: "L", 130: "M",
           193: "N", 149: "O", 150: "P", 151: "Q", 129: "R", 191: "S", 146: "T",
           147: "U", 148: "V", 128: "W", 138: "X", 143: "Y", 144: "Z"}
EXPECT = {1: "right", 2: "left", 3: "up", 4: "down", 5: "enter", 9: "clear",
          10: "del", 73: "f1 y=", 72: "f2 window", 46: "f3 zoom", 90: "f4 trace",
          68: "f5 graph", 64: "quit", 135: "[", 136: "]", 140: "(-)", 141: ".",
          152: "EE", 180: "x,t,0,n"}
for i in range(10):
    EXPECT[142 + i] = str(i)
for c in LETTERS:
    EXPECT[c] = EXPECT.get(c, "") + " letter " + LETTERS[c]
for i in range(26):
    EXPECT[154 + i] = "alpha " + chr(65 + i)


def ruler():
    clear()
    set_color(255, 255, 255)
    fill_rect(0, 0, 320, 240)
    set_color(0, 0, 0)
    draw_text(0, 0, "0123456789ABCDEFGHIJ")
    draw_text(0, 16, "MMMMMMMMMM iiiiiiiiii")
    set_color(220, 0, 0)
    for x in range(0, 321, 10):
        draw_line(x, 34, x, 40 if x % 50 else 46)
    draw_line(0, 16, 320, 16)
    set_color(0, 0, 0)
    draw_text(0, 50, "red ticks every 10 px")
    draw_text(0, 66, "× = times sign?  · = dot?")
    draw_text(0, 100, "press keys ([clear] x2 quits)")


ruler()
last = None
while True:
    k = wait_key()
    set_color(255, 255, 255)
    fill_rect(0, 130, 320, 60)
    set_color(0, 0, 160)
    draw_text(0, 134, "code: " + str(k))
    draw_text(0, 154, "STOICH thinks: " + EXPECT.get(k, "?"))
    if k == 9 and last == 9:
        break
    last = k
clear()
