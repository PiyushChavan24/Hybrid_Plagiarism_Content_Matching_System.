"""
M1 — preprocessing.py
HPCM Plagiarism Detection System
---------------------------------
Tokenize, lemmatize, remove stopwords.
Provides clean text for downstream modules (M2–M5).
"""

import re
import string
import logging

import nltk
import spacy

# ---------------------------------------------------------------------------
# One-time NLTK downloads (safe to call repeatedly — skips if present)
# ---------------------------------------------------------------------------
nltk.download("punkt", quiet=True)
nltk.download("punkt_tab", quiet=True)
nltk.download("stopwords", quiet=True)
nltk.download("wordnet", quiet=True)

from nltk.corpus import stopwords
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.stem import WordNetLemmatizer

# ---------------------------------------------------------------------------
# Logger
# ---------------------------------------------------------------------------
logger = logging.getLogger("hpcm.preprocessing")

# ---------------------------------------------------------------------------
# Load spaCy model (used for POS tagging in M4, loaded once here)
# ---------------------------------------------------------------------------
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    logger.warning(
        "spaCy model 'en_core_web_sm' not found. "
        "Run: python -m spacy download en_core_web_sm"
    )
    nlp = None

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
STOP_WORDS: set[str] = set(stopwords.words("english"))
lemmatizer = WordNetLemmatizer()


# =============================== core API =================================

def normalize_text(raw: str) -> str:
    """
    Light normalization applied before any NLP step:
    - collapse whitespace / newlines
    - strip non-ASCII control chars
    - lowercase
    """
    text = raw.strip()
    text = re.sub(r"[^\x20-\x7E\n]", " ", text)   # keep printable ASCII + newline
    text = re.sub(r"\s+", " ", text)                 # collapse whitespace
    return text.lower()


def tokenize_sentences(text: str) -> list[str]:
    """Split text into sentences using NLTK punkt."""
    return sent_tokenize(text)


def tokenize_words(text: str) -> list[str]:
    """Word-level tokenization with NLTK."""
    return word_tokenize(text)


def remove_stopwords(tokens: list[str]) -> list[str]:
    """Remove English stopwords and punctuation-only tokens."""
    return [
        t for t in tokens
        if t not in STOP_WORDS and t not in string.punctuation and len(t) > 1
    ]


def lemmatize_tokens(tokens: list[str]) -> list[str]:
    """Lemmatize each token using WordNet."""
    return [lemmatizer.lemmatize(t) for t in tokens]


def get_pos_tags(text: str) -> list[tuple[str, str]]:
    """
    Return (token, POS) pairs via spaCy.
    Used by M4 stylometric analysis.
    """
    if nlp is None:
        raise RuntimeError("spaCy model not loaded — cannot POS-tag.")
    doc = nlp(text)
    return [(token.text, token.pos_) for token in doc]


def preprocess(raw: str) -> dict:
    """
    Full preprocessing pipeline for one document.

    Returns
    -------
    dict with keys:
        normalized       — lowercased, whitespace-collapsed text
        sentences        — list[str]
        tokens           — list[str]  (all words, lowercased)
        clean_tokens     — list[str]  (stopwords + punct removed, lemmatized)
        clean_text       — str        (rejoined clean_tokens — input for TF-IDF)
        num_sentences    — int
        num_tokens       — int
        num_clean_tokens — int
    """
    normalized = normalize_text(raw)
    sentences = tokenize_sentences(normalized)
    tokens = tokenize_words(normalized)
    filtered = remove_stopwords(tokens)
    lemmas = lemmatize_tokens(filtered)

    result = {
        "normalized": normalized,
        "sentences": sentences,
        "tokens": tokens,
        "clean_tokens": lemmas,
        "clean_text": " ".join(lemmas),
        "num_sentences": len(sentences),
        "num_tokens": len(tokens),
        "num_clean_tokens": len(lemmas),
    }
    logger.debug(
        "Preprocessed: %d sentences, %d → %d tokens",
        result["num_sentences"],
        result["num_tokens"],
        result["num_clean_tokens"],
    )
    return result


# ========================== TEST BLOCK ====================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    sample_a = """
    Natural language processing (NLP) is a subfield of linguistics, computer
    science, and artificial intelligence concerned with the interactions between
    computers and human language. The goal is to enable computers to understand,
    interpret, and generate human language in a valuable way.
    """

    sample_b = """
    NLP, a branch of AI, focuses on the interaction between computers and
    human languages.  It aims to help machines understand and produce natural
    language that is meaningful and useful.
    """

    print("=" * 65)
    print("HPCM M1 — Preprocessing Module Test")
    print("=" * 65)

    for label, text in [("Document A", sample_a), ("Document B", sample_b)]:
        result = preprocess(text)
        print(f"\n--- {label} ---")
        print(f"  Sentences     : {result['num_sentences']}")
        print(f"  Raw tokens    : {result['num_tokens']}")
        print(f"  Clean tokens  : {result['num_clean_tokens']}")
        print(f"  Sentences     : {result['sentences'][:2]}{'...' if len(result['sentences']) > 2 else ''}")
        print(f"  Clean tokens  : {result['clean_tokens'][:12]}...")
        print(f"  Clean text    : {result['clean_text'][:80]}...")

    # Quick POS test
    if nlp is not None:
        pos = get_pos_tags("The quick brown fox jumps over the lazy dog.")
        print(f"\n--- POS Tag Sample ---")
        print(f"  {pos}")
    else:
        print("\n  [SKIP] POS tagging — spaCy model not available.")

    print("\n" + "=" * 65)
    print("M1 preprocessing.py — ALL CHECKS PASSED")
    print("=" * 65)