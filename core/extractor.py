"""
core/extractor.py
Extracts structured data from raw resume sections:
skills, education, experience, certifications, and languages.
"""

from __future__ import annotations

import logging
import re
from functools import lru_cache

import spacy

from models.resume import Education, Experience, Resume
from utils.config import (
    DEGREE_HIERARCHY,
    EXPERIENCE_THRESHOLDS,
    SPACY_MODEL,
)

logger = logging.getLogger(__name__)

_nlp = spacy.load(SPACY_MODEL)


# ---------------------------------------------------------------------------
# Skill extraction
# ---------------------------------------------------------------------------

SKILL_PATTERNS: frozenset[str] = frozenset({
    # Programming languages
    "python", "java", "javascript", "typescript", "c++", "c#", "go", "rust",
    "kotlin", "swift", "ruby", "php", "scala", "r", "matlab", "bash", "shell",
    # Web
    "html", "css", "react", "angular", "vue", "node.js", "django", "flask",
    "fastapi", "spring", "express", "nextjs", "tailwind",
    # Data / ML
    "machine learning", "deep learning", "nlp", "computer vision",
    "tensorflow", "pytorch", "keras", "scikit-learn", "pandas", "numpy",
    "matplotlib", "seaborn", "huggingface", "transformers",
    # Databases
    "sql", "mysql", "postgresql", "mongodb", "redis", "elasticsearch",
    "sqlite", "oracle", "cassandra", "dynamodb",
    # Cloud / DevOps
    "aws", "azure", "gcp", "docker", "kubernetes", "terraform", "ansible",
    "jenkins", "github actions", "ci/cd", "linux", "git",
    # Data engineering
    "spark", "hadoop", "kafka", "airflow", "dbt", "snowflake", "bigquery",
    # Soft skills
    "communication", "teamwork", "leadership", "problem solving",
    "project management", "agile", "scrum",
})


def extract_skills(text: str, custom_skills: list[str] | None = None) -> list[str]:
    """
    Extract skills from text by matching against the skill pattern set.
    Optionally extend with custom skills from the job description.
    """
    text_lower = text.lower()
    skill_set  = SKILL_PATTERNS.copy()

    if custom_skills:
        skill_set = skill_set | {s.lower() for s in custom_skills}

    found: list[str] = []
    for skill in sorted(skill_set):
        pattern = r"\b" + re.escape(skill) + r"\b"
        if re.search(pattern, text_lower):
            found.append(skill)

    return sorted(set(found))


# ---------------------------------------------------------------------------
# Experience extraction
# ---------------------------------------------------------------------------

_YEAR_RE    = re.compile(r"\b(19|20)\d{2}\b")
_PRESENT_RE = re.compile(r"\b(present|current|now|till date|to date)\b", re.IGNORECASE)
_DURATION_RE = re.compile(
    r"(\d+)\+?\s*years?\s*(?:of\s*)?(?:experience|exp)?", re.IGNORECASE
)


def _extract_years_from_text(text: str) -> list[int]:
    return [int(y) for y in _YEAR_RE.findall(text)]


def extract_total_experience(text: str) -> float:
    """
    Estimate total years of experience from resume text.

    Strategy:
        1. Look for explicit "X years of experience" statements.
        2. Fall back to summing durations between year pairs in the text.
    """
    # Strategy 1 — explicit duration statement
    match = _DURATION_RE.search(text)
    if match:
        return float(match.group(1))

    # Strategy 2 — year range inference
    years = sorted(set(_extract_years_from_text(text)))
    has_present = bool(_PRESENT_RE.search(text))

    if not years:
        return 0.0

    import datetime
    current_year = datetime.datetime.now().year

    if has_present and years:
        total = current_year - years[0]
        return max(0.0, float(total))

    if len(years) >= 2:
        total = years[-1] - years[0]
        return max(0.0, float(total))

    return 0.0


def extract_experience_entries(text: str) -> list[Experience]:
    """
    Parse individual experience entries from the experience section text.
    Uses spaCy NER to identify organisations and dates.
    """
    entries: list[Experience] = []
    doc = _nlp(text[:5000])   # limit for performance

    current_org   = ""
    current_years = []

    for ent in doc.ents:
        if ent.label_ == "ORG":
            if current_org:
                entry = Experience(
                    company  = current_org,
                    raw_text = current_org,
                )
                if len(current_years) >= 2:
                    entry = Experience(
                        company    = current_org,
                        start_year = current_years[0],
                        end_year   = current_years[-1],
                        raw_text   = current_org,
                    )
                entries.append(entry)
            current_org   = ent.text
            current_years = []

        elif ent.label_ == "DATE":
            years = _extract_years_from_text(ent.text)
            current_years.extend(years)

    # Flush last entry
    if current_org:
        entry = Experience(company=current_org, raw_text=current_org)
        if len(current_years) >= 2:
            entry = Experience(
                company    = current_org,
                start_year = current_years[0],
                end_year   = current_years[-1],
                raw_text   = current_org,
            )
        entries.append(entry)

    return entries


# ---------------------------------------------------------------------------
# Education extraction
# ---------------------------------------------------------------------------

_DEGREE_RE = re.compile(
    r"\b(bachelor|master|phd|doctorate|associate|mba|b\.?sc|m\.?sc"
    r"|b\.?tech|m\.?tech|b\.?e|m\.?e|undergraduate|graduate|postgraduate"
    r"|high school|diploma)\b",
    re.IGNORECASE,
)


def extract_education_entries(text: str) -> list[Education]:
    """
    Parse education entries from the education section text.
    Uses regex for degree detection and spaCy NER for institution names.
    """
    entries: list[Education] = []
    doc = _nlp(text[:3000])

    orgs  = [e.text for e in doc.ents if e.label_ == "ORG"]
    years = sorted(_extract_years_from_text(text))

    degree_matches = _DEGREE_RE.findall(text)

    if not degree_matches and not orgs:
        return entries

    # Pair up degrees with institutions as best we can
    max_entries = max(len(degree_matches), len(orgs), 1)
    for i in range(max_entries):
        degree      = degree_matches[i] if i < len(degree_matches) else ""
        institution = orgs[i]           if i < len(orgs)           else ""
        start_year  = years[0]          if len(years) > 1          else None
        end_year    = years[-1]         if len(years) > 0          else None

        entries.append(Education(
            institution = institution,
            degree      = degree,
            start_year  = start_year,
            end_year    = end_year,
            raw_text    = text[:200],
        ))

    return entries


def extract_highest_degree(text: str) -> str:
    """
    Return the highest academic degree found in text,
    ranked by DEGREE_HIERARCHY.
    """
    text_lower    = text.lower()
    highest_index = -1
    highest_degree = ""

    for degree in DEGREE_HIERARCHY:
        if re.search(r"\b" + re.escape(degree) + r"\b", text_lower):
            idx = DEGREE_HIERARCHY.index(degree)
            if idx > highest_index:
                highest_index  = idx
                highest_degree = degree

    return highest_degree


# ---------------------------------------------------------------------------
# Certifications and languages
# ---------------------------------------------------------------------------

_CERT_KEYWORDS = re.compile(
    r"\b(certified|certification|certificate|license|accreditation|AWS|GCP|Azure"
    r"|PMP|CISSP|CPA|CFA|CompTIA|Oracle|Microsoft|Google|Scrum|ITIL)\b",
    re.IGNORECASE,
)


def extract_certifications(text: str) -> list[str]:
    """Extract certification mentions from text."""
    lines = text.splitlines()
    certs = []
    for line in lines:
        line = line.strip()
        if line and _CERT_KEYWORDS.search(line):
            certs.append(line)
    return certs[:10]   # cap at 10


def extract_languages(text: str) -> list[str]:
    """Extract spoken languages from the languages section."""
    common_languages = [
        "english", "spanish", "french", "german", "mandarin", "chinese",
        "hindi", "arabic", "portuguese", "japanese", "korean", "italian",
        "russian", "dutch", "turkish", "polish", "swedish",
    ]
    text_lower = text.lower()
    return [lang.capitalize() for lang in common_languages if lang in text_lower]


# ---------------------------------------------------------------------------
# Top-level enrichment
# ---------------------------------------------------------------------------

def enrich_resume(resume: Resume) -> Resume:
    """
    Run all extractors on a parsed Resume and populate structured fields.
    Returns the same Resume object with fields filled in.
    """
    full_text = resume.get_full_text()

    # Skills
    resume.skills = extract_skills(full_text)

    # Experience
    exp_text = resume.sections.get("experience", full_text)
    resume.experience = extract_experience_entries(exp_text)
    resume.total_experience_years = extract_total_experience(exp_text)

    # Education
    edu_text = resume.sections.get("education", full_text)
    resume.education      = extract_education_entries(edu_text)
    resume.highest_degree = extract_highest_degree(edu_text)

    # Certifications
    cert_text = resume.sections.get("certifications", full_text)
    resume.certifications = extract_certifications(cert_text)

    # Languages
    lang_text = resume.sections.get("languages", full_text)
    resume.languages = extract_languages(lang_text)

    return resume
