"""Chemical reaction schemes: parse, balance and lay out.

A reaction is a plain JSON-able dict, so it can ride on the placed group
(``rxn_data``) through undo snapshots and SVG files and be re-opened in
the Reaction builder later::

    {"reactants": [species, …], "products": [species, …],
     "arrow": "forward", "above": "H2SO4", "below": "Δ, 2 h",
     "style": "skeletal", "states": True, "labels": False, "unit": 40.0}

A species is one of::

    {"coef": "2", "name": "water"}                 # library molecule
    {"coef": "1", "formula": "Fe2O3"}              # formula or free text
    {"coef": "1", "atoms": [...], "bonds": [...]}  # hand-built molecule

plus an optional ``"state"`` (s/l/g/aq) and a per-species ``"mode"``
overriding the reaction's drawing style. Coefficients are strings so a
fraction ("1/2") survives JSON exactly.

Structural species are drawn through `molrepr.depict` at ONE bond length
(``unit`` px), so every molecule of a scheme matches; formulas are typeset
with sub/superscripts. Balancing counts atoms and charge; `auto_balance`
finds the smallest whole-number coefficients by exact (Fraction) null-space
elimination.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import copy
import math
import re
from collections import Counter
from fractions import Fraction
from functools import lru_cache

from . import molecules, molrepr

#: Arrow kinds, in menu order.
ARROWS = ["forward", "equilibrium", "reversible", "resonance", "retro",
          "none"]
ARROW_LABELS = {"forward": "→  Reaction", "equilibrium": "⇌  Equilibrium",
                "reversible": "⇄  Reversible", "resonance": "↔  Resonance",
                "retro": "⇒  Retrosynthesis", "none": "↛  No reaction"}
#: How the species are drawn (the molrepr modes a scheme uses).
STYLES = ["skeletal", "structural", "lewis", "condensed", "formula", "3d"]
#: State symbols.
STATES = ["", "s", "l", "g", "aq"]

#: Arrow spellings recognised in a typed equation — longest / most
#: specific first, so "<=>" is not read as "=>" nor "-->" as "->".
_ARROW_TOKENS = [("-/->", "none"), ("↛", "none"), ("<=>", "equilibrium"),
                 ("⇌", "equilibrium"), ("<->", "resonance"),
                 ("↔", "resonance"), ("⇄", "reversible"),
                 ("-->", "forward"), ("->", "forward"), ("→", "forward"),
                 ("=>", "retro"), ("⇒", "retro"), ("=", "forward")]
_ARROW_TEXT = {"forward": "->", "equilibrium": "<=>", "reversible": "⇄",
               "resonance": "<->", "retro": "=>", "none": "-/->"}

_INK = "#1a1a1a"
ELEMENTS = frozenset(
    "H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe "
    "Co Ni Cu Zn Ga Ge As Se Br Kr Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In "
    "Sn Sb Te I Xe Cs Ba La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf "
    "Ta W Re Os Ir Pt Au Hg Tl Pb Bi Po At Rn Fr Ra Ac Th Pa U Np Pu Am D"
    .split())
#: Common shorthand that the formula index cannot disambiguate.
_ALIASES = {"c2h5oh": "ethanol", "etoh": "ethanol", "meoh": "methanol",
            "acoh": "acetic_acid", "hcho": "formaldehyde"}

_SUB_IN = str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")
_SUP_IN = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻", "0123456789+-")
_SUP_OUT = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")
_SUB_OUT = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")
_VULGAR = {Fraction(1, 2): "½", Fraction(1, 3): "⅓", Fraction(2, 3): "⅔",
           Fraction(1, 4): "¼", Fraction(3, 4): "¾"}
_VULGAR_IN = {v: f"{k.numerator}/{k.denominator}" for k, v in _VULGAR.items()}


def new_reaction():
    return {"reactants": [], "products": [], "arrow": "forward",
            "above": "", "below": "", "style": "skeletal", "states": True,
            "labels": False}


def normalise(rxn):
    """A deep copy of *rxn* with every key present and sane types — the
    one door for dicts from the AI, MCP clients and old files."""
    out = new_reaction()
    for key in ("arrow", "above", "below", "style", "states", "labels",
                "unit"):
        if key in (rxn or {}):
            out[key] = copy.deepcopy(rxn[key])
    if out["arrow"] not in ARROWS:
        out["arrow"] = "forward"
    if out["style"] not in STYLES:
        out["style"] = "skeletal"
    out["above"] = str(out.get("above") or "")
    out["below"] = str(out.get("below") or "")
    for side in ("reactants", "products"):
        out[side] = []
        for sp in (rxn or {}).get(side) or []:
            sp = copy.deepcopy(dict(sp))
            sp["coef"] = str(coef_value(sp))
            if sp.get("state") not in STATES:
                sp["state"] = ""
            if sp.get("mode") not in STYLES:
                sp.pop("mode", None)
            out[side].append(sp)
    return out


# ------------------------------------------------------------- formulas
def split_charge(text):
    """("SO4", -2) from "SO4^2-", "SO₄²⁻" or "SO4--"; a bare trailing sign
    is ±1 and any digits before it stay in the formula (NH4+ is NH₄⁺)."""
    t = str(text).strip().replace("−", "-")
    m = re.search(r"([⁰¹²³⁴⁵⁶⁷⁸⁹]*)([⁺⁻]+)$", t)
    if m:
        digits = m.group(1).translate(_SUP_IN)
        signs = m.group(2).translate(_SUP_IN)
    else:
        m = re.search(r"\^\s*(\d*)\s*([+-]+)$", t) \
            or re.search(r"()([+-]+)$", t)
        if not m:
            return t, 0
        digits, signs = m.group(1), m.group(2)
    core = t[:m.start()].strip()
    if digits:
        return core, int(digits) * (1 if signs[0] == "+" else -1)
    return core, signs.count("+") - signs.count("-")


_TOKEN = re.compile(r"[A-Z][a-z]?|\d+|[()\[\]{}]")


def _parse_group(s):
    tokens = _TOKEN.findall(s)
    if "".join(tokens) != s:
        raise ValueError(f"can't read {s!r} as a formula")
    stack = [Counter()]
    i = 0

    def count():
        nonlocal i
        if i < len(tokens) and tokens[i].isdigit():
            i += 1
            return int(tokens[i - 1])
        return 1
    while i < len(tokens):
        tok = tokens[i]
        i += 1
        if tok in "([{":
            stack.append(Counter())
        elif tok in ")]}":
            if len(stack) == 1:
                raise ValueError("unbalanced bracket")
            grp = stack.pop()
            n = count()
            for el, c in grp.items():
                stack[-1][el] += c * n
        elif tok.isdigit():
            raise ValueError("a number with no element")
        elif tok not in ELEMENTS:
            raise ValueError(f"unknown element {tok}")
        else:
            stack[-1][tok] += count()
    if len(stack) != 1:
        raise ValueError("unbalanced bracket")
    return stack[0]


def parse_formula(text):
    """({element: count}, charge) for a formula — brackets, hydrates
    (CuSO4·5H2O), unicode sub/superscripts and ionic charges (NH4+,
    SO4^2-, Fe³⁺, e-). Raises ValueError if it isn't a formula."""
    core, q = split_charge(text)
    core = core.translate(_SUB_IN).replace(" ", "")
    if core == "e":                                   # an electron
        return {}, q or -1
    total = Counter()
    for part in re.split(r"[·•∙*.]", core):
        if not part:
            raise ValueError("empty formula")
        m = re.match(r"(\d+)(\D.*)$", part)
        mult, body = (int(m.group(1)), m.group(2)) if m else (1, part)
        for el, c in _parse_group(body).items():
            total[el] += c * mult
    if not total:
        raise ValueError("empty formula")
    return dict(total), q


def pretty_formula(text):
    """Typeset a formula: H2SO4 → H₂SO₄, SO4^2- → SO₄²⁻, CuSO4.5H2O →
    CuSO₄·5H₂O. Text that is not a formula comes back unchanged."""
    try:
        parse_formula(text)
    except ValueError:
        return str(text)
    core, q = split_charge(text)
    out = []
    for part in re.split(r"([·•∙*.])", core.translate(_SUB_IN)):
        if part in ("·", "•", "∙", "*", "."):
            out.append("·")
            continue
        m = re.match(r"(\d+)(\D.*)$", part)
        lead, body = (m.group(1), m.group(2)) if m else ("", part)
        out.append(lead + re.sub(r"(?<=[A-Za-z)\]}])(\d+)",
                                 lambda d: d.group(1).translate(_SUB_OUT),
                                 body))
    s = "".join(out)
    if q:
        s += (str(abs(q)) if abs(q) > 1 else "").translate(_SUP_OUT)
        s += "⁺" if q > 0 else "⁻"
    return s


def pretty_text(text):
    """Conditions text: typeset each formula-looking word (H2SO4, 2 h
    stays), and hv → hν."""
    def fix(word):
        if word.lower() == "hv":
            return "hν"
        if re.search(r"[A-Z]", word) and re.search(r"\d", word):
            return pretty_formula(word)
        return word
    return re.sub(r"[^\s,;/]+", lambda m: fix(m.group(0)), str(text))


# -------------------------------------------------------------- species
def coef_value(sp):
    raw = str(sp.get("coef", 1) if isinstance(sp, dict) else sp).strip()
    raw = _VULGAR_IN.get(raw, raw) or "1"
    try:
        v = Fraction(raw).limit_denominator(100)
    except (ValueError, ZeroDivisionError):
        return Fraction(1)
    return v if v > 0 else Fraction(1)


def coef_text(sp):
    """The coefficient as printed: "" for 1, "2", "½", "3/2"."""
    v = coef_value(sp)
    if v == 1:
        return ""
    if v.denominator == 1:
        return str(v.numerator)
    return _VULGAR.get(v, f"{v.numerator}/{v.denominator}")


def species_atoms(sp):
    """(atoms, bonds) of a structural species, else (None, None)."""
    if sp.get("atoms"):
        return sp["atoms"], sp.get("bonds") or []
    name = sp.get("name")
    if name and name in molecules._MODELS and not molecules.is_crystal(name):
        atoms, bonds = molecules.model_data(name)[:2]
        return atoms, bonds
    return None, None


def composition(sp):
    """({element: count}, charge) of a species, or None if unknown."""
    atoms, _b = species_atoms(sp)
    if atoms is not None:
        return dict(Counter(a[0] for a in atoms)), 0
    try:
        return parse_formula(sp.get("formula") or "")
    except ValueError:
        return None


def species_text(sp):
    """How a species reads in lists and captions."""
    if sp.get("atoms"):
        return molrepr.molecular_formula(sp["atoms"])
    if sp.get("name"):
        return molecules.LABELS.get(sp["name"], sp["name"])
    return pretty_formula(sp.get("formula") or "")


def _norm(text):
    return (str(text).translate(_SUB_IN).replace(" ", "").replace("=", "")
            .replace("≡", ""))


@lru_cache(maxsize=1)
def _library():
    """(key, element counts, condensed formula) for every library
    molecule — the index a typed formula is matched against."""
    out = []
    for title, names in molecules.CATEGORIES:
        if title == "Polymers":
            continue
        for key in names:
            if key not in molecules._MODELS or molecules.is_crystal(key):
                continue
            try:
                atoms, bonds = molecules.model_data(key)[:2]
            except Exception:                     # pragma: no cover
                continue
            counts = frozenset(Counter(a[0] for a in atoms).items())
            out.append((key, counts,
                        _norm(molrepr.condensed_formula(atoms, bonds))))
    return tuple(out)


def resolve_species(text):
    """A species dict for typed *text*: a library molecule when the name,
    condensed formula or (unambiguous) molecular formula matches one, else
    a formula / free-text species. None for empty text."""
    t = str(text).strip()
    if not t:
        return None
    key = _ALIASES.get(t.lower()) or molecules.resolve_name(t)
    if key and key in molecules._MODELS and not molecules.is_crystal(key):
        return {"name": key}
    try:                               # CH2=CH2 is a formula too
        counts, q = parse_formula(t.replace("=", "").replace("≡", ""))
    except ValueError:
        return {"formula": t}
    if q == 0:
        lib = _library()
        norm = _norm(t)
        for key, _c, cond in lib:
            if cond == norm:
                return {"name": key}
        hits = [key for key, c, _s in lib if c == frozenset(counts.items())]
        if len(hits) == 1:
            return {"name": hits[0]}
    return {"formula": t}


def _token(sp):
    """A species as equation text that `resolve_species` maps back."""
    name = sp.get("name")
    atoms, bonds = species_atoms(sp)
    if name and atoms is not None:
        cond = molrepr.condensed_formula(atoms, bonds).translate(_SUB_IN)
        return cond if resolve_species(cond) == {"name": name} else name
    if atoms is not None:
        return molrepr.molecular_formula(atoms).translate(_SUB_IN)
    return str(sp.get("formula") or "")


# ------------------------------------------------------------ equations
_PLUS = re.compile(r"\s+\+\s+|(?<=[\w)\]])\+(?=[\w(\[])")
_TERM = re.compile(r"^(\d+/\d+|\d*\.\d+|\d+|[½⅓⅔¼¾])?\s*(.+?)\s*"
                   r"(?:\((s|l|g|aq)\))?$")


def _parse_side(side):
    out = []
    for term in _PLUS.split(side.strip()):
        term = term.strip()
        if not term:
            continue
        m = _TERM.match(term)
        coef, body, state = m.group(1), m.group(2), m.group(3) or ""
        if coef and body[:1] in "-,'":            # "1-propanol" is a name
            coef, body = None, term
        sp = resolve_species(body) or {"formula": body}
        sp["coef"] = str(coef_value({"coef": coef or "1"}))
        sp["state"] = state
        out.append(sp)
    return out


def parse_equation(text):
    """Read "CH4 + 2 O2 -> CO2 + 2 H2O(g)" into a reaction dict. Arrows:
    -> → = (reaction), <=> ⇌ (equilibrium), ⇄, <-> ↔ (resonance),
    => ⇒ (retrosynthesis), -/-> ↛ (no reaction). Conditions go in
    brackets straight after the arrow: "A ->[H2SO4][Δ] B"."""
    s = str(text).strip()
    for tok, kind in _ARROW_TOKENS:
        k = s.find(tok)
        if k >= 0:
            break
    else:
        raise ValueError("No reaction arrow — write ->, <=>, ⇌, => …")
    left, right = s[:k], s[k + len(tok):]
    rxn = new_reaction()
    rxn["arrow"] = kind
    m = re.match(r"\s*\[([^\]]*)\](?:\s*\[([^\]]*)\])?", right)
    if m:
        rxn["above"] = m.group(1).strip()
        rxn["below"] = (m.group(2) or "").strip()
        right = right[m.end():]
    rxn["reactants"] = _parse_side(left)
    rxn["products"] = _parse_side(right)
    return rxn


def to_equation(rxn):
    """The reaction as editable equation text (inverse of parse_equation)."""
    def term(sp):
        c = coef_value(sp)
        state = f"({sp['state']})" if sp.get("state") else ""
        return ("" if c == 1 else f"{c} ") + _token(sp) + state

    def side(key):
        return " + ".join(term(sp) for sp in rxn.get(key) or [])
    cond = ""
    if rxn.get("above") or rxn.get("below"):
        cond = f"[{rxn.get('above', '')}]"
        if rxn.get("below"):
            cond += f"[{rxn['below']}]"
    arrow = _ARROW_TEXT.get(rxn.get("arrow"), "->")
    return f"{side('reactants')} {arrow}{cond} {side('products')}".strip()


# ------------------------------------------------------------ balancing
def balance_report(rxn):
    """{"balanced", "diffs": {element|"charge": (left, right)},
    "unknown": [species whose composition can't be counted]}."""
    totals, charges, unknown = [Counter(), Counter()], [Fraction(0)] * 2, []
    for s, key in enumerate(("reactants", "products")):
        for sp in rxn.get(key) or []:
            comp = composition(sp)
            if comp is None:
                unknown.append(species_text(sp))
                continue
            c = coef_value(sp)
            for el, n in comp[0].items():
                totals[s][el] += c * n
            charges[s] += c * comp[1]
    left, right = totals
    diffs = {el: (left[el], right[el]) for el in sorted(set(left) | set(right))
             if left[el] != right[el]}
    if charges[0] != charges[1]:
        diffs["charge"] = tuple(charges)
    ok = not diffs and not unknown and bool(rxn.get("reactants")) \
        and bool(rxn.get("products"))
    return {"balanced": ok, "diffs": diffs, "unknown": unknown}


def balance_text(report):
    """One-line human summary of a `balance_report`."""
    if report["balanced"]:
        return "Balanced ✓"
    parts = []
    if report["unknown"]:
        parts.append("can't count " + ", ".join(report["unknown"]))
    for el, (l, r) in report["diffs"].items():
        parts.append(f"{el} {l} → {r}")
    return "Not balanced — " + "; ".join(parts) if parts \
        else "Add reactants and products."


def auto_balance(rxn):
    """Set the smallest whole-number coefficients that conserve every
    element and the charge. Returns None on success, else the reason."""
    reac, prod = rxn.get("reactants") or [], rxn.get("products") or []
    if not reac or not prod:
        return "Add reactants and products first."
    species = reac + prod
    comps = [composition(sp) for sp in species]
    if any(c is None for c in comps):
        return "Some species have no formula to count."
    sign = [1] * len(reac) + [-1] * len(prod)
    rows = [[Fraction(c[0].get(el, 0) * s) for c, s in zip(comps, sign)]
            for el in sorted({el for c in comps for el in c[0]})]
    if any(c[1] for c in comps):
        rows.append([Fraction(c[1] * s) for c, s in zip(comps, sign)])
    m = len(species)
    pivots, r = [], 0
    for col in range(m):                     # reduced row-echelon form
        piv = next((i for i in range(r, len(rows)) if rows[i][col]), None)
        if piv is None:
            continue
        rows[r], rows[piv] = rows[piv], rows[r]
        pv = rows[r][col]
        rows[r] = [x / pv for x in rows[r]]
        for i in range(len(rows)):
            if i != r and rows[i][col]:
                f = rows[i][col]
                rows[i] = [a - f * b for a, b in zip(rows[i], rows[r])]
        pivots.append(col)
        r += 1
        if r == len(rows):
            break
    free = [c for c in range(m) if c not in pivots]
    if not free:
        return "No way to balance these species — check the formulas."
    if len(free) > 1:
        return ("More than one independent reaction here — set some "
                "coefficients by hand.")
    x = [Fraction(0)] * m
    x[free[0]] = Fraction(1)
    for i, col in enumerate(pivots):
        x[col] = -rows[i][free[0]]
    if all(v < 0 for v in x):
        x = [-v for v in x]
    if any(v <= 0 for v in x):
        return "No positive solution — is every species on the right side?"
    lcm = 1
    for v in x:
        lcm = lcm * v.denominator // math.gcd(lcm, v.denominator)
    ints = [int(v * lcm) for v in x]
    g = 0
    for v in ints:
        g = math.gcd(g, v)
    for sp, v in zip(species, ints):
        sp["coef"] = str(v // g)
    return None


# --------------------------------------------------------------- layout
def arrow_specs(kind, x0, x1, y, unit):
    """Line/polygon specs for a reaction arrow from x0 to x1 at height y."""
    lw = max(1.2, unit * 0.045)
    hl, hw, d = unit * 0.32, unit * 0.12, unit * 0.09
    ink = {"stroke": _INK, "width": lw}
    head = {"shape": "polygon", "stroke": _INK, "width": 1, "fill": _INK}

    def seg(xa, ya, xb, yb):
        return dict(ink, shape="line", x1=xa, y1=ya, x2=xb, y2=yb)

    def tip(x, yy, direction, half=None):
        """Filled head at (x, yy) pointing ±x; *half* = -1/+1 keeps only
        the upper/lower barb (a harpoon)."""
        back = x - direction * hl
        lo = yy - hw if half in (None, -1) else yy
        hi = yy + hw if half in (None, 1) else yy
        return dict(head, points=[[x, yy], [back, lo], [back, hi]])
    if kind == "equilibrium":
        return [seg(x0, y - d, x1 - 1, y - d), tip(x1, y - d, 1, -1),
                seg(x0 + 1, y + d, x1, y + d), tip(x0, y + d, -1, 1)]
    if kind == "reversible":
        return [seg(x0, y - 2 * d, x1 - hl, y - 2 * d), tip(x1, y - 2 * d, 1),
                seg(x0 + hl, y + 2 * d, x1, y + 2 * d),
                tip(x0, y + 2 * d, -1)]
    if kind == "resonance":
        return [seg(x0 + hl, y, x1 - hl, y), tip(x1, y, 1), tip(x0, y, -1)]
    if kind == "retro":
        k = hw * 1.9
        return [seg(x0, y - d, x1 - hl * 0.55, y - d),
                seg(x0, y + d, x1 - hl * 0.55, y + d),
                seg(x1 - hl, y - k, x1, y), seg(x1, y, x1 - hl, y + k)]
    out = [seg(x0, y, x1 - hl, y), tip(x1, y, 1)]
    if kind == "none":
        cx, c = (x0 + x1 - hl) / 2, hw * 1.4
        out += [seg(cx - c, y - c, cx + c, y + c),
                seg(cx - c, y + c, cx + c, y - c)]
    return out


def _caption(sp):
    name = sp.get("name")
    if not name:
        return ""
    return re.sub(r"\s*\(.*\)$", "", molecules.LABELS.get(name, name))


def _species_part(sp, style, unit, fs, small, labels):
    mode = sp.get("mode") or style
    atoms, bonds = species_atoms(sp)
    if atoms is None or mode in molrepr.TEXT_MODES:
        if atoms is None:
            text = pretty_formula(sp.get("formula") or "?")
        elif mode == "condensed":
            text = molrepr.condensed_formula(atoms, bonds)
        else:
            text = molrepr.molecular_formula(atoms)
        specs, w, h = molrepr.normalize([molrepr.text_spec(text, 0, 0, fs)])
    elif mode == "3d":
        box = unit * (1.2 + 0.7 * math.sqrt(len(atoms)))
        specs, w, h = molrepr.normalize(molecules.specs_from_atoms(
            atoms, bonds, box, box, bond=molecules.DEFAULT_BOND))
    else:
        specs, w, h = molrepr.depict(mode, atoms, bonds, unit)
    cy = h / 2.0
    cap = _caption(sp) if labels else ""
    if cap:
        cw, ch = molrepr.text_size(cap, small)
        if cw > w:
            molrepr.shift_specs(specs, (cw - w) / 2.0, 0)
            w = cw
        top = h + unit * 0.3
        specs.append(molrepr.text_spec(cap, w / 2.0, top + ch / 2.0, small,
                                       "#444444"))
        h = top + ch
    return specs, w, h, cy


def _arrow_part(rxn, unit, small):
    above = pretty_text(rxn.get("above") or "").strip()
    below = pretty_text(rxn.get("below") or "").strip()
    aw, ah = molrepr.text_size(above, small) if above else (0.0, 0.0)
    bw, bh = molrepr.text_size(below, small) if below else (0.0, 0.0)
    length = max(unit * 2.4, aw + unit * 0.8, bw + unit * 0.8)
    specs = arrow_specs(rxn.get("arrow", "forward"), 0.0, length, 0.0, unit)
    _x0, y0, _x1, y1 = molrepr.specs_bounds(specs)
    pad = unit * 0.16
    if above:
        specs.append(molrepr.text_spec(above, length / 2, y0 - pad - ah / 2,
                                       small))
    if below:
        specs.append(molrepr.text_spec(below, length / 2, y1 + pad + bh / 2,
                                       small))
    x0, y0, x1, y1 = molrepr.specs_bounds(specs)
    molrepr.shift_specs(specs, -x0, -y0)
    return specs, x1 - x0, y1 - y0, -y0


def reaction_specs(rxn, unit=40.0):
    """Shape specs for the whole scheme laid out left to right on one
    axis (species, "+", coefficients, state symbols, the arrow with its
    conditions). Returns (specs, width, height), top-left at (0, 0)."""
    style = rxn.get("style") or "skeletal"
    fs = molrepr.pt_for_height(unit * 0.62)
    small = molrepr.pt_for_height(unit * 0.46)
    gap = unit * 0.32

    def text(txt, pt, before):
        w, h = molrepr.text_size(txt, pt)
        return [molrepr.text_spec(txt, w / 2, h / 2, pt)], w, h, h / 2, before
    parts = []
    for s, key in enumerate(("reactants", "products")):
        for k, sp in enumerate(rxn.get(key) or []):
            if k:
                parts.append(text("+", fs, gap))
            before = gap
            c = coef_text(sp)
            if c:
                parts.append(text(c, fs, gap))
                before = unit * 0.1
            parts.append(_species_part(sp, style, unit, fs, small,
                                       rxn.get("labels")) + (before,))
            if rxn.get("states", True) and sp.get("state"):
                parts.append(text(f"({sp['state']})", small, unit * 0.05))
        if s == 0:
            parts.append(_arrow_part(rxn, unit, small) + (gap * 1.3,))
    top = max(p[3] for p in parts)
    bottom = max(p[2] - p[3] for p in parts)
    out, x = [], 0.0
    for i, (specs, w, _h, cy, before) in enumerate(parts):
        if i:
            x += before
        out += molrepr.shift_specs(specs, x, top - cy)
        x += w
    return out, x, top + bottom
