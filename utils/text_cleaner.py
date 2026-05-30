"""
utils/text_cleaner.py
Text preprocessing utilities for NLP pipeline.
"""

from __future__ import annotations

import re
import unicodedata
from functools import lru_cache

import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import word_tokenize

_lemmatizer = WordNetLemmatizer()

@lru_cache(maxsize=1)
def _get_stopwords() -> frozenset[str]:
    return frozenset(stopwords.words("english"))


# ---------------------------------------------------------------------------
# Basic cleaning
# ---------------------------------------------------------------------------

def normalize_whitespace(text: str) -> str:
    """Replace all whitespace sequences with a single space."""
    return re.sub(r"\s+", " ", text).strip()


def remove_special_characters(text: str, keep_punctuation: bool = False) -> str:
    """Remove non-alphanumeric characters optionally keeping punctuation."""
    if keep_punctuation:
        pattern = r"[^a-zA-Z0-9\s\.\,\!\?\-\(\)\@\+\#]"
    else:
        pattern = r"[^a-zA-Z0-9\s]"
    return re.sub(pattern, " ", text)


def normalize_unicode(text: str) -> str:
    """Normalize unicode characters to ASCII equivalents where possible."""
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")


def remove_urls(text: str) -> str:
    return re.sub(r"http\S+|www\.\S+", " ", text)


def remove_emails(text: str) -> str:
    return re.sub(r"\S+@\S+", " ", text)


def remove_phone_numbers(text: str) -> str:
    return re.sub(r"[\+\(]?[1-9][0-9\-\(\)\s]{8,}[0-9]", " ", text)


# ---------------------------------------------------------------------------
# NLP preprocessing
# ---------------------------------------------------------------------------

def tokenize(text: str) -> list[str]:
    """Tokenize text into a list of word tokens."""
    return word_tokenize(text.lower())


def remove_stopwords(tokens: list[str]) -> list[str]:
    """Remove English stopwords from a token list."""
    sw = _get_stopwords()
    return [t for t in tokens if t not in sw and t.isalpha()]


def lemmatize(tokens: list[str]) -> list[str]:
    """Lemmatize a list of tokens."""
    return [_lemmatizer.lemmatize(t) for t in tokens]


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def clean_text(text: str, aggressive: bool = False) -> str:
    """
    Standard cleaning pipeline.
    aggressive=True strips emails, URLs, and phone numbers as well.
    """
    text = normalize_unicode(text)
    if aggressive:
        text = remove_urls(text)
        text = remove_emails(text)
        text = remove_phone_numbers(text)
    text = remove_special_characters(text, keep_punctuation=not aggressive)
    text = normalize_whitespace(text)
    return text.lower()


def preprocess_for_nlp(text: str) -> list[str]:
    """
    Full NLP preprocessing pipeline.
    Returns lemmatized, stopword-free tokens.
    """
    cleaned = clean_text(text, aggressive=True)
    tokens  = tokenize(cleaned)
    tokens  = remove_stopwords(tokens)
    tokens  = lemmatize(tokens)
    return tokens


def tokens_to_text(tokens: list[str]) -> str:
    """Rejoin tokens into a single string."""
    return " ".join(tokens)
