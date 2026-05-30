"""
core/ranker.py
Batch processing and candidate ranking engine.
Scores multiple resumes against a job description
and returns a sorted RankingResult.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Generator

from tqdm import tqdm

from models.job import JobDescription
from models.resume import Resume
from models.result import AnalysisResult, RankingResult
from utils.config import TOP_N_CANDIDATES
from core.extractor import enrich_resume
from core.nlp_engine import enrich_job_description
from core.parser import parse_resume, parse_job_description_text
from core.scorer import BaseScorer, get_scorer

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Resume generator — memory-efficient batch loading
# ---------------------------------------------------------------------------

def _resume_generator(
    resume_paths: list[Path],
) -> Generator[Resume, None, None]:
    """
    Yield parsed and enriched Resume objects one at a time.
    Using a generator avoids loading all resumes into memory at once.
    """
    for path in resume_paths:
        try:
            resume = parse_resume(path)
            resume = enrich_resume(resume)
            yield resume
        except Exception as e:
            logger.error("Failed to process resume %s: %s", path.name, e)
            continue


# ---------------------------------------------------------------------------
# Single resume scoring
# ---------------------------------------------------------------------------

def score_single(
    resume_path: Path | str,
    jd_path:     Path | str,
    scorer:      BaseScorer | None = None,
) -> AnalysisResult:
    """
    Score one resume against one job description.

    Args:
        resume_path - path to resume file
        jd_path     - path to job description file
        scorer      - scorer instance (defaults to CompositeScorer)

    Returns:
        AnalysisResult with full score breakdown and gap analysis
    """
    if scorer is None:
        scorer = get_scorer("composite")

    resume_path = Path(resume_path)
    jd_path     = Path(jd_path)

    # Parse and enrich resume
    resume = parse_resume(resume_path)
    resume = enrich_resume(resume)

    # Parse and enrich job description
    jd_data = parse_job_description_text(jd_path)
    job     = enrich_job_description(
        raw_text  = jd_data["raw_text"],
        file_path = str(jd_path),
        file_name = jd_path.name,
        sections  = jd_data["sections"],
    )

    return scorer.score(resume, job)


# ---------------------------------------------------------------------------
# Batch ranking
# ---------------------------------------------------------------------------

def rank_resumes(
    resume_dir:  Path | str,
    jd_path:     Path | str,
    scorer:      BaseScorer | None = None,
    top_n:       int | None = None,
) -> RankingResult:
    """
    Score all resumes in a directory against a job description
    and return a ranked RankingResult.

    Args:
        resume_dir  - directory containing resume files
        jd_path     - path to job description file
        scorer      - scorer instance (defaults to CompositeScorer)
        top_n       - limit results to top N candidates

    Returns:
        RankingResult with candidates sorted by composite score descending
    """
    from utils.config import SUPPORTED_EXTENSIONS

    if scorer is None:
        scorer = get_scorer("composite")

    resume_dir = Path(resume_dir)
    jd_path    = Path(jd_path)
    top_n      = top_n or TOP_N_CANDIDATES

    # Collect resume paths
    resume_paths = sorted([
        p for p in resume_dir.iterdir()
        if p.suffix.lower() in SUPPORTED_EXTENSIONS
    ])

    if not resume_paths:
        logger.warning("No supported resume files found in %s", resume_dir)
        return RankingResult(job_file=jd_path.name)

    # Parse and enrich job description once
    jd_data = parse_job_description_text(jd_path)
    job     = enrich_job_description(
        raw_text  = jd_data["raw_text"],
        file_path = str(jd_path),
        file_name = jd_path.name,
        sections  = jd_data["sections"],
    )

    logger.info(
        "Ranking %d resumes against: %s", len(resume_paths), jd_path.name
    )

    # Score all resumes
    results: list[AnalysisResult] = []

    for resume in tqdm(
        _resume_generator(resume_paths),
        total   = len(resume_paths),
        desc    = "Scoring resumes",
        unit    = "resume",
    ):
        try:
            result = scorer.score(resume, job)
            results.append(result)
        except Exception as e:
            logger.error("Scoring failed for %s: %s", resume.file_name, e)
            continue

    # Sort by composite score descending
    results.sort(key=lambda r: r.composite_score, reverse=True)

    return RankingResult(
        job_title               = job.job_title,
        job_file                = jd_path.name,
        total_resumes_analyzed  = len(results),
        ranked_candidates       = results[:top_n],
    )
