"""
M4 — stylometric.py
HPCM Plagiarism Detection System
----------------------------------
Writing-style features → S_sty
  • POS tag distribution similarity
  • Type-Token Ratio (TTR) difference
  • Average sentence length difference
Consumes tokens, clean_tokens, sentences from M1
and get_pos_tags() from M1 for spaCy POS tagging.
"""

import logging
import math
from collections import Counter

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

# ---------------------------------------------------------------------------
# Logger
# ---------------------------------------------------------------------------
logger = logging.getLogger("hpcm.stylometric")

# POS tags we track (spaCy universal POS set)
POS_TAGS = [
    "ADJ", "ADP", "ADV", "AUX", "CCONJ", "DET", "INTJ",
    "NOUN", "NUM", "PART", "PRON", "PROPN", "PUNCT",
    "SCONJ", "SYM", "VERB", "X",
]


def _pos_distribution(pos_tags: list[tuple[str, str]]) -> np.ndarray:
    """
    Convert (token, POS) pairs into a normalized frequency vector.

    Returns
    -------
    np.ndarray of shape (1, len(POS_TAGS))
    """
    counts = Counter(tag for _, tag in pos_tags)
    total = sum(counts.values()) or 1
    vec = [counts.get(tag, 0) / total for tag in POS_TAGS]
    return np.array(vec).reshape(1, -1)


def _pos_similarity(src_pos: list[tuple[str, str]], sus_pos: list[tuple[str, str]]) -> float:
    """Cosine similarity between POS distribution vectors."""
    src_vec = _pos_distribution(src_pos)
    sus_vec = _pos_distribution(sus_pos)

    # Edge case: zero vectors
    if np.all(src_vec == 0) or np.all(sus_vec == 0):
        return 0.0

    return float(cosine_similarity(src_vec, sus_vec)[0][0])


def _type_token_ratio(tokens: list[str]) -> float:
    """TTR = unique tokens / total tokens."""
    if not tokens:
        return 0.0
    return len(set(tokens)) / len(tokens)


def _avg_sentence_length(tokens: list[str], num_sentences: int) -> float:
    """Average number of tokens per sentence."""
    if num_sentences == 0:
        return 0.0
    return len(tokens) / num_sentences


def _ttr_similarity(ttr_a: float, ttr_b: float) -> float:
    """Convert TTR difference into a similarity score [0, 1]."""
    return 1.0 - abs(ttr_a - ttr_b)


def _sent_len_similarity(avg_a: float, avg_b: float) -> float:
    """
    Convert average sentence length difference into similarity [0, 1].
    Uses exponential decay so large differences → low similarity.
    """
    diff = abs(avg_a - avg_b)
    return math.exp(-0.1 * diff)


def compute_stylometric_similarity(
    source_data: dict,
    suspect_data: dict,
    source_pos: list[tuple[str, str]],
    suspect_pos: list[tuple[str, str]],
) -> dict:
    """
    Compare writing style between two documents.

    Parameters
    ----------
    source_data   : dict — M1 preprocess() output for source
    suspect_data  : dict — M1 preprocess() output for suspect
    source_pos    : list[(token, POS)] from M1 get_pos_tags()
    suspect_pos   : list[(token, POS)] from M1 get_pos_tags()

    Returns
    -------
    dict with keys:
        s_sty            — float, combined stylometric similarity [0.0, 1.0]
        pos_similarity   — float, POS distribution cosine similarity
        ttr_similarity   — float, TTR-based similarity
        sentlen_similarity — float, avg sentence length similarity
        source_ttr       — float
        suspect_ttr      — float
        source_avg_sentlen — float
        suspect_avg_sentlen — float
    """
    # Edge case: empty documents
    if not source_data["tokens"] or not suspect_data["tokens"]:
        logger.warning("One or both documents are empty — returning S_sty = 0.0")
        return {
            "s_sty": 0.0,
            "pos_similarity": 0.0,
            "ttr_similarity": 0.0,
            "sentlen_similarity": 0.0,
            "source_ttr": 0.0,
            "suspect_ttr": 0.0,
            "source_avg_sentlen": 0.0,
            "suspect_avg_sentlen": 0.0,
        }

    # --- POS distribution similarity ---
    pos_sim = _pos_similarity(source_pos, suspect_pos)

    # --- TTR similarity ---
    src_ttr = _type_token_ratio(source_data["clean_tokens"])
    sus_ttr = _type_token_ratio(suspect_data["clean_tokens"])
    ttr_sim = _ttr_similarity(src_ttr, sus_ttr)

    # --- Average sentence length similarity ---
    src_avg = _avg_sentence_length(source_data["tokens"], source_data["num_sentences"])
    sus_avg = _avg_sentence_length(suspect_data["tokens"], suspect_data["num_sentences"])
    sentlen_sim = _sent_len_similarity(src_avg, sus_avg)

    # --- Combined S_sty (equal weighting of 3 sub-features) ---
    s_sty = (pos_sim + ttr_sim + sentlen_sim) / 3.0

    result = {
        "s_sty": round(s_sty, 6),
        "pos_similarity": round(pos_sim, 6),
        "ttr_similarity": round(ttr_sim, 6),
        "sentlen_similarity": round(sentlen_sim, 6),
        "source_ttr": round(src_ttr, 4),
        "suspect_ttr": round(sus_ttr, 4),
        "source_avg_sentlen": round(src_avg, 2),
        "suspect_avg_sentlen": round(sus_avg, 2),
    }

    logger.debug(
        "Stylometric: S_sty=%.4f (POS=%.4f TTR=%.4f SentLen=%.4f)",
        s_sty, pos_sim, ttr_sim, sentlen_sim,
    )
    return result


# ========================== TEST BLOCK ====================================
if __name__ == "__main__":
    import sys
    import os

    logging.basicConfig(level=logging.DEBUG)

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from modules.preprocessing import preprocess, get_pos_tags

    # --- Test Pair 1: Similar writing style ---
    text_a = """
    Natural language processing (NLP) is a subfield of linguistics, computer
    science, and artificial intelligence concerned with the interactions between
    computers and human language. The goal is to enable computers to understand,
    interpret, and generate human language in a valuable way.
    """
    text_b = """
    NLP, a branch of AI, focuses on the interaction between computers and
    human languages. It aims to help machines understand and produce natural
    language that is meaningful and useful.
    """

    # --- Test Pair 2: Very different style ---
    text_c = """
    Sun. Hot. Plants eat light. They make food. Leaves do it. Green stuff
    helps. Water comes up. CO2 goes in. Sugar comes out. Simple.
    """

    # --- Test Pair 3: Identical ---
    text_d = text_a

    print("=" * 65)
    print("HPCM M4 — Stylometric Similarity Module Test")
    print("=" * 65)

    prep_a = preprocess(text_a)
    prep_b = preprocess(text_b)
    prep_c = preprocess(text_c)
    prep_d = preprocess(text_d)

    pos_a = get_pos_tags(text_a)
    pos_b = get_pos_tags(text_b)
    pos_c = get_pos_tags(text_c)
    pos_d = get_pos_tags(text_d)

    pairs = [
        ("A vs B (similar style)", prep_a, prep_b, pos_a, pos_b),
        ("A vs C (different style)", prep_a, prep_c, pos_a, pos_c),
        ("A vs D (identical)", prep_a, prep_d, pos_a, pos_d),
    ]

    all_passed = True
    for label, src_d, sus_d, src_p, sus_p in pairs:
        result = compute_stylometric_similarity(src_d, sus_d, src_p, sus_p)
        s = result["s_sty"]
        print(f"\n--- {label} ---")
        print(f"  S_sty           : {s}")
        print(f"  POS similarity  : {result['pos_similarity']}")
        print(f"  TTR similarity  : {result['ttr_similarity']}")
        print(f"  SentLen sim     : {result['sentlen_similarity']}")
        print(f"  Source TTR      : {result['source_ttr']}")
        print(f"  Suspect TTR     : {result['suspect_ttr']}")
        print(f"  Source avg sent  : {result['source_avg_sentlen']}")
        print(f"  Suspect avg sent : {result['suspect_avg_sentlen']}")

        if "identical" in label.lower() and s < 0.99:
            print("  [FAIL] Identical docs should have S_sty ≈ 1.0")
            all_passed = False
        elif "different style" in label.lower() and s > 0.90:
            print("  [FAIL] Very different styles should show lower S_sty")
            all_passed = False
        else:
            print("  [OK]")

    print("\n" + "=" * 65)
    if all_passed:
        print("M4 stylometric.py — ALL CHECKS PASSED")
    else:
        print("M4 stylometric.py — SOME CHECKS FAILED (see above)")
    print("=" * 65)