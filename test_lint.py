#!/usr/bin/env python3
"""Regression tests for lint_pine.

Written after v5.0 shipped with `tfWarn` referenced and never declared while
the linter reported a clean file. A checker that has never been shown to catch
the bug it exists for is not evidence of anything.
"""
import sys, tempfile, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lint_pine import check

BASE = '''//@version=6
indicator("t", overlay=true)
i_x = input.float(1.0, "x")
lbl = close > open ? "UP" : "DOWN"
val = close > open
     ? high
     : low
f(a, b) =>
    a + b
z = f(1, 2)
plot(val + z, title="v", color=color.new(#FF0000, 0))
'''

CASES = [
    ("clean baseline", BASE, 0),
    ("undeclared identifier (the v5.0 bug)",
     BASE.replace('plot(val + z,', 'plot(val + z + tfWarn,'), 1),
    ("undeclared group constant",
     BASE.replace('input.float(1.0, "x")', 'input.float(1.0, "x", group=G_MISSING)'), 1),
    ("wrong arity on a user function",
     BASE.replace('z = f(1, 2)', 'z = f(1, 2, 3)'), 1),
    ("continuation indented on a multiple of 4",
     BASE.replace('     ? high\n     : low', '    ? high\n    : low'), 2),
    ("stateful builtin inside a ternary",
     BASE.replace('z = f(1, 2)', 'z = val ? ta.sma(close, 5) : 0.0'), 1),
    ("use before definition",
     BASE.replace('i_x = input.float(1.0, "x")',
                  'early = later + 1\nlater = 2\ni_x = input.float(1.0, "x")'), 1),
    ("ternary split across lines is NOT an error", BASE, 0),
    ("function declared inside a block",
     BASE.replace('z = f(1, 2)', 'if val\n    g(a) =>\n        a * 2\n    z2 = g(3)\nz = f(1, 2)'), 1),
]

fails = 0
for name, src, want in CASES:
    fd, p = tempfile.mkstemp(suffix=".pine")
    with os.fdopen(fd, "w") as fh:
        fh.write(src)
    got = check(p)
    os.unlink(p)
    ok = len(got) == want
    print("%-4s %-44s want %d, got %d" % ("ok" if ok else "FAIL", name, want, len(got)))
    if not ok:
        for n, m in got:
            print("        line %d  %s" % (n, m))
        fails += 1
print("\n%d/%d passed" % (len(CASES) - fails, len(CASES)))
sys.exit(1 if fails else 0)
