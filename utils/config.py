"""
utils/config.py
Central configuration and constants for HireLens.
Loads values from .env with sensible defaults.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

BASE_DIR   = Path(__file__).resolve().parent.parent
DATA_DIR   = BASE_DIR / "data"
RESUME_DIR = DATA_DIR / os.getenv("RESUME_DIR", "data/resumes").split("/")[-1]
JD_DIR     = DATA_DIR / os.getenv("JD_DIR", "data/job_descriptions").split("/")[-1]
OUTPUT_DIR = DATA_DIR / os.getenv("OUTPUT_DIR", "data/output").split("/")[-1]


# ---------------------------------------------------------------------------
# Supported file types
# ---------------------------------------------------------------------------

SUPPORTED_EXTENSIONS: frozenset[str] = frozenset({".pdf", ".docx", ".txt"})


# ---------------------------------------------------------------------------
# NLP model identifiers
# ---------------------------------------------------------------------------

SPACY_MODEL               = os.getenv("SPACY_MODEL", "en_core_web_md")
SENTENCE_TRANSFORMER_MODEL = os.getenv(
    "SENTENCE_TRANSFORMER_MODEL", "all-MiniLM-L6-v2"
)


# ---------------------------------------------------------------------------
# Scoring weights
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ScoringWeights:
    """
    Immutable container for ATS scoring weights.
    Validates that all weights sum to 1.0 on construction.
    """
    keyword_match:       float = float(os.getenv("WEIGHT_KEYWORD_MATCH",      0.30))
    semantic_similarity: float = float(os.getenv("WEIGHT_SEMANTIC_SIMILARITY", 0.30))
    skills:              float = float(os.getenv("WEIGHT_SKILLS",              0.20))
    experience:          float = float(os.getenv("WEIGHT_EXPERIENCE",          0.10))
    education:           float = float(os.getenv("WEIGHT_EDUCATION",           0.10))

    def __post_init__(self) -> None:
        total = round(
            self.keyword_match
            + self.semantic_similarity
            + self.skills
            + self.experience
            + self.education,
            10,
        )
        if abs(total - 1.0) > 1e-9:
            raise ValueError(
                f"Scoring weights must sum to 1.0, got {total}. "
                "Check your .env file."
            )

    def as_dict(self) -> dict[str, float]:
        return {
            "keyword_match":       self.keyword_match,
            "semantic_similarity": self.semantic_similarity,
            "skills":              self.skills,
            "experience":          self.experience,
            "education":           self.education,
        }


WEIGHTS = ScoringWeights()


# ---------------------------------------------------------------------------
# Report settings
# ---------------------------------------------------------------------------

REPORT_FORMAT    = os.getenv("REPORT_FORMAT", "both")      # json | pdf | both
TOP_N_CANDIDATES = int(os.getenv("TOP_N_CANDIDATES", 10))


# ---------------------------------------------------------------------------
# Section headers used by the parser to detect resume sections
# ---------------------------------------------------------------------------

SECTION_HEADERS: dict[str, list[str]] = {
    "summary": [
        "summary", "objective", "profile", "about", "about me",
        "professional summary", "career objective",
    ],
    "experience": [
        "experience", "work experience", "employment", "employment history",
        "work history", "professional experience", "career history",
    ],
    "education": [
        "education", "academic background", "qualifications",
        "academic qualifications", "educational background",
    ],
    "skills": [
        "skills", "technical skills", "core competencies", "competencies",
        "technologies", "tools", "tech stack", "expertise",
    ],
    "projects": [
        "projects", "personal projects", "academic projects",
        "key projects", "notable projects",
    ],
    "certifications": [
        "certifications", "certificates", "licenses", "accreditations",
    ],
    "languages": [
        "languages", "spoken languages",
    ],
}


# ---------------------------------------------------------------------------
# Experience scoring thresholds (in years)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ExperienceThresholds:
    entry:  int = 2
    mid:    int = 5
    senior: int = 10


EXPERIENCE_THRESHOLDS = ExperienceThresholds()


# ---------------------------------------------------------------------------
# Education degree hierarchy (higher index = higher qualification)
# ---------------------------------------------------------------------------

DEGREE_HIERARCHY: list[str] = [
    "high school",
    "associate",
    "bachelor",
    "undergraduate",
    "graduate",
    "master",
    "mba",
    "postgraduate",
    "phd",
    "doctorate",
]
