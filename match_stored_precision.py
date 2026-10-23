"""answers_match_stored: does an answer match the gold at the precision the gold was stored with?

Dated 2026-10-23. Decided that day: GSM-Hard's matching-rule sensitivity check uses this
match instead of exact rational equality. The primary scorer does not change: it stays
stage2_lib.answers_match (exact, else a relative tolerance of 1e-6), which produced every
published number. See the CORRECTIONS.md entry dated 2026-10-23.

Why
---
GSM-Hard's golds are program outputs stored as floats rounded to 10 decimal places:
no stored gold has more than 10 decimals, 111 have exactly 10 (e.g. 1386.6666666667,
2.0107e-06), and large ones carry float noise (1285665.9000000004). Against such golds:
- the 1e-6 relative tolerance is too loose at large magnitudes (82085208 matches
  82085198) and too tight below 5e-5 (5/2486737 fails against 2.0107e-06);
- exact rational equality counts the gold's own storage noise as error
  (1285665.9 fails against 1285665.9000000004, 10/3 against 3.3333333333).

The rule
--------
    |pred - gold| <= ABS_TOL + REL_TOL * |gold|
ABS_TOL = 5e-11 is half a unit in the 10th decimal place: the rounding of the stored gold.
REL_TOL = 1e-14 covers float noise in the stored gold. On the 18 frozen generator files
(checked 2026-10-23, both readers):
- float noise needs at most 3.4e-16 (gsm_hard/0292: 852828.6363636364 vs 852828.6363636367);
- the first answer that differs from its gold in a stored decimal would need 9.1e-13
  (Flash-Lite gsm_hard/1184: 179.9999262334855 vs 179.9999262337).
Any REL_TOL between the two gives the same verdict on every row; 1e-14 sits about 30x
above the first and 90x below the second. (1e-12, used in the 22 Oct scorer check, sat
above the second: it gave the same certified-wrong counts but counted 1184 as right.)
On golds that are integers or short exact decimals (SVAMP, GSM8K, GSM-Symbolic), this
match agrees with answers_match on every row.

Exact rationals throughout (fractions.Fraction); no floats. No z3 import.
"""
from fractions import Fraction

VERSION = "match_stored_precision 2026-10-23"
ABS_TOL = Fraction(5, 10**11)
REL_TOL = Fraction(1, 10**14)


def answers_match_stored(pred, gold, abs_tol=ABS_TOL, rel_tol=REL_TOL):
    """True if pred agrees with gold to the gold's stored precision.

    pred and gold are Fractions (as from extract_final_v2 and stage2_lib.to_fraction),
    or None, which never matches.
    """
    if pred is None or gold is None:
        return False
    return abs(pred - gold) <= abs_tol + rel_tol * abs(gold)


def _self_test():
    """Cases from the 22 Oct scorer check. Raises AssertionError on any failure."""
    F = Fraction
    cases = [
        (F(5, 2486737), F("2.0107e-06"), True),          # tiny gold: right at its 10-dp precision
        (F(4160, 3), F("1386.6666666667"), True),        # repeating fraction vs 10-dp gold
        (F(10, 3), F("3.3333333333"), True),
        (F("1285665.9"), F("1285665.9000000004"), True),  # float noise in the gold
        (F("3244047.1"), F("3244047.0999999996"), True),
        (F("1386.6666666666665"), F("1386.6666666667"), True),
        (F("852828.6363636364"), F("852828.6363636367"), True),   # the largest float noise seen
        (F("179.9999262334855"), F("179.9999262337"), False),    # differs in the 10th decimal (1184)
        (F(82085208), F("82085198.0"), False),            # off by 10: the 1e-6 tolerance accepts it
        (F("782577.75"), F("782577.0"), False),           # off by 0.75 (item 1150)
        (F("794329.8"), F("794330.0"), False),            # off by 0.2 (item 1111)
        (F("3.33"), F("3.3333333333"), False),            # a rounded answer is not a match
        (F(51), F("51.0"), True),
        (F(0), F(0), True),
        (F(1, 10**11), F(0), True),
        (F(1, 10**9), F(0), False),
        (None, F(1), False),
        (F(1), None, False),
    ]
    for pred, gold, want in cases:
        got = answers_match_stored(pred, gold)
        assert got == want, (pred, gold, got, want)
    return len(cases)


if __name__ == "__main__":
    print(VERSION, "| self-test cases passed:", _self_test())
