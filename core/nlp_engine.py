"""
core/nlp_engine.py
NLP processing pipeline for HireLens.
Handles TF-IDF vectorization, semantic similarity,
keyword extraction, and job description enrichment.
"""

from __future__ import annotations

import logging
import re
from functools import lru_cache

import numpy as np
import spacy
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from models.job import JobDescription
from utils.config import DEGREE_HIERARCHY, SENTENCE_TRANSFORMER_MODEL, SPACY_MODEL
from utils.text_cleaner import clean_text, preprocess_for_nlp
from core.extractor import (
    extract_skills,
    extract_highest_degree,
    extract_total_experience,
)

logger = logging.getLogger(__name__)

_nlp = spacy.load(SPACY_MODEL)

# ---------------------------------------------------------------------------
# Job title extraction patterns
# ---------------------------------------------------------------------------

_TITLE_PREFIX_RE = re.compile(
    r"(?i)^(?:position|role|job\s*title|title|job|posting|opening|vacancy)\s*[:\-]\s*"
)

_TITLE_SKIP_RE = re.compile(
    r"(?i)^(?:job\s*description|job\s*posting|position\s*description|"
    r"role\s*description|about\s*the\s*role|about\s*the\s*position|"
    r"we\s*are\s*(?:looking|hiring)|overview|introduction|company\s*overview)\b"
)

_TITLE_HINT_WORDS: frozenset[str] = frozenset({
    "engineer", "developer", "analyst", "manager", "designer",
    "architect", "consultant", "specialist", "lead", "director",
    "scientist", "administrator", "coordinator", "officer", "head",
    "intern", "associate", "executive", "programmer", "technician",
    "supervisor", "president", "chief", "senior", "junior", "staff",
})


# ---------------------------------------------------------------------------
# Sentence transformer
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _get_transformer() -> SentenceTransformer:
    logger.info("Loading sentence transformer: %s", SENTENCE_TRANSFORMER_MODEL)
    return SentenceTransformer(SENTENCE_TRANSFORMER_MODEL)


# ---------------------------------------------------------------------------
# Keyword extraction
# ---------------------------------------------------------------------------

def extract_keywords_tfidf(
    text: str,
    top_n: int = 40,
    reference_corpus: list[str] | None = None,
) -> list[str]:
    """Extract top-N keywords using TF-IDF."""
    cleaned = clean_text(text, aggressive=True)
    corpus  = reference_corpus + [cleaned] if reference_corpus else [cleaned]

    vectorizer = TfidfVectorizer(
        max_features = 500,
        ngram_range  = (1, 2),
        stop_words   = "english",
        min_df       = 1,
    )
    tfidf_matrix  = vectorizer.fit_transform(corpus)
    feature_names = vectorizer.get_feature_names_out()
    scores        = tfidf_matrix[-1].toarray().flatten()
    top_indices   = scores.argsort()[::-1][:top_n]

    return [feature_names[i] for i in top_indices if scores[i] > 0]


# ---------------------------------------------------------------------------
# Semantic similarity
# ---------------------------------------------------------------------------

def compute_semantic_similarity(text_a: str, text_b: str) -> float:
    """Cosine similarity between two texts using sentence embeddings."""
    model      = _get_transformer()
    embeddings = model.encode([text_a[:5000], text_b[:5000]], convert_to_numpy=True)
    similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
    return float(np.clip(similarity, 0.0, 1.0))


# ---------------------------------------------------------------------------
# Keyword match score
# ---------------------------------------------------------------------------

def compute_keyword_match_score(
    resume_text: str,
    jd_keywords: list[str],
) -> tuple[float, list[str], list[str]]:
    """
    Compute keyword overlap between resume and JD keywords.
    Uses direct regex matching first, then lemmatized token fallback.
    """
    if not jd_keywords:
        return 0.0, [], []

    resume_lower  = resume_text.lower()
    resume_tokens = set(preprocess_for_nlp(resume_text))

    matched: list[str] = []
    missing: list[str] = []

    for kw in jd_keywords:
        kw_lower = kw.lower()

        # Direct word-boundary match
        if re.search(r"\b" + re.escape(kw_lower) + r"\b", resume_lower):
            matched.append(kw)
            continue

        # Lemmatized token subset match
        kw_tokens = set(preprocess_for_nlp(kw))
        if kw_tokens and kw_tokens.issubset(resume_tokens):
            matched.append(kw)
            continue

        missing.append(kw)

    score = len(matched) / len(jd_keywords)
    return float(score), matched, missing


# ---------------------------------------------------------------------------
# Skill match score
# ---------------------------------------------------------------------------

def compute_skill_match_score(
    resume_skills: list[str],
    jd_skills: list[str],
) -> tuple[float, list[str], list[str]]:
    """Compare resume skills against JD required skills."""
    if not jd_skills:
        return 0.0, [], []

    resume_set = {s.lower() for s in resume_skills}
    jd_set     = {s.lower() for s in jd_skills}
    matched    = sorted(resume_set & jd_set)
    missing    = sorted(jd_set - resume_set)
    score      = len(matched) / len(jd_set)
    return float(score), matched, missing


# ---------------------------------------------------------------------------
# Experience score
# ---------------------------------------------------------------------------

def compute_experience_score(
    candidate_years: float,
    required_years:  float | None,
) -> tuple[float, float | None]:
    if required_years is None or required_years <= 0:
        return 1.0, None
    if candidate_years >= required_years:
        return 1.0, round(candidate_years - required_years, 1)
    return float(np.clip(candidate_years / required_years, 0.0, 1.0)), round(
        required_years - candidate_years, 1
    )


# ---------------------------------------------------------------------------
# Education score
# ---------------------------------------------------------------------------

def compute_education_score(
    candidate_degree: str,
    required_degree:  str,
) -> tuple[float, str | None]:
    if not required_degree:
        return 1.0, None

    def degree_index(degree: str) -> int:
        dl = degree.lower()
        for i, d in enumerate(DEGREE_HIERARCHY):
            if d in dl:
                return i
        return -1

    c_idx = degree_index(candidate_degree)
    r_idx = degree_index(required_degree)

    if r_idx == -1:
        return 1.0, None
    if c_idx >= r_idx:
        return 1.0, None

    gap = f"{required_degree.capitalize()} degree required"
    if c_idx == -1:
        return 0.0, gap

    return float(np.clip(c_idx / r_idx, 0.0, 1.0)), gap


# ---------------------------------------------------------------------------
# Job title extraction
# ---------------------------------------------------------------------------

def _extract_job_title(full_text: str) -> str:
    """
    Extract job title from job description text.

    Strategy:
        1. Scan first 25 lines; for lines with a known prefix like
           'Position:' or 'Role:', strip the prefix and check for
           title hint words.
        2. Check for lines with title hint words and no skip pattern.
        3. Fall back to the first non-skip line after stripping any prefix.
    """
    lines = [ln.strip() for ln in full_text.splitlines() if ln.strip()]

    # Pass 1: lines with hint words (with or without prefix)
    for line in lines[:25]:
        if _TITLE_SKIP_RE.match(line):
            continue
        cleaned = _TITLE_PREFIX_RE.sub("", line).strip()
        if cleaned and any(w in cleaned.lower() for w in _TITLE_HINT_WORDS):
            return cleaned

    # Pass 2: any line that has a known prefix — take what follows it
    for line in lines[:25]:
        if _TITLE_PREFIX_RE.match(line):
            remainder = _TITLE_PREFIX_RE.sub("", line).strip()
            if remainder:
                return remainder

    # Pass 3: first line that is not a skip pattern
    for line in lines[:10]:
        if not _TITLE_SKIP_RE.match(line):
            return _TITLE_PREFIX_RE.sub("", line).strip()

    return ""


# ---------------------------------------------------------------------------
# Job description enrichment
# ---------------------------------------------------------------------------

def enrich_job_description(
    raw_text:  str,
    file_path: str = "",
    file_name: str = "",
    sections:  dict[str, str] | None = None,
) -> JobDescription:
    """Parse raw JD text into a structured JobDescription model."""
    sections  = sections or {}
    full_text = raw_text

    # Company via NER
    doc     = _nlp(full_text[:1000])
    company = next(
        (ent.text for ent in doc.ents if ent.label_ == "ORG"), ""
    )

    job_title       = _extract_job_title(full_text)
    required_skills = extract_skills(full_text)
    keywords        = extract_keywords_tfidf(full_text, top_n=40)
    min_exp         = extract_total_experience(full_text)
    required_edu    = extract_highest_degree(full_text)

    return JobDescription(
        file_path            = file_path,
        file_name            = file_name,
        raw_text             = raw_text,
        sections             = sections,
        job_title            = job_title,
        company              = company,
        required_skills      = required_skills,
        keywords             = keywords,
        min_experience_years = min_exp if min_exp > 0 else None,
        required_education   = required_edu,
    )
