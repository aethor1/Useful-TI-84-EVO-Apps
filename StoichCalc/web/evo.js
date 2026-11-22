// TI-84 Evo replica: canvas backend for the ti_draw shim + keypad that feeds
// key codes into the same stoich_ui.App the calculator runs.
"use strict";

const SCALE = 3, CW = 10, CH = 16, H = 210;              // must match stoich_ui.py
const cv = document.getElementById("scr");
const ctx = cv.getContext("2d");
ctx.scale(SCALE, SCALE);
let color = "rgb(0,0,0)";

// ---------- ti_draw backend (called from web/shims/ti_draw.py)
window.tiClear = () => { ctx.fillStyle = "#fff"; ctx.fillRect(0, 0, 320, H); };
window.tiColor = (r, g, b) => { color = `rgb(${r},${g},${b})`; };
window.tiFillRect = (x, y, w, h) => { ctx.fillStyle = color; ctx.fillRect(x, y, w, h); };
window.tiLine = (x1, y1, x2, y2) => {
  ctx.strokeStyle = color; ctx.lineWidth = 1;
  ctx.beginPath(); ctx.moveTo(x1 + .5, y1 + .5); ctx.lineTo(x2 + .5, y2 + .5); ctx.stroke();
};
window.tiText = (x, y, s) => {
  // fixed 10x16 cells so the layout matches what stoich_ui.py measured
  ctx.fillStyle = color;
  ctx.font = '600 14px "Consolas", "DejaVu Sans Mono", "Menlo", monospace';
  ctx.textBaseline = "top";
  let i = 0;
  for (const ch of s) {
    const w = ctx.measureText(ch).width;
    ctx.fillText(ch, x + i * CW + (CW - w) / 2, y + 1);
    i++;
  }
};

// ---------- keypad definition (layout from TI's Evo product photos)
// k = the TI-BASIC getKey code the Evo's wait_key() returns (row*10 + column).
const KEYS = [
  { t: "y=", k: 11, s: "stat plot", c: "fn" }, { t: "window", k: 12, s: "tblset", c: "fn" },
  { t: "zoom", k: 13, s: "format", c: "fn" }, { t: "trace", k: 14, s: "calc", c: "fn" },
  { t: "graph", k: 15, s: "table", c: "fn" },
  { t: "2nd", id: "2nd", k: 21, c: "k2nd" }, { t: "mode", k: 22, s: "quit" }, { t: "del", k: 23, s: "ins" },
  { dpad: true },
  { t: "alpha", id: "alpha", k: 31, c: "kalpha", s: "A-lock" }, { t: "X,T,θ,n", k: 32, s: "link", c: "small" },
  { t: "stat", k: 33, s: "list" },
  { t: "math", k: 41, s: "test", a: "A" }, { t: "▫/▫", k: 42, s: "", a: "B" },
  { t: "prgm", k: 43, s: "draw", a: "C" }, { t: "vars", k: 44, s: "matrix" }, { t: "clear", k: 45, s: "undo" },
  { t: "x▫", k: 51, s: "√", a: "D" }, { t: "sin", k: 52, s: "sin⁻¹", a: "E" },
  { t: "cos", k: 53, s: "cos⁻¹", a: "F" }, { t: "tan", k: 54, s: "tan⁻¹", a: "G" },
  { t: "÷", k: 55, s: "π", a: "H" },
  { t: "x²", k: 61, s: "√", a: "I" }, { t: ",", k: 62, s: "EE", a: "J" },
  { t: "(", k: 63, s: "{", a: "K" }, { t: ")", k: 64, s: "}", a: "L" }, { t: "×", k: 65, s: "e", a: "M" },
  { t: "log", k: 71, s: "10ˣ", a: "N" }, { t: "7", k: 72, s: "u", a: "O", c: "num" },
  { t: "8", k: 73, s: "v", a: "P", c: "num" }, { t: "9", k: 74, s: "w", a: "Q", c: "num" },
  { t: "−", k: 75, s: "[", a: "R" },
  { t: "ln", k: 81, s: "eˣ", a: "S" }, { t: "4", k: 82, s: "L4", a: "T", c: "num" },
  { t: "5", k: 83, s: "L5", a: "U", c: "num" }, { t: "6", k: 84, s: "L6", a: "V", c: "num" },
  { t: "+", k: 85, s: "]", a: "W" },
  { t: "sto→", k: 91, s: "recall", a: "X", c: "small" }, { t: "1", k: 92, s: "L1", a: "Y", c: "num" },
  { t: "2", k: 93, s: "L2", a: "Z", c: "num" }, { t: "3", k: 94, s: "L3", a: "θ", c: "num" },
  { t: "◂▸", k: 95, s: "mem", a: "\"" },
  { t: "on ⌂", id: "on", s: "off", c: "small on" }, { t: "0", k: 102, s: "catalog", a: "␣", c: "num" },
  { t: ".", k: 103, s: "i", a: ":", c: "num" }, { t: "(−)", k: 104, s: "ans", a: "?", c: "num" },
  { t: "enter", k: 105, s: "entry" },
];
const LETTER = {};                       // green letter -> key code (PC keyboard)
for (const d of KEYS) if (d.a && /^[A-Z]$/.test(d.a)) LETTER[d.a] = d.k;
const DIGIT = [102, 92, 93, 94, 82, 83, 84, 72, 73, 74];

const keysEl = document.getElementById("keys");
const byCode = {};
let shift = false;

function mk(def) {
  const b = document.createElement("button");
  b.className = "key " + (def.c || "");
  b.type = "button";
  b.innerHTML = `${def.s ? `<span class="sec">${def.s}</span>` : ""}${def.a ? `<span class="al">${def.a}</span>` : ""}${def.t}`;
  b.addEventListener("click", () => press(def));
  if (def.k != null) byCode[def.k] = b;
  return b;
}
for (const def of KEYS) {
  if (def.dpad) {
    const d = document.createElement("div");
    d.className = "dpad";
    for (const [cls, code, lab] of [["u", 25, "▲"], ["d", 34, "▼"], ["l", 24, "◀"], ["r", 26, "▶"]]) {
      const b = document.createElement("button");
      b.className = cls; b.type = "button"; b.textContent = lab; b.setAttribute("aria-label", "arrow " + cls);
      b.addEventListener("click", () => send(code));
      byCode[code] = b;
      d.appendChild(b);
    }
    keysEl.appendChild(d);
  } else keysEl.appendChild(mk(def));
}

function indicators() {
  document.getElementById("ind2nd").classList.toggle("on", shift);
}

// Like the Evo: [2nd] and [alpha] are keys of their own; STOICH tracks 2nd itself.
function press(def) {
  if (def.id === "on") { shift = false; indicators(); if (!running) start(); return; }
  shift = def.id === "2nd" ? !shift : false;
  indicators();
  send(def.k);
}

// ---------- Python
let py = null, running = false;
const SRC = ["../src/chemdata.py", "../src/chemcore.py", "../src/stoich_ui.py", "shims/ti_draw.py"];

function showErr(e) {
  const el = document.getElementById("err");
  el.hidden = false; el.textContent = String(e);
}

function start() {
  try {
    py.runPython("app = stoich_ui.App()\napp.draw()");
    running = true;
  } catch (e) { showErr(e); }
}

function send(code) {
  const b = byCode[code];
  if (b) { b.classList.add("flash"); setTimeout(() => b.classList.remove("flash"), 90); }
  if (!py || !running) return;
  try {
    py.runPython(`app.key(${code})`);
    if (!py.runPython("app.running")) {
      running = false;
      tiColor(25, 55, 120); tiFillRect(0, 0, 320, H);
      tiColor(255, 255, 255);
      tiText(60, 100, "Program ended.");
      tiText(60, 124, "Press [on] to run again");
    }
  } catch (e) { showErr(e); }
}

async function boot() {
  try {
    py = await loadPyodide();
    for (const p of SRC) {
      const r = await fetch(p, { cache: "no-store" });
      if (!r.ok) throw new Error("Could not load " + p + " (serve the StoichCalc folder, not web/)");
      py.FS.writeFile(p.split("/").pop(), await r.text());
    }
    py.runPython("import sys\nsys.path.insert(0, '.')\nimport stoich_ui");
    document.getElementById("loading").hidden = true;
    start();
  } catch (e) {
    document.getElementById("loading").textContent = "Load failed - see panel";
    showErr(e);
  }
}
boot();

// ---------- PC keyboard
// Letters always type letters, digits always type digits: the page presses
// [x,t,θ,n] for you in the formula field when it needs to switch ABC/123.
const PCMAP = {
  ArrowRight: 26, ArrowLeft: 24, ArrowUp: 25, ArrowDown: 34, Enter: 105, Escape: 45,
  Backspace: 23, Delete: 23, F1: 11, F2: 12, F3: 13, F4: 14, F5: 15, Tab: 32,
};
const NUMKEYS = { ".": [103], "*": [103], "(": [63], ")": [64], "-": [104], "_": [104],
  "[": [21, 63], "]": [21, 64] };
const pyv = s => py.runPython(s);
document.addEventListener("keydown", e => {
  if (e.ctrlKey || e.metaKey || e.altKey || !py || !running) return;
  const k = e.key;
  let codes = null;
  const scr = pyv("app.scr");
  if (k in PCMAP) codes = [PCMAP[k]];
  else if ((k === "," || k === " ") && scr === "lazy1") codes = [32];
  else if ((k === "e" || k === "E") && scr === "prob") codes = [62];   // [,] = EE
  else if (/^[0-9]$/.test(k) || k in NUMKEYS) {
    const c = /^[0-9]$/.test(k) ? [DIGIT[+k]] : NUMKEYS[k];
    if (scr === "lazy1") codes = [];
    else if (scr === "formula" && pyv("app.letter_mode()")) codes = [32, ...c];
    else codes = c;
  } else if (/^[a-z]$/.test(k) && pyv(`app.pick is not None and (app.pick[0][0][0] + '${k}') in app.pick[0]`)) {
    e.preventDefault(); pyv(`app.pc_lower('${k}')`); return;
  } else if (/^[a-zA-Z]$/.test(k) && LETTER[k.toUpperCase()]) codes = [LETTER[k.toUpperCase()]];
  if (!codes) return;
  e.preventDefault();
  for (const c of codes) send(c);
});

// ---------- scale the calculator to fit the window height
function fit() {
  const f = document.getElementById("fit"), c = document.getElementById("calc");
  const h = c.offsetHeight, w = c.offsetWidth;
  const s = Math.min(1, (window.innerHeight - 32) / h, (window.innerWidth - 32) / w);
  c.style.transform = `scale(${s})`;
  f.style.height = h * s + "px";
  f.style.width = w * s + "px";
}
window.addEventListener("resize", fit);
fit();
