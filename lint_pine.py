#!/usr/bin/env python3
"""Static checks for Pine v6 sources.
Understands multi-line statements: Pine continuation lines must be indented by
a NON-multiple of 4 (a multiple of 4 would start a block instead)."""
import re, sys

KEYWORDS = {"if","else","for","while","switch","var","varip","and","or","not","to","by",
 "break","continue","return","import","export","type","method","enum","true","false","na",
 "int","float","bool","string","color","line","label","box","table","array","matrix","map",
 "series","simple","const","input","polyline","linefill","chart"}
BARE = {"open","high","low","close","volume","hl2","hlc3","ohlc4","hlcc4","time","bar_index",
 "last_bar_index","na","nz","timenow","plot","plotshape","plotchar","bgcolor","barcolor","fill",
 "alertcondition","alert","indicator","strategy","library","max_bars_back","syminfo","timeframe",
 "barstate","ta","math","str","array","request","input","color","label","line","box","table",
 "format","order","position","text","size","shape","location","extend","currency","barmerge"}

def strip_strings(s):
    """Blank out string contents AND trailing comments in one pass, so an
    apostrophe inside a comment is not mistaken for an open quote."""
    out, i, q = [], 0, None
    while i < len(s):
        c = s[i]
        if q:
            if c == "\\": out.append("  "); i += 2; continue
            if c == q: q = None
            out.append(" ")
        else:
            if c in "'\"": q = c; out.append(" ")
            elif c == "/" and i + 1 < len(s) and s[i+1] == "/":
                out.append(" " * (len(s) - i)); break
            else: out.append(c)
        i += 1
    return "".join(out), q

def logical_lines(lines):
    """Yield (start_lineno, [physical line numbers], joined_code)."""
    buf, start, depth, nums = "", None, 0, []
    for n, l in enumerate(lines, 1):
        code, unterm = strip_strings(l)
        if not l.strip() or l.lstrip().startswith("//"):
            if depth == 0:
                continue
        if start is None:
            start, buf, nums = n, "", []
        nums.append(n); buf += (" " + code) if depth else code
        depth += code.count("(") - code.count(")") + code.count("[") - code.count("]")
        if depth <= 0:
            yield start, nums, buf
            start, buf, depth, nums = None, "", 0, []
    if start is not None:
        yield start, nums, buf

def undefined_names(lines):
    """Identifiers referenced but never assigned anywhere in the file.

    Added after a clean lint on a file referencing an undefined group constant
    (G_FILTERS), which is a hard compile error on TradingView. Scoped to the
    prefixes this project uses for module-level constants so it stays quiet on
    builtins and locals.
    """
    src = "\n".join(lines)
    clean, i, n, in_s = [], 0, len(src), None
    while i < n:
        c = src[i]
        if in_s:
            if c == in_s: in_s = None
            clean.append(" ")
        elif c in "\"'":
            in_s = c; clean.append(" ")
        elif c == "/" and i + 1 < n and src[i+1] == "/":
            while i < n and src[i] != "\n": i += 1
            clean.append("\n"); continue
        else:
            clean.append(c)
        i += 1
    clean = "".join(clean)

    assigned = set(re.findall(r"^\s*([A-Za-z_]\w*)\s*(?::=|=)", clean, re.M))
    assigned |= set(re.findall(r"^\s*(?:var\s+)?(?:int|float|bool|string|color|line|label|box|table)\s+([A-Za-z_]\w*)", clean, re.M))
    for grp in re.findall(r"\[([^\]]+)\]\s*=", clean):
        for nm in grp.split(","):
            assigned.add(nm.strip().split()[-1] if nm.strip() else "")
    for params in re.findall(r"^\s*[A-Za-z_]\w*\(([^)]*)\)\s*=>", clean, re.M):
        for prm in params.split(","):
            prm = prm.strip()
            if prm: assigned.add(prm.split()[-1])
    assigned |= set(re.findall(r"^\s*for\s+([A-Za-z_]\w*)\s*=", clean, re.M))

    out = []
    for name in sorted(set(re.findall(r"\b((?:G_|i_|eff)\w*)", clean))):
        if name in assigned: continue
        for ln, text in enumerate(lines, 1):
            if text.lstrip().startswith("//"): continue
            if re.search(r"\b" + re.escape(name) + r"\b", text):
                out.append((ln, "'%s' referenced but never assigned" % name))
                break
    return out


def check(path):
    lines = open(path, encoding="utf-8").read().split("\n")
    errs = []

    for n, l in enumerate(lines, 1):
        if "\t" in l: errs.append((n, "TAB character"))
        _, unterm = strip_strings(l)
        if unterm: errs.append((n, "unterminated string literal"))

    # indentation: statement starts on multiples of 4, continuations on non-multiples
    for start, nums, _ in logical_lines(lines):
        head = lines[start-1]
        ind = len(head) - len(head.lstrip(" "))
        if head.strip() and ind % 4:
            errs.append((start, "statement indent %d is not a multiple of 4" % ind))
        for n in nums[1:]:
            l = lines[n-1]
            if not l.strip() or l.lstrip().startswith("//"): continue
            ci = len(l) - len(l.lstrip(" "))
            if ci % 4 == 0:
                errs.append((n, "continuation indent %d IS a multiple of 4 (Pine reads it as a block)" % ci))

    # stateful builtin inside a ternary branch
    ST = re.compile(r"\b(ta\.\w+|request\.\w+|time)\s*\(")
    for start, nums, code in logical_lines(lines):
        c, _ = strip_strings(code)
        if "?" not in c: continue
        m = ST.search(c[c.index("?"):])
        if m: errs.append((start, "stateful builtin %s() inside ternary branch" % m.group(1)))

    # user function arity
    funcs = {}
    for start, nums, code in logical_lines(lines):
        m = re.match(r"^\s*(\w+)\(([^)]*)\)\s*=>", code)
        if m: funcs[m.group(1)] = (len([p for p in m.group(2).split(",") if p.strip()]), start)
    for fname, (arity, defline) in funcs.items():
        for start, nums, code in logical_lines(lines):
            if start == defline: continue
            for m in re.finditer(r"(?<![\w.])%s\s*\(" % re.escape(fname), strip_strings(code)[0]):
                i, depth, args, cur = m.end(), 1, [], ""
                while i < len(code) and depth:
                    ch = code[i]
                    if ch in "([": depth += 1
                    elif ch in ")]":
                        depth -= 1
                        if not depth: break
                    if depth == 1 and ch == ",": args.append(cur); cur = ""
                    else: cur += ch
                    i += 1
                if cur.strip(): args.append(cur)
                if depth == 0 and len(args) != arity:
                    errs.append((start, "%s() called with %d args, defined with %d" % (fname, len(args), arity)))

    # use before definition
    defined, first_use = {}, {}
    DEF = re.compile(r"^\s*(?:var(?:ip)?\s+)?(?:(?:int|float|bool|string|color|line|label|box|table)(?:\[\])?\s+)?([A-Za-z_]\w*)\s*(?::=|=(?!=))")
    for start, nums, code in logical_lines(lines):
        c, _ = strip_strings(code)
        m = DEF.match(code)
        if m: defined.setdefault(m.group(1), start)
        t = re.match(r"^\s*\[([^\]]+)\]\s*=", code)
        if t:
            for v in t.group(1).split(","): defined.setdefault(v.strip(), start)
        f = re.match(r"^\s*(\w+)\(([^)]*)\)\s*=>", code)
        if f:
            defined.setdefault(f.group(1), start)
            for p in f.group(2).split(","):
                if p.strip(): defined.setdefault(p.strip().split()[-1], start)
        for ident in re.findall(r"(?<![\w.])([A-Za-z_]\w*)", c):
            first_use.setdefault(ident, start)
    for name, d in defined.items():
        u = first_use.get(name)
        if u and u < d and name not in KEYWORDS and name not in BARE:
            errs.append((u, "'%s' used at %d, first defined at %d" % (name, u, d)))

    errs += undefined_names(lines)

    return sorted(set(errs))

bad = 0
for path in sys.argv[1:]:
    e = check(path)
    print("=== %s ===" % path)
    for n, m in e[:30]: print("  line %-5d %s" % (n, m))
    print("  %d issue(s)" % len(e))
    bad += len(e)
sys.exit(1 if bad else 0)
