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

# A wrapped line does not have to be inside an open bracket. Pine also
# continues a statement when the next line begins with an operator, which is how
# a multi-line ternary is written:
#     float x = cond
#          ? a
#          : b
# Treating those as fresh statements made the indent rule fire on legal code,
# and a linter that cries wolf is one you stop reading — which is how v5.0
# shipped with an undeclared identifier in it.
# Matched against the RAW line, never the string-stripped one: blanking a
# literal turns `'{' + rest` into `    + rest`, which then looks like a line
# that opens with an operator when it is an ordinary statement.
CONT_START = re.compile(r"^[ \t]*(\?|:|\+|\*|/|=>|,|\)|\]|and\b|or\b)")
# The other half of the same rule — the break can sit at the end of the line
# instead of the start of the next one.
# Deliberately NARROW. A first attempt matched any trailing operator and
# swallowed whole files into one logical line, turning 1 finding into 130.
# Only the ternary split is handled here; every other wrap in this codebase
# either sits inside brackets or opens the next line with an operator.
CONT_END = re.compile(r"[?:][ \t]*$")


def code_only(s):
    """The raw line with any trailing comment removed and STRING LITERALS LEFT
    INTACT. The continuation tests must run on this, not on the blanked form:
    `x = cond ? "BULL" : "BEAR"` blanks to something ending in `:`, which reads
    as a ternary split across lines and swallows the rest of the file."""
    i, q = 0, None
    while i < len(s):
        c = s[i]
        if q:
            if c == "\\":
                i += 2
                continue
            if c == q:
                q = None
        elif c in "'\"":
            q = c
        elif c == "/" and i + 1 < len(s) and s[i+1] == "/":
            return s[:i]
        i += 1
    return s


def logical_lines(lines):
    """Yield (start_lineno, [physical line numbers], joined_code)."""
    def next_is_cont(i, raw):
        if CONT_END.search(code_only(raw).rstrip()):
            return True
        for j in range(i + 1, len(lines)):
            s = lines[j]
            if not s.strip() or s.lstrip().startswith("//"):
                continue
            return bool(CONT_START.match(s))
        return False

    buf, start, depth, nums = "", None, 0, []
    for n, l in enumerate(lines, 1):
        code, unterm = strip_strings(l)
        if not l.strip() or l.lstrip().startswith("//"):
            if depth == 0:
                continue
        if start is None:
            start, buf, nums = n, "", []
        nums.append(n); buf += (" " + code) if len(nums) > 1 else code
        depth += code.count("(") - code.count(")") + code.count("[") - code.count("]")
        if depth <= 0 and next_is_cont(n - 1, l):
            depth = 0
            continue
        if depth <= 0:
            yield start, nums, buf
            start, buf, depth, nums = None, "", 0, []
    if start is not None:
        yield start, nums, buf

TYPEWORDS = r"(?:int|float|bool|string|color|line|linefill|label|box|table|polyline|chart\.point|array|matrix|map)"


def undefined_names(lines):
    """Identifiers referenced but never assigned anywhere in the file.

    Added after a clean lint on a file referencing an undefined group constant
    (G_FILTERS), which is a hard compile error on TradingView.

    WIDENED after v5.0 shipped with `tfWarn` referenced and never declared —
    the previous version only inspected names prefixed G_ / i_ / eff, so an
    ordinary local that a patch deleted out from under its use sailed through a
    clean lint and failed to compile on TradingView. It now checks EVERY bare
    identifier, which requires getting three things right or it drowns in false
    positives:

      qualified names   `size.small` is one token, not a reference to `small`.
                        The whole dotted expression is removed, not just its
                        prefix.
      named arguments   `tooltip=` inside a call looks exactly like a use. Any
                        identifier followed by a single `=` is skipped.
      declarations      Pine spells these six ways — plain, `var`/`varip`,
                        typed (`float x =`), bracket-array (`box[] xs =`),
                        generic (`array<float> xs =`), tuple (`[a, b] =`),
                        function parameters, `for` and `for...in` loop vars,
                        and the field names inside a `type` block.

    Verified against every .pine in this repo that TradingView has compiled:
    zero findings on all of them.
    """
    clean = "\n".join(strip_strings(l)[0] for l in lines)
    clean = re.sub(r"#[0-9A-Fa-f]{6,8}\b", " ", clean)          # color literals

    assigned = set()
    # plain / var / varip / typed / bracket-array / generic declarations
    decl = (r"^[ \t]*(?:var(?:ip)?[ \t]+)?"
            r"(?:" + TYPEWORDS + r"(?:[ \t]*<[^>\n]*>|[ \t]*\[[ \t]*\])?[ \t]+)?"
            r"([A-Za-z_]\w*)[ \t]*(?::=|=)(?!=)")
    assigned |= set(re.findall(decl, clean, re.M))
    # a user type used as the declared type: `SessionDrawings d = ...`
    assigned |= set(re.findall(r"^[ \t]*(?:var(?:ip)?[ \t]+)?[A-Za-z_]\w*(?:[ \t]*<[^>\n]*>|[ \t]*\[[ \t]*\])?[ \t]+([A-Za-z_]\w*)[ \t]*=(?!=)", clean, re.M))
    # tuple destructuring, including request.security's [a, b] = form
    for grp in re.findall(r"\[([^\]\n]+)\][ \t]*=(?!=)", clean):
        for nm in grp.split(","):
            nm = nm.strip()
            if nm:
                assigned.add(nm.split()[-1])
    # function parameters
    for params in re.findall(r"^[ \t]*[A-Za-z_]\w*\(([^)\n]*)\)[ \t]*=>", clean, re.M):
        for prm in params.split(","):
            prm = prm.strip().split("=")[0].strip()
            if prm:
                assigned.add(prm.split()[-1])
    # for i = 0 to n   /   for [i, x] in arr   /   for x in arr
    assigned |= set(re.findall(r"^[ \t]*for[ \t]+([A-Za-z_]\w*)", clean, re.M))
    for grp in re.findall(r"^[ \t]*for[ \t]+\[([^\]\n]+)\][ \t]+in\b", clean, re.M):
        for nm in grp.split(","):
            if nm.strip():
                assigned.add(nm.strip())
    # type blocks: the type name and every field declared inside it
    for m in re.finditer(r"^type[ \t]+([A-Za-z_]\w*)[ \t]*$", clean, re.M):
        assigned.add(m.group(1))
        tail = clean[m.end():]
        for fl in tail.split("\n")[1:]:
            if not fl.startswith((" ", "\t")) or not fl.strip():
                break
            f = re.match(r"[ \t]+\S+(?:[ \t]*<[^>]*>|[ \t]*\[[ \t]*\])?[ \t]+([A-Za-z_]\w*)", fl)
            if f:
                assigned.add(f.group(1))

    # drop dotted expressions whole, then collect bare identifiers that are
    # neither call heads nor named arguments
    bare = re.sub(r"\b[A-Za-z_]\w*(?:[ \t]*\.[ \t]*[A-Za-z_]\w*)+", " ", clean)
    used = set()
    for m in re.finditer(r"\b([A-Za-z_]\w*)\b[ \t]*(\(|=(?!=))?", bare):
        if m.group(2):
            continue
        used.add(m.group(1))

    out = []
    for name in sorted(used - assigned - KEYWORDS - BARE):
        for ln, text in enumerate(lines, 1):
            if text.lstrip().startswith("//"):
                continue
            if re.search(r"\b" + re.escape(name) + r"\b", strip_strings(text)[0]):
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
    # Every declaration form Pine accepts. Missing `var polyline x = na` here
    # made the checker report a variable as "used before defined" at the exact
    # line that defines it.
    DEF = re.compile(r"^\s*(?:var(?:ip)?\s+)?"
                     r"(?:[A-Za-z_]\w*(?:\s*<[^>\n]*>|\s*\[\s*\])?\s+)?"
                     r"([A-Za-z_]\w*)\s*(?::=|=(?!=))")
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

def main(argv):
    bad = 0
    for path in argv:
        e = check(path)
        print("=== %s ===" % path)
        for n, m in e[:30]:
            print("  line %-5d %s" % (n, m))
        print("  %d issue(s)" % len(e))
        bad += len(e)
    return 1 if bad else 0


# Guarded so the module can be imported and its helpers reused — without this
# an `import lint_pine` ran the driver and called sys.exit() on the spot, which
# silently killed anything trying to test the checker.
if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
