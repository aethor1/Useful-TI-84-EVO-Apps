// TI-84 Evo replica: canvas backend for the ti_draw shim + keypad that feeds
// key codes into the same stoich_ui.App the calculator runs.
"use strict";

const SCALE = 3, CW = 10, CH = 16;              // must match stoich_ui.py
const cv = document.getElementById("scr");
const ctx = cv.getContext("2d");
ctx.scale(SCALE, SCALE);
let color = "rgb(0,0,0)";

// ---------- ti_draw backend (called from web/shims/ti_draw.py)
window.tiClear = () => { ctx.fillStyle = "#fff"; ctx.fillRect(0, 0, 320, 240); };
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
const L = c => 154 + c.charCodeAt(0) - 65;     // alpha letter -> key code
const KEYS = [
  { t: "y=", k: 73, s: "stat plot", c: "fn" }, { t: "window", k: 72, s: "tblset", c: "fn" },
  { t: "zoom", k: 46, s: "format", c: "fn" }, { t: "trace", k: 90, s: "calc", c: "fn" },
  { t: "graph", k: 68, s: "table", c: "fn" },
  { t: "2nd", id: "2nd", c: "k2nd" }, { t: "mode", k: 69, s: "quit", s2: 64 }, { t: "del", k: 10, s: "ins", s2: 11 },
  { dpad: true },
  { t: "alpha", id: "alpha", c: "kalpha", s: "A-lock" }, { t: "X,T,θ,n", k: 180, s: "link", c: "small" },
  { t: "stat", k: 49, s: "list" },
  { t: "math", k: 50, s: "test", a: "A" }, { t: "▫/▫", k: 44, s: "", a: "B" },
  { t: "prgm", k: 45, s: "draw", a: "C" }, { t: "vars", k: 53, s: "matrix" }, { t: "clear", k: 9, s: "undo" },
  { t: "x▫", k: 132, s: "√", a: "D" }, { t: "sin", k: 183, s: "sin⁻¹", a: "E" },
  { t: "cos", k: 185, s: "cos⁻¹", a: "F" }, { t: "tan", k: 187, s: "tan⁻¹", a: "G" },
  { t: "÷", k: 131, s: "π", a: "H" },
  { t: "x²", k: 189, s: "√", a: "I" }, { t: ",", k: 139, s: "EE", s2: 152, a: "J" },
  { t: "(", k: 133, s: "{", a: "K" }, { t: ")", k: 134, s: "}", a: "L" }, { t: "×", k: 130, s: "e", a: "M" },
  { t: "log", k: 193, s: "10ˣ", a: "N" }, { t: "7", k: 149, s: "u", a: "O", c: "num" },
  { t: "8", k: 150, s: "v", a: "P", c: "num" }, { t: "9", k: 151, s: "w", a: "Q", c: "num" },
  { t: "−", k: 129, s: "[", s2: 135, a: "R" },
  { t: "ln", k: 191, s: "eˣ", a: "S" }, { t: "4", k: 146, s: "L4", a: "T", c: "num" },
  { t: "5", k: 147, s: "L5", a: "U", c: "num" }, { t: "6", k: 148, s: "L6", a: "V", c: "num" },
  { t: "+", k: 128, s: "]", s2: 136, a: "W" },
  { t: "sto→", k: 138, s: "recall", a: "X", c: "small" }, { t: "1", k: 143, s: "L1", a: "Y", c: "num" },
  { t: "2", k: 144, s: "L2", a: "Z", c: "num" }, { t: "3", k: 145, s: "L3", a: "θ", c: "num" },
  { t: "◂▸", k: null, s: "mem", a: "\"" },
  { t: "on ⌂", id: "on", s: "off", c: "small on" }, { t: "0", k: 142, s: "catalog", a: "␣", ak: 153, c: "num" },
  { t: ".", k: 141, s: "i", a: ":", c: "num" }, { t: "(−)", k: 140, s: "ans", a: "?", c: "num" },
  { t: "enter", k: 5, s: "entry" },
];

const keysEl = document.getElementById("keys");
const byCode = {};
let shift = false, alpha = false, alock = false;

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
    for (const [cls, code, lab] of [["u", 3, "▲"], ["d", 4, "▼"], ["l", 2, "◀"], ["r", 1, "▶"]]) {
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
  document.getElementById("indAlpha").classList.toggle("on", alpha && !alock);
  document.getElementById("indLock").classList.toggle("on", alock);
}

function press(def) {
  if (def.id === "2nd") { shift = !shift; alpha = false; indicators(); return; }
  if (def.id === "alpha") {
    if (shift) { alock = true; shift = false; }
    else if (alock) alock = false;
    else alpha = !alpha;
    indicators(); return;
  }
  if (def.id === "on") { shift = alpha = false; indicators(); if (!running) start(); return; }
  let code = def.k;
  if (shift) { code = def.s2 ?? null; shift = false; }
  else if (alpha || alock) {
    code = def.ak ?? (def.a && /^[A-Z]$/.test(def.a) ? L(def.a) : null);
    if (code == null && (def.k <= 10)) code = def.k;   // arrows/enter/clear still work in A-lock
    alpha = false;
  }
  indicators();
  if (code != null) send(code);
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
      tiColor(25, 55, 120); tiFillRect(0, 0, 320, 240);
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
  ArrowRight: 1, ArrowLeft: 2, ArrowUp: 3, ArrowDown: 4, Enter: 5, Escape: 9,
  Backspace: 10, Delete: 10, F1: 73, F2: 72, F3: 46, F4: 90, F5: 68, Tab: 180,
};
const NUMKEYS = { ".": 141, "(": 133, ")": 134, "*": 130, "-": 129, "_": 140, "[": 135, "]": 136 };
const pyv = s => py.runPython(s);
document.addEventListener("keydown", e => {
  if (e.ctrlKey || e.metaKey || e.altKey || !py || !running) return;
  const k = e.key;
  let codes = null;
  const scr = pyv("app.scr");
  if (k in PCMAP) codes = [PCMAP[k]];
  else if ((k === "," || k === " ") && scr === "lazy1") codes = [180];
  else if ((k === "e" || k === "E") && scr === "prob") codes = [152];   // [2nd][EE]
  else if (/^[0-9]$/.test(k) || k in NUMKEYS) {
    const c = /^[0-9]$/.test(k) ? 142 + +k : NUMKEYS[k];
    if (scr === "lazy1") codes = [];
    else if (scr === "formula" && pyv("app.letter_mode()")) codes = [180, c];
    else codes = [c];
  } else if (/^[a-z]$/.test(k) && pyv(`app.pick is not None and (app.pick[0][0][0] + '${k}') in app.pick[0]`)) {
    e.preventDefault(); pyv(`app.pc_lower('${k}')`); return;
  } else if (/^[a-zA-Z]$/.test(k)) codes = [L(k.toUpperCase())];
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
