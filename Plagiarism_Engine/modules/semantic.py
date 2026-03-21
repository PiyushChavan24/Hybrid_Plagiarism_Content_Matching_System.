"""
M3 — semantic.py
HPCM Plagiarism Detection System
----------------------------------
Sentence-BERT embeddings → cosine similarity → S_sem
Consumes sentences from M1 preprocessing.
"""

import logging
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# ---------------------------------------------------------------------------
# Logger
# ---------------------------------------------------------------------------
logger = logging.getLogger("hpcm.semantic")

# ---------------------------------------------------------------------------
# Load model once at module level (reused across calls)
# First call downloads ~90 MB, then cached locally.
# ---------------------------------------------------------------------------
MODEL_NAME = "all-MiniLM-L6-v2"
logger.info("Loading Sentence-BERT model: %s ...", MODEL_NAME)
sbert_model = SentenceTransformer(MODEL_NAME)
logger.info("Sentence-BERT model loaded.")


def _embed_sentences(sentences: list[str]) -> np.ndarray:
    """
    Encode a list of sentences into dense vectors.

    Returns
    -------
    np.ndarray of shape (n_sentences, embedding_dim)
    """
    embeddings = sbert_model.encode(sentences, show_progress_bar=False)
    return np.array(embeddings)


def _document_embedding(sentence_embeddings: np.ndarray) -> np.ndarray:
    """
    Create a single document-level embedding by averaging sentence vectors.

    Returns
    -------
    np.ndarray of shape (1, embedding_dim)
    """
    return np.mean(sentence_embeddings, axis=0).reshape(1, -1)


def compute_semantic_similarity(
    source_sentences: list[str],
    suspect_sentences: list[str],
) -> dict:
    """
    Compare two documents using Sentence-BERT embeddings.

    Parameters
    ----------
    source_sentences  : list[str] — sentences from M1 for the source doc
    suspect_sentences : list[str] — sentences from M1 for the suspect doc

    Returns
    -------
    dict with keys:
        s_sem               — float, document-level cosine similarity [0.0, 1.0]
        max_sentence_sim    — float, highest sentence-pair similarity
        avg_sentence_sim    — float, mean of best-match similarities
        source_sent_count   — int
        suspect_sent_count  — int
    """
    # Edge case: empty sentence lists
    if not source_sentences or not suspect_sentences:
        logger.warning("One or both sentence lists are empty — returning S_sem = 0.0")
        return {
            "s_sem": 0.0,
            "max_sentence_sim": 0.0,
            "avg_sentence_sim": 0.0,
            "source_sent_count": len(source_sentences),
            "suspect_sent_count": len(suspect_sentences),
        }

    # Encode sentences
    src_emb = _embed_sentences(source_sentences)
    sus_emb = _embed_sentences(suspect_sentences)

    # --- Document-level similarity (averaged embeddings) ---
    src_doc = _document_embedding(src_emb)
    sus_doc = _document_embedding(sus_emb)
    s_sem = float(cosine_similarity(src_doc, sus_doc)[0][0])

    # --- Sentence-level cross-similarity matrix ---
    sim_matrix = cosine_similarity(src_emb, sus_emb)

    # For each source sentence, find best match in suspect
    best_matches = np.max(sim_matrix, axis=1)  # shape (n_source,)
    max_sentence_sim = float(np.max(sim_matrix))
    avg_sentence_sim = float(np.mean(best_matches))

    result = {
        "s_sem": round(s_sem, 6),
        "max_sentence_sim": round(max_sentence_sim, 6),
        "avg_sentence_sim": round(avg_sentence_sim, 6),
        "source_sent_count": len(source_sentences),
        "suspect_sent_count": len(suspect_sentences),
    }

    logger.debug(
        "Semantic similarity: S_sem=%.4f  max_sent=%.4f  avg_sent=%.4f",
        s_sem, max_sentence_sim, avg_sentence_sim,
    )
    return result


# ========================== TEST BLOCK ====================================
if __name__ == "__main__":
    import sys
    import os

    logging.basicConfig(level=logging.DEBUG)

    # Import M1
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from modules.preprocessing import preprocess

    # --- Test Pair 1: High similarity (paraphrase) ---
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

    # --- Test Pair 2: Low similarity (different topic) ---
    text_c = """
    Photosynthesis is the process used by plants to convert light energy into
    chemical energy that can be stored and later released to fuel the plant's
    activities. This process occurs primarily in the leaves of the plant.
    """

    # --- Test Pair 3: Identical ---
    text_d = text_a

    print("=" * 65)
    print("HPCM M3 — Semantic Similarity Module Test")
    print("=" * 65)

    prep_a = preprocess(text_a)
    prep_b = preprocess(text_b)
    prep_c = preprocess(text_c)
    prep_d = preprocess(text_d)

    pairs = [
        ("A vs B (paraphrase)", prep_a["sentences"], prep_b["sentences"]),
        ("A vs C (different)",  prep_a["sentences"], prep_c["sentences"]),
        ("A vs D (identical)",  prep_a["sentences"], prep_d["sentences"]),
        ("Empty vs A",         [],                   prep_a["sentences"]),
    ]

    all_passed = True
    for label, src, sus in pairs:
        result = compute_semantic_similarity(src, sus)
        s = result["s_sem"]
        print(f"\n--- {label} ---")
        print(f"  S_sem          : {s}")
        print(f"  Max sent sim   : {result['max_sentence_sim']}")
        print(f"  Avg sent sim   : {result['avg_sentence_sim']}")
        print(f"  Source sents   : {result['source_sent_count']}")
        print(f"  Suspect sents  : {result['suspect_sent_count']}")

        # Sanity checks
        if "identical" in label.lower() and s < 0.99:
            print("  [FAIL] Identical docs should have S_sem ≈ 1.0")
            all_passed = False
        elif "different" in label.lower() and s > 0.70:
            print("  [FAIL] Different topics should have lower S_sem")
            all_passed = False
        elif "paraphrase" in label.lower() and s < 0.50:
            print("  [FAIL] Paraphrase should have moderate-high S_sem")
            all_passed = False
        elif "empty" in label.lower() and s != 0.0:
            print("  [FAIL] Empty doc should yield S_sem = 0.0")
            all_passed = False
        else:
            print("  [OK]")

    print("\n" + "=" * 65)
    if all_passed:
        print("M3 semantic.py — ALL CHECKS PASSED")
    else:
        print("M3 semantic.py — SOME CHECKS FAILED (see above)")
    print("=" * 65)