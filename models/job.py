"""
models/job.py
Pydantic data model representing a parsed job description.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class JobDescription(BaseModel):
    """
    Structured representation of a job description.
    Holds both raw text and extracted structured fields
    that the scoring engine compares against resumes.
    """

    # --- Source ---
    file_path:  Path  = Field(default=Path("."))
    file_name:  str   = ""
    raw_text:   str   = ""

    # --- Job Info ---
    job_title:   str  = ""
    company:     str  = ""
    location:    str  = ""

    # --- Requirements (extracted) ---
    required_skills:    list[str] = Field(default_factory=list)
    preferred_skills:   list[str] = Field(default_factory=list)
    required_education: str       = ""
    min_experience_years: Optional[float] = None

    # --- Keywords (extracted for matching) ---
    keywords: list[str] = Field(default_factory=list)

    # --- Raw section text ---
    sections: dict[str, str] = Field(default_factory=dict)

    @field_validator("file_path", mode="before")
    @classmethod
    def coerce_path(cls, v: object) -> Path:
        return Path(str(v))

    @property
    def all_skills(self) -> list[str]:
        """Combined required and preferred skills, deduplicated."""
        seen = set()
        result = []
        for skill in self.required_skills + self.preferred_skills:
            if skill.lower() not in seen:
                seen.add(skill.lower())
                result.append(skill)
        return result

    def get_full_text(self) -> str:
        """
        Returns the full raw text of the job description.
        Falls back to joining all section texts if raw_text is empty.
        """
        if self.raw_text:
            return self.raw_text
        return " ".join(self.sections.values())

    def to_summary_dict(self) -> dict:
        """Returns a lightweight dict for reporting purposes."""
        return {
            "file_name":             self.file_name,
            "job_title":             self.job_title,
            "company":               self.company,
            "required_skills_count": len(self.required_skills),
            "preferred_skills_count": len(self.preferred_skills),
            "min_experience_years":  self.min_experience_years,
            "required_education":    self.required_education,
            "keywords_count":        len(self.keywords),
        }

    class Config:
        arbitrary_types_allowed = True
