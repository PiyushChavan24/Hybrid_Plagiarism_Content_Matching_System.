"""
M5 — fusion.py
HPCM Plagiarism Detection System
----------------------------------
Fuse three similarity scores into a single composite score:
  C_final = 0.25 * S_lex + 0.50 * S_sem + 0.25 * S_sty
"""

import logging

# ---------------------------------------------------------------------------
# Logger
# ---------------------------------------------------------------------------
logger = logging.getLogger("hpcm.fusion")

# ---------------------------------------------------------------------------
# Weights (must sum to 1.0)
# ---------------------------------------------------------------------------
W_LEX = 0.25
W_SEM = 0.50
W_STY = 0.25


def compute_fusion(s_lex: float, s_sem: float, s_sty: float) -> dict:
    """
    Weighted fusion of the three similarity layers.

    Parameters
    ----------
    s_lex : float — lexical similarity from M2 [0.0, 1.0]
    s_sem : float — semantic similarity from M3 [0.0, 1.0]
    s_sty : float — stylometric similarity from M4 [0.0, 1.0]

    Returns
    -------
    dict with keys:
        c_final     — float, composite score [0.0, 1.0]
        weights     — dict, the weights used
        components  — dict, individual weighted contributions
    """
    # Clamp inputs to [0, 1] for safety
    s_lex = max(0.0, min(1.0, s_lex))
    s_sem = max(0.0, min(1.0, s_sem))
    s_sty = max(0.0, min(1.0, s_sty))

    lex_contrib = W_LEX * s_lex
    sem_contrib = W_SEM * s_sem
    sty_contrib = W_STY * s_sty

    c_final = lex_contrib + sem_contrib + sty_contrib

    result = {
        "c_final": round(c_final, 6),
        "weights": {
            "w_lex": W_LEX,
            "w_sem": W_SEM,
            "w_sty": W_STY,
        },
        "components": {
            "lex_contribution": round(lex_contrib, 6),
            "sem_contribution": round(sem_contrib, 6),
            "sty_contribution": round(sty_contrib, 6),
        },
    }

    logger.debug(
        "Fusion: C_final=%.4f (lex=%.4f×%.2f + sem=%.4f×%.2f + sty=%.4f×%.2f)",
        c_final, s_lex, W_LEX, s_sem, W_SEM, s_sty, W_STY,
    )
    return result


# ========================== TEST BLOCK ====================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    print("=" * 65)
    print("HPCM M5 — Fusion Module Test")
    print("=" * 65)

    test_cases = [
        # (label, s_lex, s_sem, s_sty, expected_c_final)
        ("All zeros",      0.0, 0.0, 0.0, 0.0),
        ("All ones",       1.0, 1.0, 1.0, 1.0),
        ("Only semantic",  0.0, 1.0, 0.0, 0.50),
        ("Only lexical",   1.0, 0.0, 0.0, 0.25),
        ("Only stylometric", 0.0, 0.0, 1.0, 0.25),
        ("Typical high",   0.75, 0.85, 0.80, 0.25*0.75 + 0.50*0.85 + 0.25*0.80),
        ("Typical medium", 0.40, 0.60, 0.55, 0.25*0.40 + 0.50*0.60 + 0.25*0.55),
        ("Typical low",    0.10, 0.15, 0.20, 0.25*0.10 + 0.50*0.15 + 0.25*0.20),
        ("Clamped above",  1.5, 0.5, 0.5,  0.25*1.0 + 0.50*0.5 + 0.25*0.5),
        ("Clamped below", -0.2, 0.5, 0.5,  0.25*0.0 + 0.50*0.5 + 0.25*0.5),
    ]

    all_passed = True
    for label, s_lex, s_sem, s_sty, expected in test_cases:
        result = compute_fusion(s_lex, s_sem, s_sty)
        c = result["c_final"]
        expected_r = round(expected, 6)
        match = abs(c - expected_r) < 1e-5
        status = "[OK]" if match else "[FAIL]"

        if not match:
            all_passed = False

        print(f"\n--- {label} ---")
        print(f"  Input       : S_lex={s_lex}  S_sem={s_sem}  S_sty={s_sty}")
        print(f"  C_final     : {c}")
        print(f"  Expected    : {expected_r}")
        print(f"  Components  : {result['components']}")
        print(f"  {status}")

    print("\n" + "=" * 65)
    if all_passed:
        print("M5 fusion.py — ALL CHECKS PASSED")
    else:
        print("M5 fusion.py — SOME CHECKS FAILED (see above)")
    print("=" * 65)