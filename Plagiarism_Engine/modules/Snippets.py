"""
M9 — snippets.py
HPCM Plagiarism Detection System
----------------------------------
Extracts matching sentence pairs between source and suspect documents.
OPTIMIZED: Accepts pre-computed source embeddings to avoid re-encoding.
"""

import logging
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from modules.semantic import sbert_model

# ---------------------------------------------------------------------------
# Logger
# ---------------------------------------------------------------------------
logger = logging.getLogger("hpcm.snippets")

# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------
SNIPPET_THRESHOLD = 0.75


def extract_snippets(
    source_sentences: list[str],
    suspect_sentences: list[str],
    threshold: float = SNIPPET_THRESHOLD,
    max_snippets: int = 10,
    _src_embeddings: np.ndarray = None,
) -> list[dict]:
    """
    Find matching sentence pairs between source and suspect.

    Parameters
    ----------
    source_sentences   : list[str]
    suspect_sentences  : list[str]
    threshold          : float — minimum cosine similarity to flag
    max_snippets       : int
    _src_embeddings    : np.ndarray or None — pre-computed source embeddings

    Returns
    -------
    list[dict] with matching sentence pairs
    """
    if not source_sentences or not suspect_sentences:
        return []

    # Filter out very short sentences (< 5 words)
    src_valid = [(i, s) for i, s in enumerate(source_sentences) if len(s.split()) >= 5]
    sus_valid = [(i, s) for i, s in enumerate(suspect_sentences) if len(s.split()) >= 5]

    if not src_valid or not sus_valid:
        return []

    src_indices, src_texts = zip(*src_valid)
    sus_indices, sus_texts = zip(*sus_valid)

    # Encode sentences — use cached source embeddings if available
    if _src_embeddings is not None and len(_src_embeddings) > 0:
        # Filter cached embeddings to match valid indices
        src_embeddings = _src_embeddings[list(src_indices)]
    else:
        src_embeddings = sbert_model.encode(list(src_texts), show_progress_bar=False)

    sus_embeddings = sbert_model.encode(list(sus_texts), show_progress_bar=False)

    # Compute cross-similarity matrix
    sim_matrix = cosine_similarity(src_embeddings, sus_embeddings)

    # Find all pairs above threshold
    matches = []
    for i in range(len(src_texts)):
        for j in range(len(sus_texts)):
            sim = float(sim_matrix[i][j])
            if sim >= threshold:
                matches.append({
                    "source_sentence": src_texts[i].strip(),
                    "suspect_sentence": sus_texts[j].strip(),
                    "similarity": round(sim, 4),
                    "source_index": src_indices[i],
                    "suspect_index": sus_indices[j],
                })

    # Sort by similarity (highest first)
    matches.sort(key=lambda x: x["similarity"], reverse=True)

    # Deduplicate: each source/suspect sentence maps to at most one match
    seen_source = set()
    seen_suspect = set()
    unique_matches = []
    for m in matches:
        if m["source_index"] not in seen_source and m["suspect_index"] not in seen_suspect:
            unique_matches.append(m)
            seen_source.add(m["source_index"])
            seen_suspect.add(m["suspect_index"])
        if len(unique_matches) >= max_snippets:
            break

    logger.debug(
        "Snippets: %d pairs above threshold %.2f (returned %d)",
        len(matches), threshold, len(unique_matches),
    )
    return unique_matches


# ========================== TEST BLOCK ====================================
if __name__ == "__main__":
    import sys
    import os

    logging.basicConfig(level=logging.DEBUG)

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from modules.preprocessing import preprocess

    text_a = """
    Natural language processing is a subfield of linguistics and artificial
    intelligence concerned with the interactions between computers and human
    language. The goal is to enable computers to understand, interpret, and
    generate human language in a valuable way. NLP combines computational
    linguistics with statistical and deep learning models.
    """

    text_b = """
    NLP is an area of AI that focuses on how computers interact with human
    languages. It aims to help machines understand and produce natural language.
    The field brings together ideas from linguistics and machine learning.
    Photosynthesis is how plants convert sunlight into energy.
    """

    prep_a = preprocess(text_a)
    prep_b = preprocess(text_b)

    print("=" * 65)
    print("HPCM M9 — Snippet Extraction Test")
    print("=" * 65)

    snippets = extract_snippets(prep_a["sentences"], prep_b["sentences"])

    if not snippets:
        print("\n  No matching snippets found.")
    else:
        for i, s in enumerate(snippets):
            print(f"\n--- Match {i + 1} (similarity: {s['similarity']}) ---")
            print(f"  SOURCE [{s['source_index']}]: {s['source_sentence']}")
            print(f"  SUSPECT[{s['suspect_index']}]: {s['suspect_sentence']}")

    print(f"\n{'=' * 65}")
    if len(snippets) > 0:
        print("M9 snippets.py — ALL CHECKS PASSED")
    else:
        print("M9 snippets.py — WARNING: No snippets found")
    print("=" * 65)