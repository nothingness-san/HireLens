"""
models/resume.py
Pydantic data model representing a parsed resume.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class Education(BaseModel):
    """Represents a single education entry."""
    institution:  str            = ""
    degree:       str            = ""
    field_of_study: str          = ""
    start_year:   Optional[int]  = None
    end_year:     Optional[int]  = None
    raw_text:     str            = ""


class Experience(BaseModel):
    """Represents a single work experience entry."""
    company:      str            = ""
    title:        str            = ""
    start_year:   Optional[int]  = None
    end_year:     Optional[int]  = None   # None means present
    duration_months: Optional[int] = None
    description:  str            = ""
    raw_text:     str            = ""


class Resume(BaseModel):
    """
    Full structured representation of a parsed resume.
    All fields are optional since resume formats vary widely.
    """

    # --- Source ---
    file_path:    Path           = Field(default=Path("."))
    file_name:    str            = ""
    raw_text:     str            = ""

    # --- Personal Info ---
    candidate_name: str          = ""
    email:          str          = ""
    phone:          str          = ""
    location:       str          = ""
    linkedin:       str          = ""

    # --- Sections (raw text per section) ---
    sections: dict[str, str]     = Field(default_factory=dict)

    # --- Structured Data ---
    skills:         list[str]    = Field(default_factory=list)
    education:      list[Education]  = Field(default_factory=list)
    experience:     list[Experience] = Field(default_factory=list)
    certifications: list[str]    = Field(default_factory=list)
    languages:      list[str]    = Field(default_factory=list)
    projects:       list[str]    = Field(default_factory=list)

    # --- Computed Metadata ---
    total_experience_years: float = 0.0
    highest_degree:         str   = ""

    @field_validator("file_path", mode="before")
    @classmethod
    def coerce_path(cls, v: object) -> Path:
        return Path(str(v))

    @property
    def has_contact_info(self) -> bool:
        return bool(self.email or self.phone)

    @property
    def section_names(self) -> list[str]:
        return list(self.sections.keys())

    @property
    def skill_count(self) -> int:
        return len(self.skills)

    @property
    def experience_count(self) -> int:
        return len(self.experience)

    def get_full_text(self) -> str:
        """
        Returns the full raw text of the resume.
        Falls back to joining all section texts if raw_text is empty.
        """
        if self.raw_text:
            return self.raw_text
        return " ".join(self.sections.values())

    def to_summary_dict(self) -> dict:
        """Returns a lightweight dict for reporting purposes."""
        return {
            "file_name":               self.file_name,
            "candidate_name":          self.candidate_name,
            "email":                   self.email,
            "total_experience_years":  self.total_experience_years,
            "highest_degree":          self.highest_degree,
            "skill_count":             self.skill_count,
            "sections_found":          self.section_names,
        }

    class Config:
        arbitrary_types_allowed = True
