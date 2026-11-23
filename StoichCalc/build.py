"""Bundle src/*.py into one calculator file: dist/STOICH.py
(one file = nothing to break if the Evo can't import between scripts).
The bundle is minified to save calc RAM: no comments or docstrings, 1-space
indents. Edit src/, never dist/."""
import ast
import io
import os
import tokenize

HERE = os.path.dirname(os.path.abspath(__file__))
PARTS = ["chemdata.py", "chemcore.py", "stoich_ui.py"]
LOCAL = ("chemdata", "chemcore")


def minify(src):
    """Line-based so the original line breaks (and short lines) survive."""
    drop = set()                   # docstring + local-import lines
    for n in ast.walk(ast.parse(src)):
        body = getattr(n, "body", None)
        for s in body if isinstance(body, list) else ():
            if (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant)
                    and isinstance(s.value.value, str)) or \
                    (isinstance(s, ast.ImportFrom) and s.module in LOCAL):
                drop.update(range(s.lineno, s.end_lineno + 1))
    cut = {}                       # line -> column where its comment starts
    for t in tokenize.generate_tokens(io.StringIO(src).readline):
        if t.type == tokenize.COMMENT:
            cut[t.start[0]] = t.start[1]
        elif t.type == tokenize.STRING and t.start[0] != t.end[0] and t.start[0] not in drop:
            raise ValueError("line %d: multi-line string would get re-indented" % t.start[0])
    out = []
    for i, line in enumerate(src.splitlines(), 1):
        line = line[:cut.get(i, len(line))].rstrip()
        if i in drop or not line:
            continue
        n = len(line) - len(line.lstrip(" "))
        out.append(" " * (n // 4) + line[n:])      # 4-space indents -> 1 space
    return "\n".join(out)


def build():
    src = []
    for p in PARTS:
        with open(os.path.join(HERE, "src", p), encoding="utf-8") as f:
            src.append(f.read())
    out = os.path.join(HERE, "dist", "STOICH.py")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write("# STOICH - mole conversions for the TI-84 Evo\n"
                "# Built from src/ by build.py (minified) - edit the sources.\n"
                + minify("\n".join(src)) + "\nmain()\n")
    return out


if __name__ == "__main__":
    p = build()
    print(p, os.path.getsize(p), "bytes")
