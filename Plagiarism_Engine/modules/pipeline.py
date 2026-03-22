"""
M8 — pipeline.py
HPCM Plagiarism Detection System
----------------------------------
Orchestrator: calls M1 → M7 + M9 in sequence, returns a full report dict.
OPTIMIZED: Caches source preprocessing and embeddings across comparisons.
           Uses pre-computed suspect embeddings when available.
"""

import logging
import time
import numpy as np

from modules.preprocessing import preprocess, get_pos_tags
from modules.lexical import compute_lexical_similarity
from modules.semantic import compute_semantic_similarity, sbert_model
from modules.stylometric import compute_stylometric_similarity
from modules.fusion import compute_fusion
from modules.DSC import compute_threshold
from modules.risk import classify_risk
from modules.Snippets import extract_snippets

# ---------------------------------------------------------------------------
# Logger
# ---------------------------------------------------------------------------
logger = logging.getLogger("hpcm.pipeline")


def _encode_sentences(sentences: list[str]) -> np.ndarray:
    """Encode sentences with SBERT — cached at call site."""
    if not sentences:
        return np.array([])
    return sbert_model.encode(sentences, show_progress_bar=False)


def run_pipeline(
    source_id: str,
    source_text: str,
    suspect_id: str,
    suspect_title: str,
    suspect_text: str,
    use_layer4: bool = True,
    # Pre-computed source data (for multi-comparison optimization)
    _src_prep: dict = None,
    _src_embeddings: np.ndarray = None,
    _src_pos: list = None,
    # Pre-computed suspect embedding (from database)
    _sus_embedding: list = None,
) -> dict:
    """
    Run the full HPCM plagiarism detection pipeline on a document pair.
    Accepts pre-computed source data and suspect embeddings to avoid redundant processing.
    """
    start_time = time.time()

    # ---- M1: Preprocessing ----
    if _src_prep is None:
        logger.info("M1: Preprocessing source (%s)...", source_id)
        src_prep = preprocess(source_text)
    else:
        src_prep = _src_prep

    logger.info("M1: Preprocessing suspect (%s)...", suspect_id)
    sus_prep = preprocess(suspect_text)

    # ---- M2: Lexical Similarity ----
    logger.info("M2: Computing lexical similarity...")
    lex_result = compute_lexical_similarity(
        src_prep["clean_text"],
        sus_prep["clean_text"],
    )
    s_lex = lex_result["s_lex"]

    # ---- M3: Semantic Similarity (use cached embeddings) ----
    logger.info("M3: Computing semantic similarity...")
    if _src_embeddings is not None and len(_src_embeddings) > 0:
        # Use cached source embeddings
        from sklearn.metrics.pairwise import cosine_similarity

        # Use pre-computed suspect embedding if available, otherwise encode
        if _sus_embedding is not None:
            logger.info("M3: Using pre-computed suspect embedding")
            sus_embeddings = np.array(_sus_embedding).reshape(1, -1)
        else:
            sus_embeddings = _encode_sentences(sus_prep["sentences"])

        if len(sus_embeddings) == 0 or len(_src_embeddings) == 0:
            sem_result = {
                "s_sem": 0.0,
                "max_sentence_sim": 0.0,
                "avg_sentence_sim": 0.0,
                "source_sent_count": len(src_prep["sentences"]),
                "suspect_sent_count": len(sus_prep["sentences"]),
            }
        else:
            src_doc = np.mean(_src_embeddings, axis=0).reshape(1, -1)

            # For pre-computed embedding, it's already a document-level embedding
            if _sus_embedding is not None:
                sus_doc = sus_embeddings
            else:
                sus_doc = np.mean(sus_embeddings, axis=0).reshape(1, -1)

            s_sem_val = float(cosine_similarity(src_doc, sus_doc)[0][0])

            # Sentence-level similarity matrix (only if we have sentence-level embeddings)
            if _sus_embedding is not None:
                # Can't compute sentence-level matrix with doc-level embedding
                # Use doc-level similarity as approximation
                sem_result = {
                    "s_sem": round(s_sem_val, 6),
                    "max_sentence_sim": round(s_sem_val, 6),
                    "avg_sentence_sim": round(s_sem_val, 6),
                    "source_sent_count": len(src_prep["sentences"]),
                    "suspect_sent_count": len(sus_prep["sentences"]),
                }
            else:
                sim_matrix = cosine_similarity(_src_embeddings, sus_embeddings)
                best_matches = np.max(sim_matrix, axis=1)
                sem_result = {
                    "s_sem": round(s_sem_val, 6),
                    "max_sentence_sim": round(float(np.max(sim_matrix)), 6),
                    "avg_sentence_sim": round(float(np.mean(best_matches)), 6),
                    "source_sent_count": len(src_prep["sentences"]),
                    "suspect_sent_count": len(sus_prep["sentences"]),
                }
    else:
        sem_result = compute_semantic_similarity(
            src_prep["sentences"],
            sus_prep["sentences"],
        )
    s_sem = sem_result["s_sem"]

    # ---- M4: Stylometric Similarity (optional) ----
    if use_layer4:
        logger.info("M4: Computing stylometric similarity...")
        src_pos = _src_pos if _src_pos is not None else get_pos_tags(src_prep["normalized"])
        sus_pos = get_pos_tags(sus_prep["normalized"])
        sty_result = compute_stylometric_similarity(
            src_prep, sus_prep, src_pos, sus_pos,
        )
        s_sty = sty_result["s_sty"]
    else:
        logger.info("M4: Skipped (use_layer4=False)")
        sty_result = {"s_sty": 0.0, "pos_similarity": 0.0,
                      "ttr_similarity": 0.0, "sentlen_similarity": 0.0,
                      "source_ttr": 0.0, "suspect_ttr": 0.0,
                      "source_avg_sentlen": 0.0, "suspect_avg_sentlen": 0.0}
        s_sty = 0.0

    # ---- M5: Fusion ----
    logger.info("M5: Computing fusion score...")
    fusion_result = compute_fusion(s_lex, s_sem, s_sty)
    c_final = fusion_result["c_final"]

    # ---- M6: DSC Threshold ----
    logger.info("M6: Computing calibrated threshold...")
    src_ttr = sty_result.get("source_ttr", 0.0)
    sus_ttr = sty_result.get("suspect_ttr", 0.0)
    dsc_result = compute_threshold(
        src_prep["num_tokens"],
        sus_prep["num_tokens"],
        src_ttr,
        sus_ttr,
        s_sem,
    )
    t_cal = dsc_result["t_cal"]

    # ---- M7: Risk Classification ----
    logger.info("M7: Classifying risk...")
    risk_result = classify_risk(c_final, t_cal)

    # ---- M9: Snippet Extraction (use cached embeddings) ----
    logger.info("M9: Extracting matching snippets...")
    snippets = extract_snippets(
        src_prep["sentences"],
        sus_prep["sentences"],
        _src_embeddings=_src_embeddings,
    )

    elapsed = round(time.time() - start_time, 3)

    # ---- Build Report ----
    report = {
        "source_id": source_id,
        "suspect_id": suspect_id,
        "suspect_title": suspect_title,
        "scores": {
            "s_lex": s_lex,
            "s_sem": s_sem,
            "s_sty": s_sty,
            "c_final": c_final,
        },
        "threshold": {
            "t_cal": t_cal,
            "t_base": dsc_result["t_base"],
            "factors": {
                "f_len": dsc_result["f_len"],
                "f_vocab": dsc_result["f_vocab"],
                "f_topic": dsc_result["f_topic"],
            },
        },
        "risk": {
            "level": risk_result["risk_level"],
            "confidence": risk_result["confidence"],
        },
        "snippets": snippets,
        "details": {
            "lexical": lex_result,
            "semantic": sem_result,
            "stylometric": sty_result,
            "fusion": fusion_result,
        },
        "metadata": {
            "use_layer4": use_layer4,
            "source_sentences": src_prep["num_sentences"],
            "suspect_sentences": sus_prep["num_sentences"],
            "source_tokens": src_prep["num_tokens"],
            "suspect_tokens": sus_prep["num_tokens"],
            "snippet_count": len(snippets),
            "used_cached_suspect_embedding": _sus_embedding is not None,
            "elapsed_seconds": elapsed,
        },
    }

    logger.info(
        "Pipeline complete: %s vs %s → %s (C=%.4f, T=%.4f, snippets=%d, cached_sus=%s) in %.3fs",
        source_id, suspect_id, risk_result["risk_level"],
        c_final, t_cal, len(snippets), _sus_embedding is not None, elapsed,
    )
    return report


def run_full_comparison(
    project_id: str,
    project_text: str,
    compare_against: list[dict],
    use_layer4: bool = True,
) -> dict:
    """
    Compare one project against multiple suspect documents.
    OPTIMIZED: Pre-computes source preprocessing, embeddings, and POS tags once.
               Uses pre-computed suspect embeddings when available from database.
    """
    total_start = time.time()

    # ===== PRE-COMPUTE SOURCE DATA ONCE =====
    logger.info("Pre-computing source document data...")
    src_prep = preprocess(project_text)
    src_embeddings = _encode_sentences(src_prep["sentences"])
    src_pos = get_pos_tags(src_prep["normalized"]) if use_layer4 else None

    cached_count = sum(1 for s in compare_against if s.get("embedding"))
    logger.info(
        "Source pre-computed: %d sentences, %d tokens, embeddings shape=%s. "
        "Suspects: %d total, %d with pre-computed embeddings",
        src_prep["num_sentences"], src_prep["num_tokens"],
        src_embeddings.shape if len(src_embeddings) > 0 else "(empty)",
        len(compare_against), cached_count,
    )

    # ===== RUN PIPELINE FOR EACH SUSPECT =====
    comparisons = []
    highest_score = 0.0
    risk_priority = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
    highest_risk = "LOW"

    for i, suspect in enumerate(compare_against):
        logger.info(
            "Comparing %d/%d: %s (cached_embedding=%s)",
            i + 1, len(compare_against),
            suspect.get("title", suspect["id"]),
            bool(suspect.get("embedding")),
        )
        report = run_pipeline(
            source_id=project_id,
            source_text=project_text,
            suspect_id=suspect["id"],
            suspect_title=suspect.get("title", "Untitled"),
            suspect_text=suspect["text"],
            use_layer4=use_layer4,
            _src_prep=src_prep,
            _src_embeddings=src_embeddings,
            _src_pos=src_pos,
            _sus_embedding=suspect.get("embedding"),
        )
        comparisons.append(report)

        if report["scores"]["c_final"] > highest_score:
            highest_score = report["scores"]["c_final"]

        if risk_priority[report["risk"]["level"]] > risk_priority[highest_risk]:
            highest_risk = report["risk"]["level"]

    total_elapsed = round(time.time() - total_start, 3)
    logger.info(
        "Full comparison complete: %d documents in %.3fs",
        len(compare_against), total_elapsed,
    )

    return {
        "project_id": project_id,
        "comparisons": comparisons,
        "highest_risk": highest_risk,
        "highest_score": round(highest_score, 6),
        "total_comparisons": len(comparisons),
        "total_elapsed_seconds": total_elapsed,
    }


# ========================== TEST BLOCK ====================================
if __name__ == "__main__":
    import json

    logging.basicConfig(level=logging.INFO)

    print("=" * 65)
    print("HPCM M8 — Optimized Pipeline Test")
    print("=" * 65)

    source_text = """
    Natural language processing (NLP) is a subfield of linguistics, computer
    science, and artificial intelligence concerned with the interactions between
    computers and human language. The goal is to enable computers to understand,
    interpret, and generate human language in a valuable way. NLP combines
    computational linguistics with statistical, machine learning, and deep
    learning models to process human language.
    """

    suspects = [
        {
            "id": "doc_paraphrase",
            "title": "NLP Overview (paraphrased)",
            "text": """
            NLP, a branch of AI, focuses on the interaction between computers
            and human languages. It aims to help machines understand and produce
            natural language that is meaningful and useful. The field brings
            together ideas from linguistics and machine learning to analyze
            and generate text.
            """,
        },
        {
            "id": "doc_different",
            "title": "Photosynthesis Article",
            "text": """
            Photosynthesis is the process used by plants to convert light
            energy into chemical energy that can be stored and later released
            to fuel the plant's activities. This process occurs primarily in
            the leaves of the plant using chlorophyll pigments.
            """,
        },
        {
            "id": "doc_copy",
            "title": "Exact Copy",
            "text": source_text,
        },
    ]

    result = run_full_comparison(
        project_id="proj_001",
        project_text=source_text,
        compare_against=suspects,
        use_layer4=True,
    )

    print(f"\n  Total time: {result['total_elapsed_seconds']}s")
    print(f"  Comparisons: {result['total_comparisons']}")

    for comp in result["comparisons"]:
        risk = comp["risk"]["level"]
        c = comp["scores"]["c_final"]
        title = comp["suspect_title"]
        t = comp["metadata"]["elapsed_seconds"]
        snips = len(comp["snippets"])
        cached = comp["metadata"]["used_cached_suspect_embedding"]

        print(f"\n  [{risk:6s}] {title}")
        print(f"           C_final={c:.4f}  Time={t}s  Snippets={snips}  Cached={cached}")

    print(f"\n{'=' * 65}")
    print("M8 pipeline.py (optimized) — TEST COMPLETE")
    print("=" * 65)