"""
M7 — risk.py
HPCM Plagiarism Detection System
----------------------------------
Risk classification based on C_final and T_cal from M5/M6.

  HIGH   — C_final >= 0.80
  MEDIUM — C_final >= T_cal (and < 0.80)
  LOW    — C_final <  T_cal
"""

import logging

# ---------------------------------------------------------------------------
# Logger
# ---------------------------------------------------------------------------
logger = logging.getLogger("hpcm.risk")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
HIGH_THRESHOLD = 0.80


def classify_risk(c_final: float, t_cal: float) -> dict:
    """
    Classify plagiarism risk level.

    Parameters
    ----------
    c_final : float — composite score from M5 [0.0, 1.0]
    t_cal   : float — calibrated threshold from M6

    Returns
    -------
    dict with keys:
        risk_level   — str, "HIGH" | "MEDIUM" | "LOW"
        c_final      — float
        t_cal        — float
        high_cutoff  — float (0.80)
        confidence   — str, human-readable explanation
    """
    if c_final >= HIGH_THRESHOLD:
        risk_level = "HIGH"
        confidence = (
            f"Score {c_final:.2f} exceeds hard ceiling {HIGH_THRESHOLD}. "
            f"Strong evidence of plagiarism."
        )
    elif c_final >= t_cal:
        risk_level = "MEDIUM"
        confidence = (
            f"Score {c_final:.2f} exceeds calibrated threshold {t_cal:.2f}. "
            f"Moderate evidence — manual review recommended."
        )
    else:
        risk_level = "LOW"
        confidence = (
            f"Score {c_final:.2f} is below calibrated threshold {t_cal:.2f}. "
            f"Low likelihood of plagiarism."
        )

    result = {
        "risk_level": risk_level,
        "c_final": round(c_final, 6),
        "t_cal": round(t_cal, 6),
        "high_cutoff": HIGH_THRESHOLD,
        "confidence": confidence,
    }

    logger.debug("Risk: %s (C_final=%.4f, T_cal=%.4f)", risk_level, c_final, t_cal)
    return result


# ========================== TEST BLOCK ====================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    print("=" * 65)
    print("HPCM M7 — Risk Classification Module Test")
    print("=" * 65)

    test_cases = [
        # (label, c_final, t_cal, expected_risk)
        ("Clear HIGH",             0.92, 0.68, "HIGH"),
        ("Boundary HIGH (0.80)",   0.80, 0.65, "HIGH"),
        ("Clear MEDIUM",           0.72, 0.65, "MEDIUM"),
        ("Boundary MEDIUM (=T)",   0.65, 0.65, "MEDIUM"),
        ("Clear LOW",              0.40, 0.65, "LOW"),
        ("Just below T_cal",       0.64, 0.65, "LOW"),
        ("Zero score",             0.00, 0.65, "LOW"),
        ("Perfect score",          1.00, 0.70, "HIGH"),
        ("High T_cal, mid score",  0.72, 0.75, "LOW"),
        ("Low T_cal, mid score",   0.55, 0.50, "MEDIUM"),
    ]

    all_passed = True
    for label, c_final, t_cal, expected in test_cases:
        result = classify_risk(c_final, t_cal)
        actual = result["risk_level"]
        match = actual == expected
        status = "[OK]" if match else "[FAIL]"

        if not match:
            all_passed = False

        print(f"\n--- {label} ---")
        print(f"  C_final    : {c_final}")
        print(f"  T_cal      : {t_cal}")
        print(f"  Risk       : {actual}")
        print(f"  Expected   : {expected}")
        print(f"  Confidence : {result['confidence']}")
        print(f"  {status}")

    print("\n" + "=" * 65)
    if all_passed:
        print("M7 risk.py — ALL CHECKS PASSED")
    else:
        print("M7 risk.py — SOME CHECKS FAILED (see above)")
    print("=" * 65)