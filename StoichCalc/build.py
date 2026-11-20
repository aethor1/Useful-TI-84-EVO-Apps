"""Bundle src/*.py into one calculator file: dist/STOICH.py
(one file = nothing to break if the Evo can't import between scripts)."""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
PARTS = ["chemdata.py", "chemcore.py", "stoich_ui.py"]
LOCAL = ("from chemdata import", "from chemcore import")


def strip_local_imports(src):
    out = []
    skipping = False
    for line in src.splitlines():
        if line.startswith(LOCAL):
            skipping = line.rstrip().endswith("(") or "(" in line and ")" not in line
            continue
        if skipping:
            if ")" in line:
                skipping = False
            continue
        s = line.strip()
        if not s or s.startswith("#"):      # drop blank/comment lines (saves calc RAM)
            continue
        out.append(line.rstrip())
    return "\n".join(out)


def build():
    chunks = ["# STOICH - stoichiometry / mole conversions for the TI-84 Evo",
              "# Built from src/ by build.py - edit the sources, not this file.", ""]
    for p in PARTS:
        with open(os.path.join(HERE, "src", p), encoding="utf-8") as f:
            chunks.append("# ===== " + p)
            chunks.append(strip_local_imports(f.read()))
    chunks.append("\nmain()\n")
    os.makedirs(os.path.join(HERE, "dist"), exist_ok=True)
    out = os.path.join(HERE, "dist", "STOICH.py")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(chunks))
    return out


if __name__ == "__main__":
    p = build()
    print(p, os.path.getsize(p), "bytes")
