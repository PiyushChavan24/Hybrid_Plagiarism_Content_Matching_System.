"""
M2 — lexical.py
HPCM Plagiarism Detection System
----------------------------------
TF-IDF vectorization + cosine similarity → S_lex
Consumes clean_text from M1 preprocessing.
"""

import logging
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# ---------------------------------------------------------------------------
# Logger
# ---------------------------------------------------------------------------
logger = logging.getLogger("hpcm.lexical")


def compute_lexical_similarity(source_clean: str, suspect_clean: str) -> dict:
    """
    Compare two documents using TF-IDF cosine similarity.

    Parameters
    ----------
    source_clean  : str — clean_text from M1 for the source document
    suspect_clean : str — clean_text from M1 for the suspect document

    Returns
    -------
    dict with keys:
        s_lex           — float, cosine similarity [0.0, 1.0]
        tfidf_vocab_size — int, number of features in the TF-IDF matrix
        source_len      — int, token count in source
        suspect_len     — int, token count in suspect
    """
    # Edge case: either document is empty after preprocessing
    if not source_clean.strip() or not suspect_clean.strip():
        logger.warning("One or both documents are empty — returning S_lex = 0.0")
        return {
            "s_lex": 0.0,
            "tfidf_vocab_size": 0,
            "source_len": len(source_clean.split()),
            "suspect_len": len(suspect_clean.split()),
        }

    # Build TF-IDF matrix over both documents
    vectorizer = TfidfVectorizer(
        lowercase=False,        # already lowercased in M1
        token_pattern=r"(?u)\b\w+\b",  # single-char tokens OK
    )

    tfidf_matrix = vectorizer.fit_transform([source_clean, suspect_clean])

    # Cosine similarity between row 0 (source) and row 1 (suspect)
    sim_matrix = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])
    s_lex = float(sim_matrix[0][0])

    result = {
        "s_lex": round(s_lex, 6),
        "tfidf_vocab_size": len(vectorizer.vocabulary_),
        "source_len": len(source_clean.split()),
        "suspect_len": len(suspect_clean.split()),
    }

    logger.debug("Lexical similarity: %.4f (vocab=%d)", s_lex, result["tfidf_vocab_size"])
    return result


# ========================== TEST BLOCK ====================================
if __name__ == "__main__":
    import sys
    import os

    logging.basicConfig(level=logging.DEBUG)

    # Import M1 from the same modules/ directory
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from modules.preprocessing import preprocess

    # --- Test Pair 1: High similarity (near-paraphrase) ---
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

    # --- Test Pair 2: Low similarity (different topics) ---
    text_c = """
    Photosynthesis is the process used by plants to convert light energy into
    chemical energy that can be stored and later released to fuel the plant's
    activities. This process occurs primarily in the leaves of the plant.
    """

    # --- Test Pair 3: Identical ---
    text_d = text_a  # exact copy

    print("=" * 65)
    print("HPCM M2 — Lexical Similarity Module Test")
    print("=" * 65)

    prep_a = preprocess(text_a)
    prep_b = preprocess(text_b)
    prep_c = preprocess(text_c)
    prep_d = preprocess(text_d)

    pairs = [
        ("A vs B (paraphrase)",   prep_a["clean_text"], prep_b["clean_text"]),
        ("A vs C (different)",    prep_a["clean_text"], prep_c["clean_text"]),
        ("A vs D (identical)",    prep_a["clean_text"], prep_d["clean_text"]),
        ("Empty vs A",           "",                    prep_a["clean_text"]),
    ]

    all_passed = True
    for label, src, sus in pairs:
        result = compute_lexical_similarity(src, sus)
        s = result["s_lex"]
        print(f"\n--- {label} ---")
        print(f"  S_lex       : {s}")
        print(f"  Vocab size  : {result['tfidf_vocab_size']}")
        print(f"  Source toks : {result['source_len']}")
        print(f"  Suspect toks: {result['suspect_len']}")

        # Sanity checks
        if "identical" in label.lower() and s < 0.99:
            print("  [FAIL] Identical docs should have S_lex ≈ 1.0")
            all_passed = False
        elif "different" in label.lower() and s > 0.5:
            print("  [FAIL] Different topics should have low S_lex")
            all_passed = False
        elif "empty" in label.lower() and s != 0.0:
            print("  [FAIL] Empty doc should yield S_lex = 0.0")
            all_passed = False
        else:
            print("  [OK]")

    print("\n" + "=" * 65)
    if all_passed:
        print("M2 lexical.py — ALL CHECKS PASSED")
    else:
        print("M2 lexical.py — SOME CHECKS FAILED (see above)")
    print("=" * 65)