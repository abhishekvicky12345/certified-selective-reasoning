"""extract_final_v2: the generator-answer reader, with fractions read in full.

Dated 2026-10-22. Written after the C3 extraction audit of the same day.

stage2_lib.py is NOT changed. Its extract_final (v1) produced every published
number, so it stays the record of what ran (sha256 a53fe6035bca098f..., CRLF;
the same bytes as stage2_lib.py in the public GitHub repo). Use this module
only for corrected reruns, and report the v1 numbers beside the v2 ones.
See the CORRECTIONS.md entry dated 2026-10-22.

What v2 changes, and nothing else
---------------------------------
v1's number pattern stops at "/", so "FINAL: 7/2" reads as 7 and
"FINAL: -42159089/3" as -42159089. v2 reads a number on the FINAL: line that is
followed by "/" and an unsigned number as that fraction.

Kept exactly as in v1:
- the last FINAL: line that has a number wins;
- the number grammar (_NUM) and the optional "$" after "FINAL:";
- the fallback when no FINAL: line has a number: the last number in the text.
  A "/" in running text is usually a step of the working ("1310 * 6 / 7 ="),
  not the answer, so the fallback still ignores it;
- the tags: "final_tag", "last_number_fallback", "no_number";
- to_fraction, copied verbatim, for each part of the fraction.

Guards
- A number with more than MAX_DIGITS (1,000) digits reads as None. Python 3.11+
  refuses int strings over 4,300 digits, so v1 returns None for such a number
  on 3.11+ but its exact value on 3.10 and older; v2 returns None on every
  version. Only 4 degenerate Flash-Lite GSM-Hard outputs have numbers this long
  (24,414 to 32,581 digits), and v1 also reads them as None on Python 3.11+.
- "a/0" reads as None.
- "a/b/c" (a date, say) is not read as a fraction; v2 keeps v1's reading "a".
- "8000/G" (a letter after the slash) keeps v1's reading 8000.

Effect on the 18 frozen generator files (checked 2026-10-22, see test_v2.py):
v2 differs from v1 on exactly the 107 rows the C3 audit flagged, and on each of
them it gives the C3 careful reading. 67 rows go wrong -> right, none right -> wrong.

No z3 import: scoring with this module does not need z3-solver.
"""
import re
from fractions import Fraction

VERSION = "extract_final_v2 2026-10-22"
MAX_DIGITS = 1000

# ---- Copied verbatim from stage2_lib.py (v1, as run) ------------------------
_NUM = r"-?(?:\d[\d,]*(?:\.\d+)?|\.\d+)(?:[eE][+-]?\d+)?"
_FINAL_RE = re.compile(r"FINAL:\s*\$?\s*(" + _NUM + r")", re.I)
_ANYNUM_RE = re.compile("(" + _NUM + ")")


def to_fraction(text):
    """'1,234.50' -> Fraction(2469, 2).  Returns None if it is not a number."""
    if text is None:
        return None
    t = str(text).strip().replace(",", "").replace("$", "").rstrip(".")
    if not t:
        return None
    try:
        return Fraction(t)
    except (ValueError, ZeroDivisionError):
        try:
            return Fraction(float(t))
        except (ValueError, OverflowError):
            return None
# ---- End of the verbatim copy -----------------------------------------------

# New in v2: an optional "/ denominator" straight after the FINAL: number.
# The denominator is _NUM without its sign. The lookahead stops a partial
# denominator: without it the regex could backtrack "1/12/3" to "1/1".
_DEN = r"(?:\d[\d,]*(?:\.\d+)?|\.\d+)(?:[eE][+-]?\d+)?"
_DEN_END = r"(?![ \t]*/|\d|[.,]\d|[eE][+-]?\d)"
_FINAL_RE_V2 = re.compile(
    r"FINAL:\s*\$?\s*(" + _NUM + r")"                         # v1's pattern, unchanged
    r"(?:[ \t]*/[ \t]*(" + _DEN + r")" + _DEN_END + r")?",    # new: "/ denominator"
    re.I)


def _read_number(token):
    """v1's to_fraction, but None for a number over MAX_DIGITS digits."""
    if token is None:
        return None
    if sum(ch.isdigit() for ch in token) > MAX_DIGITS:
        return None
    return to_fraction(token)


def extract_final_v2(text):
    """The generator's answer. Last FINAL: wins; fall back to the last number.

    Same contract as stage2_lib.extract_final: returns (Fraction or None, tag).
    """
    hits = _FINAL_RE_V2.findall(text or "")
    if hits:
        num_s, den_s = hits[-1]
        num = _read_number(num_s)
        if not den_s:
            return num, "final_tag"
        den = _read_number(den_s)
        if num is None or den is None or den == 0:
            return None, "final_tag"
        return num / den, "final_tag"
    nums = _ANYNUM_RE.findall(text or "")
    if nums:
        return _read_number(nums[-1]), "last_number_fallback"
    return None, "no_number"
