"""
core/parser.py
Segments raw resume text into labeled sections and extracts
basic contact information using regex and spaCy NER.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

import spacy

from models.resume import Resume
from utils.config import SECTION_HEADERS, SPACY_MODEL
from utils.file_handler import read_file
from utils.text_cleaner import normalize_whitespace

logger = logging.getLogger(__name__)

try:
    _nlp = spacy.load(SPACY_MODEL)
except OSError:
    logger.error("spaCy model '%s' not found. Run: python run_once_setup.py", SPACY_MODEL)
    raise


# ---------------------------------------------------------------------------
# Contact extraction
# ---------------------------------------------------------------------------

_EMAIL_RE    = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
_PHONE_RE    = re.compile(r"[\+\(]?[1-9][0-9\s\-\(\)\.]{7,}[0-9]")
_LINKEDIN_RE = re.compile(r"linkedin\.com/in/[a-zA-Z0-9\-_%]+", re.IGNORECASE)
_NAME_LABEL_RE = re.compile(
    r"(?i)^\s*(?:name|full\s*name|candidate\s*name|candidate)\s*[:\-]\s*(.+)$"
)


def _extract_email(text: str) -> str:
    match = _EMAIL_RE.search(text)
    return match.group(0) if match else ""


def _extract_phone(text: str) -> str:
    match = _PHONE_RE.search(text)
    return match.group(0).strip() if match else ""


def _extract_linkedin(text: str) -> str:
    match = _LINKEDIN_RE.search(text)
    return match.group(0) if match else ""


# ---------------------------------------------------------------------------
# Name extraction
# ---------------------------------------------------------------------------

_NON_NAME_TERMS: frozenset[str] = frozenset({
    "java", "python", "sql", "html", "css", "linux", "aws", "gcp",
    "azure", "git", "docker", "kubernetes", "react", "angular", "vue",
    "swift", "kotlin", "ruby", "scala", "rust", "go", "php",
    "summary", "objective", "profile", "experience", "education",
    "skills", "resume", "curriculum", "vitae", "references",
    "contact", "address", "email", "phone", "linkedin", "portfolio",
    "work", "employment", "history", "background", "technical",
    "overview", "introduction", "about",
})


def _looks_like_name(text: str) -> bool:
    """
    Returns True if text is plausibly a person's name:
      - 1 to 4 words
      - each word is alphanumeric (allows names like 'Candidate 1')
      - at least one alphabetic character present
      - not a known non-name term
    """
    text = text.strip()
    words = text.split()
    if not (1 <= len(words) <= 4):
        return False
    if not all(w.replace("-", "").isalnum() for w in words):
        return False
    if not any(c.isalpha() for c in text):
        return False
    if text.lower() in _NON_NAME_TERMS:
        return False
    if any(w.lower() in _NON_NAME_TERMS for w in words):
        return False
    return True


def _extract_name(text: str) -> str:
    """
    Extract candidate name from resume text.

    Strategy:
        1. Look for an explicit 'Name: ...' label in the first 30 lines.
        2. Scan the first 30 lines for a line that passes _looks_like_name.
        3. Fall back to spaCy PERSON entities filtered against
           known non-name terms.
    """
    lines = [ln.strip() for ln in text.splitlines()]

    # Strategy 1: explicit label e.g. "Name: John Doe" or "Candidate: Jane"
    for line in lines[:30]:
        match = _NAME_LABEL_RE.match(line)
        if match:
            candidate = match.group(1).strip()
            if _looks_like_name(candidate):
                return candidate

    # Strategy 2: first short clean line that looks like a name
    for line in lines[:30]:
        if line and _looks_like_name(line):
            return line

    # Strategy 3: spaCy NER with non-name filtering
    doc = _nlp(text[:600])
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            candidate = ent.text.strip()
            if _looks_like_name(candidate):
                return candidate

    return ""


# ---------------------------------------------------------------------------
# Section segmentation
# ---------------------------------------------------------------------------

def _build_header_pattern() -> re.Pattern:
    all_headers: list[str] = []
    for headers in SECTION_HEADERS.values():
        all_headers.extend(headers)
    escaped = [re.escape(h) for h in sorted(all_headers, key=len, reverse=True)]
    pattern = r"(?im)^[ \t]*(" + "|".join(escaped) + r")[ \t]*[:\-]?[ \t]*$"
    return re.compile(pattern)


_HEADER_RE = _build_header_pattern()


def _identify_section(header_text: str) -> str:
    header_lower = header_text.strip().lower()
    for section_name, aliases in SECTION_HEADERS.items():
        if header_lower in aliases:
            return section_name
    return header_lower


def segment_sections(text: str) -> dict[str, str]:
    """Split raw resume text into labeled sections."""
    sections: dict[str, str] = {}
    lines = text.splitlines()
    current_section = "header"
    buffer: list[str] = []

    for line in lines:
        match = _HEADER_RE.match(line.strip())
        if match:
            if buffer:
                content = normalize_whitespace("\n".join(buffer))
                if content:
                    sections[current_section] = (
                        sections.get(current_section, "") + " " + content
                    )
            current_section = _identify_section(match.group(1))
            buffer = []
        else:
            buffer.append(line)

    if buffer:
        content = normalize_whitespace("\n".join(buffer))
        if content:
            sections[current_section] = (
                sections.get(current_section, "") + " " + content
            )

    return {k: v.strip() for k, v in sections.items() if v.strip()}


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def parse_resume(file_path: Path | str) -> Resume:
    """Parse a resume file into a structured Resume object."""
    file_path = Path(file_path)
    raw_text  = read_file(file_path)

    return Resume(
        file_path      = file_path,
        file_name      = file_path.name,
        raw_text       = raw_text,
        candidate_name = _extract_name(raw_text),
        email          = _extract_email(raw_text),
        phone          = _extract_phone(raw_text),
        linkedin       = _extract_linkedin(raw_text),
        sections       = segment_sections(raw_text),
    )


def parse_job_description_text(file_path: Path | str) -> dict[str, str]:
    """Read and segment a job description file into sections."""
    file_path = Path(file_path)
    raw_text  = read_file(file_path)
    return {"raw_text": raw_text, "sections": segment_sections(raw_text)}
