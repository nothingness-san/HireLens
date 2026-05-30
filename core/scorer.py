"""
core/scorer.py
Composite ATS scoring engine.
Combines all scoring components into a single weighted score.
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod

from models.job import JobDescription
from models.resume import Resume
from models.result import AnalysisResult, GapAnalysis, ScoreBreakdown
from utils.config import WEIGHTS
from core.nlp_engine import (
    compute_keyword_match_score,
    compute_semantic_similarity,
    compute_skill_match_score,
    compute_experience_score,
    compute_education_score,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Abstract base — Strategy Pattern
# ---------------------------------------------------------------------------

class BaseScorer(ABC):
    """
    Abstract base class for all scoring strategies.
    Concrete scorers must implement the score() method.
    """

    @abstractmethod
    def score(self, resume: Resume, job: JobDescription) -> AnalysisResult:
        """Score a resume against a job description."""
        ...


# ---------------------------------------------------------------------------
# Default composite scorer
# ---------------------------------------------------------------------------

class CompositeScorer(BaseScorer):
    """
    Default ATS scorer. Computes five sub-scores and combines
    them using configurable weights from utils/config.py.

    Sub-scores:
        1. Keyword match      - TF-IDF keyword overlap
        2. Semantic similarity - sentence embedding cosine similarity
        3. Skill match        - direct skill set comparison
        4. Experience         - years of experience vs requirement
        5. Education          - degree level vs requirement
    """

    def score(self, resume: Resume, job: JobDescription) -> AnalysisResult:
        start = time.perf_counter()

        resume_text = resume.get_full_text()
        jd_text     = job.get_full_text()

        # --- 1. Keyword match ---
        kw_score, matched_kw, missing_kw = compute_keyword_match_score(
            resume_text, job.keywords
        )

        # --- 2. Semantic similarity ---
        sem_score = compute_semantic_similarity(resume_text, jd_text)

        # --- 3. Skill match ---
        skill_score, matched_skills, missing_skills = compute_skill_match_score(
            resume.skills, job.all_skills
        )

        # --- 4. Experience ---
        exp_score, exp_gap = compute_experience_score(
            resume.total_experience_years,
            job.min_experience_years,
        )

        # --- 5. Education ---
        edu_score, edu_gap = compute_education_score(
            resume.highest_degree,
            job.required_education,
        )

        # --- Composite score (0-100) ---
        composite = (
            kw_score    * WEIGHTS.keyword_match
            + sem_score * WEIGHTS.semantic_similarity
            + skill_score * WEIGHTS.skills
            + exp_score * WEIGHTS.experience
            + edu_score * WEIGHTS.education
        ) * 100

        elapsed_ms = (time.perf_counter() - start) * 1000

        return AnalysisResult(
            candidate_name = resume.candidate_name,
            file_name      = resume.file_name,
            job_title      = job.job_title,
            composite_score = round(composite, 2),
            score_breakdown = ScoreBreakdown(
                keyword_match       = round(kw_score,    4),
                semantic_similarity = round(sem_score,   4),
                skills              = round(skill_score, 4),
                experience          = round(exp_score,   4),
                education           = round(edu_score,   4),
            ),
            gap_analysis = GapAnalysis(
                missing_skills   = missing_skills,
                missing_keywords = missing_kw,
                matched_skills   = matched_skills,
                matched_keywords = matched_kw,
                experience_gap   = exp_gap,
                education_gap    = edu_gap,
            ),
            processing_time_ms = round(elapsed_ms, 2),
        )


# ---------------------------------------------------------------------------
# Scorer factory
# ---------------------------------------------------------------------------

_SCORER_REGISTRY: dict[str, type[BaseScorer]] = {
    "composite": CompositeScorer,
}


def get_scorer(name: str = "composite") -> BaseScorer:
    """
    Return a scorer instance by name.
    Defaults to CompositeScorer.
    """
    cls = _SCORER_REGISTRY.get(name)
    if cls is None:
        raise ValueError(
            f"Unknown scorer '{name}'. "
            f"Available: {list(_SCORER_REGISTRY.keys())}"
        )
    return cls()


def register_scorer(name: str, cls: type[BaseScorer]) -> None:
    """Register a custom scorer strategy."""
    _SCORER_REGISTRY[name] = cls
