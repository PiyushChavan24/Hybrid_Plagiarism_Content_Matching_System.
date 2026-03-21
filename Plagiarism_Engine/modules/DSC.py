"""
M6 — dsc.py
HPCM Plagiarism Detection System
----------------------------------
Dynamic Similarity Calibration (DSC)
Computes a calibrated threshold T_cal that adapts based on
document characteristics rather than using a fixed cutoff.

  T_cal = T_base + F_len + F_vocab + F_topic

Where:
  T_base  = 0.65 (baseline threshold)
  F_len   = length disparity factor    [-0.05, +0.05]
  F_vocab = vocabulary richness factor  [-0.05, +0.05]
  F_topic = topic similarity factor     [-0.05, +0.05]
"""

import logging
import math

# ---------------------------------------------------------------------------
# Logger
# ---------------------------------------------------------------------------
logger = logging.getLogger("hpcm.dsc")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
T_BASE = 0.65

# Calibration factor bounds
F_MIN = -0.05
F_MAX = 0.05


def _clamp(value: float, lo: float, hi: float) -> float:
    """Clamp value to [lo, hi]."""
    return max(lo, min(hi, value))


def _length_factor(source_tokens: int, suspect_tokens: int) -> float:
    """
    Length disparity factor.
    Very different lengths → lower threshold (easier to flag).
    Similar lengths → higher threshold (stricter).
    """
    if source_tokens == 0 and suspect_tokens == 0:
        return 0.0
    max_len = max(source_tokens, suspect_tokens, 1)
    ratio = min(source_tokens, suspect_tokens) / max_len  # [0, 1]
    # ratio=1 (same length) → +0.05, ratio=0 (huge diff) → -0.05
    return _clamp(F_MIN + (F_MAX - F_MIN) * ratio, F_MIN, F_MAX)


def _vocab_factor(source_ttr: float, suspect_ttr: float) -> float:
    """
    Vocabulary richness factor.
    Similar TTR → raise threshold (similar writing, need more evidence).
    Different TTR → lower threshold (style mismatch is suspicious).
    """
    ttr_diff = abs(source_ttr - suspect_ttr)  # [0, 1]
    # diff=0 (same richness) → +0.05, diff=1 → -0.05
    return _clamp(F_MAX - (F_MAX - F_MIN) * ttr_diff, F_MIN, F_MAX)


def _topic_factor(s_sem: float) -> float:
    """
    Topic similarity factor.
    High semantic similarity → raise threshold (same topic needs stricter check).
    Low semantic similarity → lower threshold (different topics flagged easier).
    """
    # s_sem in [0, 1] maps linearly to [-0.05, +0.05]
    return _clamp(F_MIN + (F_MAX - F_MIN) * s_sem, F_MIN, F_MAX)


def compute_threshold(
    source_tokens: int,
    suspect_tokens: int,
    source_ttr: float,
    suspect_ttr: float,
    s_sem: float,
) -> dict:
    """
    Compute calibrated plagiarism threshold.

    Parameters
    ----------
    source_tokens   : int   — token count from M1 (source)
    suspect_tokens  : int   — token count from M1 (suspect)
    source_ttr      : float — TTR from M4 (source)
    suspect_ttr     : float — TTR from M4 (suspect)
    s_sem           : float — semantic similarity from M3

    Returns
    -------
    dict with keys:
        t_cal        — float, calibrated threshold
        t_base       — float, baseline (0.65)
        f_len        — float, length factor
        f_vocab      — float, vocabulary factor
        f_topic      — float, topic factor
    """
    f_len = _length_factor(source_tokens, suspect_tokens)
    f_vocab = _vocab_factor(source_ttr, suspect_ttr)
    f_topic = _topic_factor(s_sem)

    t_cal = T_BASE + f_len + f_vocab + f_topic

    # Final clamp: threshold should stay reasonable [0.50, 0.80]
    t_cal = _clamp(t_cal, 0.50, 0.80)

    result = {
        "t_cal": round(t_cal, 6),
        "t_base": T_BASE,
        "f_len": round(f_len, 6),
        "f_vocab": round(f_vocab, 6),
        "f_topic": round(f_topic, 6),
    }

    logger.debug(
        "DSC: T_cal=%.4f (base=%.2f + len=%.4f + vocab=%.4f + topic=%.4f)",
        t_cal, T_BASE, f_len, f_vocab, f_topic,
    )
    return result


# ========================== TEST BLOCK ====================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    print("=" * 65)
    print("HPCM M6 — Dynamic Similarity Calibration Test")
    print("=" * 65)

    test_cases = [
        {
            "label": "Similar docs (same length, same TTR, high semantic)",
            "source_tokens": 100, "suspect_tokens": 100,
            "source_ttr": 0.70, "suspect_ttr": 0.70,
            "s_sem": 0.90,
            "expect_range": (0.70, 0.80),  # all factors push UP
        },
        {
            "label": "Different docs (diff length, diff TTR, low semantic)",
            "source_tokens": 200, "suspect_tokens": 50,
            "source_ttr": 0.80, "suspect_ttr": 0.40,
            "s_sem": 0.15,
            "expect_range": (0.50, 0.60),  # all factors push DOWN
        },
        {
            "label": "Neutral case (moderate everything)",
            "source_tokens": 100, "suspect_tokens": 80,
            "source_ttr": 0.65, "suspect_ttr": 0.60,
            "s_sem": 0.50,
            "expect_range": (0.60, 0.72),
        },
        {
            "label": "Edge: both empty",
            "source_tokens": 0, "suspect_tokens": 0,
            "source_ttr": 0.0, "suspect_ttr": 0.0,
            "s_sem": 0.0,
            "expect_range": (0.50, 0.70),
        },
        {
            "label": "Edge: identical characteristics",
            "source_tokens": 150, "suspect_tokens": 150,
            "source_ttr": 0.65, "suspect_ttr": 0.65,
            "s_sem": 1.0,
            "expect_range": (0.75, 0.80),  # all maxed out
        },
    ]

    all_passed = True
    for tc in test_cases:
        result = compute_threshold(
            tc["source_tokens"], tc["suspect_tokens"],
            tc["source_ttr"], tc["suspect_ttr"],
            tc["s_sem"],
        )
        t = result["t_cal"]
        lo, hi = tc["expect_range"]
        in_range = lo <= t <= hi
        status = "[OK]" if in_range else "[FAIL]"

        if not in_range:
            all_passed = False

        print(f"\n--- {tc['label']} ---")
        print(f"  T_cal       : {t}")
        print(f"  Expected    : {lo} – {hi}")
        print(f"  Factors     : len={result['f_len']}  vocab={result['f_vocab']}  topic={result['f_topic']}")
        print(f"  {status}")

    print("\n" + "=" * 65)
    if all_passed:
        print("M6 dsc.py — ALL CHECKS PASSED")
    else:
        print("M6 dsc.py — SOME CHECKS FAILED (see above)")
    print("=" * 65)