"""
reports/report_generator.py
Generates JSON and PDF reports from analysis results.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from fpdf import FPDF

from models.result import AnalysisResult, RankingResult
from utils.config import OUTPUT_DIR, REPORT_FORMAT

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# JSON report
# ---------------------------------------------------------------------------

def save_json_report(
    data:      AnalysisResult | RankingResult,
    output_dir: Path | str | None = None,
    filename:   str | None = None,
) -> Path:
    output_dir = Path(output_dir) if output_dir else OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if isinstance(data, RankingResult):
            filename = f"ranking_{timestamp}.json"
        else:
            safe_name = data.file_name.replace(" ", "_").replace(".", "_")
            filename  = f"result_{safe_name}_{timestamp}.json"

    output_path = output_dir / filename

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data.to_report_dict(), f, indent=2, ensure_ascii=False)

    logger.info("JSON report saved: %s", output_path)
    return output_path


# ---------------------------------------------------------------------------
# PDF report
# ---------------------------------------------------------------------------

class _HireLensPDF(FPDF):

    def header(self) -> None:
        self.set_font("Helvetica", "B", 14)
        self.cell(0, 10, "HireLens - ATS Analysis Report", align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 9)
        self.cell(0, 6, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(4)

    def footer(self) -> None:
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")


def _add_section_title(pdf: _HireLensPDF, title: str) -> None:
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(0, 8, title, fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)


def _add_key_value(pdf: _HireLensPDF, key: str, value: str) -> None:
    """Write key and value on the same line using multi_cell for full width."""
    pdf.set_font("Helvetica", "B", 10)
    line = f"{key}: "
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 7, f"{key}: {value}", new_x="LMARGIN", new_y="NEXT")


def _add_result_to_pdf(pdf: _HireLensPDF, result: AnalysisResult) -> None:
    _add_section_title(pdf, f"Candidate: {result.candidate_name or result.file_name}")

    _add_key_value(pdf, "File",            result.file_name)
    _add_key_value(pdf, "Job Title",       result.job_title)
    _add_key_value(pdf, "Composite Score", f"{result.composite_score:.2f} / 100")
    _add_key_value(pdf, "Grade",           result.grade)
    _add_key_value(pdf, "Recommendation",  result.recommendation)
    pdf.ln(2)

    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 7, "Score Breakdown:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)

    for component, score in result.score_breakdown.to_percentage_dict().items():
        label = component.replace("_", " ").title()
        pdf.cell(0, 6, f"  {label}: {score:.1f}%", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    gap = result.gap_analysis
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 7, "Gap Analysis:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)

    if gap.matched_skills:
        pdf.multi_cell(0, 6, f"  Matched Skills: {', '.join(gap.matched_skills)}")
    if gap.missing_skills:
        pdf.multi_cell(0, 6, f"  Missing Skills: {', '.join(gap.missing_skills)}")
    if gap.experience_gap is not None:
        label = "Surplus" if gap.experience_gap < 0 else "Gap"
        pdf.cell(0, 6, f"  Experience {label}: {abs(gap.experience_gap):.1f} years", new_x="LMARGIN", new_y="NEXT")
    if gap.education_gap:
        pdf.cell(0, 6, f"  Education Gap: {gap.education_gap}", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(4)


def save_pdf_report(
    data:       AnalysisResult | RankingResult,
    output_dir: Path | str | None = None,
    filename:   str | None = None,
) -> Path:
    output_dir = Path(output_dir) if output_dir else OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if isinstance(data, RankingResult):
            filename = f"ranking_{timestamp}.pdf"
        else:
            safe_name = data.file_name.replace(" ", "_").replace(".", "_")
            filename  = f"result_{safe_name}_{timestamp}.pdf"

    output_path = output_dir / filename

    pdf = _HireLensPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    if isinstance(data, RankingResult):
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, f"Job: {data.job_title or data.job_file}", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 6, f"Total Resumes Analyzed: {data.total_resumes_analyzed}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)

        for rank, result in enumerate(data.ranked_candidates, start=1):
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(0, 7, f"Rank #{rank}", new_x="LMARGIN", new_y="NEXT")
            _add_result_to_pdf(pdf, result)
    else:
        _add_result_to_pdf(pdf, data)

    pdf.output(str(output_path))
    logger.info("PDF report saved: %s", output_path)
    return output_path


# ---------------------------------------------------------------------------
# Unified save function
# ---------------------------------------------------------------------------

def save_report(
    data:       AnalysisResult | RankingResult,
    output_dir: Path | str | None = None,
    fmt:        str | None = None,
) -> list[Path]:
    fmt = fmt or REPORT_FORMAT
    saved: list[Path] = []

    if fmt in ("json", "both"):
        saved.append(save_json_report(data, output_dir))

    if fmt in ("pdf", "both"):
        saved.append(save_pdf_report(data, output_dir))

    return saved
