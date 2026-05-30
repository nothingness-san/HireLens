"""
models/result.py
Pydantic data models for ATS scoring and analysis results.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ScoreBreakdown(BaseModel):
    """
    Detailed breakdown of each scoring component.
    All scores are in the range 0.0 to 1.0.
    """
    keyword_match:       float = 0.0
    semantic_similarity: float = 0.0
    skills:              float = 0.0
    experience:          float = 0.0
    education:           float = 0.0

    def to_percentage_dict(self) -> dict[str, float]:
        """Returns scores scaled to 0-100 for display."""
        return {k: round(v * 100, 2) for k, v in self.model_dump().items()}


class GapAnalysis(BaseModel):
    """
    Identifies what a resume is missing relative to a job description.
    """
    missing_skills:      list[str] = Field(default_factory=list)
    missing_keywords:    list[str] = Field(default_factory=list)
    experience_gap:      Optional[float] = None   # years short, if any
    education_gap:       Optional[str]   = None   # e.g. "Bachelor's required"
    matched_skills:      list[str] = Field(default_factory=list)
    matched_keywords:    list[str] = Field(default_factory=list)

    @property
    def skill_match_rate(self) -> float:
        """Ratio of matched to total required skills."""
        total = len(self.matched_skills) + len(self.missing_skills)
        if total == 0:
            return 0.0
        return len(self.matched_skills) / total


class AnalysisResult(BaseModel):
    """
    Complete analysis result for one resume against one job description.
    """

    # --- Identity ---
    candidate_name: str  = ""
    file_name:      str  = ""
    job_title:      str  = ""

    # --- Scores ---
    composite_score:  float         = 0.0   # 0.0 to 100.0
    score_breakdown:  ScoreBreakdown = Field(default_factory=ScoreBreakdown)

    # --- Gap Analysis ---
    gap_analysis: GapAnalysis = Field(default_factory=GapAnalysis)

    # --- Metadata ---
    analyzed_at: datetime = Field(default_factory=datetime.now)
    processing_time_ms: Optional[float] = None

    @property
    def grade(self) -> str:
        """Letter grade based on composite score."""
        score = self.composite_score
        if score >= 85:
            return "A"
        elif score >= 70:
            return "B"
        elif score >= 55:
            return "C"
        elif score >= 40:
            return "D"
        else:
            return "F"

    @property
    def recommendation(self) -> str:
        """Plain-language hiring recommendation."""
        score = self.composite_score
        if score >= 85:
            return "Strong match - recommend for interview"
        elif score >= 70:
            return "Good match - worth considering"
        elif score >= 55:
            return "Partial match - review manually"
        elif score >= 40:
            return "Weak match - significant gaps present"
        else:
            return "Poor match - does not meet requirements"

    def to_report_dict(self) -> dict:
        """Full dict representation for JSON/PDF reports."""
        return {
            "candidate_name":    self.candidate_name,
            "file_name":         self.file_name,
            "job_title":         self.job_title,
            "composite_score":   round(self.composite_score, 2),
            "grade":             self.grade,
            "recommendation":    self.recommendation,
            "score_breakdown":   self.score_breakdown.to_percentage_dict(),
            "gap_analysis": {
                "missing_skills":   self.gap_analysis.missing_skills,
                "missing_keywords": self.gap_analysis.missing_keywords,
                "matched_skills":   self.gap_analysis.matched_skills,
                "experience_gap":   self.gap_analysis.experience_gap,
                "education_gap":    self.gap_analysis.education_gap,
                "skill_match_rate": round(self.gap_analysis.skill_match_rate * 100, 2),
            },
            "analyzed_at":       self.analyzed_at.isoformat(),
        }


class RankingResult(BaseModel):
    """
    Ranked list of candidates for a single job description.
    """
    job_title:   str  = ""
    job_file:    str  = ""
    total_resumes_analyzed: int = 0
    ranked_candidates: list[AnalysisResult] = Field(default_factory=list)
    analyzed_at: datetime = Field(default_factory=datetime.now)

    @property
    def top_candidate(self) -> Optional[AnalysisResult]:
        if not self.ranked_candidates:
            return None
        return self.ranked_candidates[0]

    def to_report_dict(self) -> dict:
        return {
            "job_title":               self.job_title,
            "job_file":                self.job_file,
            "total_resumes_analyzed":  self.total_resumes_analyzed,
            "analyzed_at":             self.analyzed_at.isoformat(),
            "ranked_candidates": [
                c.to_report_dict() for c in self.ranked_candidates
            ],
        }
