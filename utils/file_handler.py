"""
utils/file_handler.py
Handles reading PDF, DOCX, and TXT resume files into raw text.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable

import fitz
from docx import Document

from utils.config import SUPPORTED_EXTENSIONS

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Individual readers
# ---------------------------------------------------------------------------

def _read_pdf(path: Path) -> str:
    """Extract text from a PDF file using PyMuPDF."""
    try:
        doc = fitz.open(str(path))
        pages = [page.get_text("text") for page in doc]
        doc.close()
        return "\n".join(pages)
    except Exception as e:
        logger.error("Failed to read PDF %s: %s", path.name, e)
        raise


def _read_docx(path: Path) -> str:
    """Extract text from a DOCX file using python-docx."""
    try:
        doc = Document(str(path))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n".join(paragraphs)
    except Exception as e:
        logger.error("Failed to read DOCX %s: %s", path.name, e)
        raise


def _read_txt(path: Path) -> str:
    """Read a plain text file."""
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        logger.error("Failed to read TXT %s: %s", path.name, e)
        raise


# ---------------------------------------------------------------------------
# Dispatch table — maps extension to reader function
# ---------------------------------------------------------------------------

_READERS: dict[str, Callable[[Path], str]] = {
    ".pdf":  _read_pdf,
    ".docx": _read_docx,
    ".txt":  _read_txt,
}


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def read_file(path: Path | str) -> str:
    """
    Read a resume or job description file and return its raw text.
    Supports .pdf, .docx, and .txt formats.
    """
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    ext = path.suffix.lower()

    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type '{ext}'. "
            f"Supported types: {sorted(SUPPORTED_EXTENSIONS)}"
        )

    reader = _READERS[ext]
    text = reader(path)

    if not text.strip():
        logger.warning("File %s returned empty text.", path.name)

    return text


def read_all_files(directory: Path | str) -> dict[Path, str]:
    """
    Read all supported files in a directory.
    Returns a dict mapping file path to raw text.
    Skips unsupported files silently.
    """
    directory = Path(directory)

    if not directory.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")

    results: dict[Path, str] = {}

    for file_path in sorted(directory.iterdir()):
        if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        try:
            results[file_path] = read_file(file_path)
            logger.info("Read file: %s", file_path.name)
        except Exception as e:
            logger.error("Skipping %s: %s", file_path.name, e)

    return results


def validate_file(path: Path | str) -> bool:
    """Returns True if the file exists and is a supported type."""
    path = Path(path)
    return path.exists() and path.suffix.lower() in SUPPORTED_EXTENSIONS
