"""
cli.py
Command-line interface for HireLens.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog        = "hirelens",
        description = "HireLens - NLP-based ATS and Resume Analysis System",
        formatter_class = argparse.RawTextHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # --- score: single resume ---
    score_parser = subparsers.add_parser(
        "score",
        help = "Score a single resume against a job description",
    )
    score_parser.add_argument(
        "--resume", "-r",
        required = True,
        type     = Path,
        help     = "Path to resume file (.pdf, .docx, .txt)",
    )
    score_parser.add_argument(
        "--jd", "-j",
        required = True,
        type     = Path,
        help     = "Path to job description file",
    )
    score_parser.add_argument(
        "--output", "-o",
        type    = Path,
        default = None,
        help    = "Output directory for reports (default: data/output)",
    )
    score_parser.add_argument(
        "--format", "-f",
        choices = ["json", "pdf", "both"],
        default = "both",
        help    = "Report format (default: both)",
    )

    # --- rank: batch ranking ---
    rank_parser = subparsers.add_parser(
        "rank",
        help = "Rank all resumes in a directory against a job description",
    )
    rank_parser.add_argument(
        "--resumes", "-r",
        required = True,
        type     = Path,
        help     = "Directory containing resume files",
    )
    rank_parser.add_argument(
        "--jd", "-j",
        required = True,
        type     = Path,
        help     = "Path to job description file",
    )
    rank_parser.add_argument(
        "--top-n", "-n",
        type    = int,
        default = None,
        help    = "Number of top candidates to display",
    )
    rank_parser.add_argument(
        "--output", "-o",
        type    = Path,
        default = None,
        help    = "Output directory for reports (default: data/output)",
    )
    rank_parser.add_argument(
        "--format", "-f",
        choices = ["json", "pdf", "both"],
        default = "both",
        help    = "Report format (default: both)",
    )

    # --- Global flags ---
    parser.add_argument(
        "--verbose", "-v",
        action  = "store_true",
        help    = "Enable verbose logging",
    )

    return parser


def configure_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        level   = level,
        format  = "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt = "%H:%M:%S",
    )


def run_score(args: argparse.Namespace) -> None:
    from core.ranker import score_single
    from reports.report_generator import save_report
    from rich.console import Console
    from rich.table import Table

    console = Console()
    console.print(f"\nScoring: {args.resume.name} against {args.jd.name}")

    result = score_single(args.resume, args.jd)

    # Display result
    table = Table(title="ATS Score Result", show_lines=True)
    table.add_column("Field",  style="bold")
    table.add_column("Value")

    table.add_row("Candidate",       result.candidate_name or result.file_name)
    table.add_row("Job Title",       result.job_title)
    table.add_row("Composite Score", f"{result.composite_score:.2f} / 100")
    table.add_row("Grade",           result.grade)
    table.add_row("Recommendation",  result.recommendation)

    console.print(table)

    # Breakdown
    breakdown_table = Table(title="Score Breakdown", show_lines=True)
    breakdown_table.add_column("Component", style="bold")
    breakdown_table.add_column("Score (%)")

    for component, score in result.score_breakdown.to_percentage_dict().items():
        label = component.replace("_", " ").title()
        breakdown_table.add_row(label, f"{score:.1f}")

    console.print(breakdown_table)

    # Gap analysis
    gap = result.gap_analysis
    if gap.missing_skills:
        console.print(f"\nMissing Skills: {', '.join(gap.missing_skills)}")
    if gap.matched_skills:
        console.print(f"Matched Skills: {', '.join(gap.matched_skills)}")

    # Save report
    saved = save_report(result, output_dir=args.output, fmt=args.format)
    for path in saved:
        console.print(f"\nReport saved: {path}")


def run_rank(args: argparse.Namespace) -> None:
    from core.ranker import rank_resumes
    from reports.report_generator import save_report
    from rich.console import Console
    from rich.table import Table

    console = Console()
    console.print(f"\nRanking resumes in: {args.resumes}")
    console.print(f"Against JD: {args.jd.name}\n")

    ranking = rank_resumes(
        resume_dir = args.resumes,
        jd_path    = args.jd,
        top_n      = args.top_n,
    )

    table = Table(title=f"Candidate Rankings - {ranking.job_title}", show_lines=True)
    table.add_column("Rank",        style="bold")
    table.add_column("Candidate")
    table.add_column("Score")
    table.add_column("Grade")
    table.add_column("Recommendation")

    for rank, candidate in enumerate(ranking.ranked_candidates, start=1):
        table.add_row(
            str(rank),
            candidate.candidate_name or candidate.file_name,
            f"{candidate.composite_score:.2f}",
            candidate.grade,
            candidate.recommendation,
        )

    console.print(table)
    console.print(f"\nTotal resumes analyzed: {ranking.total_resumes_analyzed}")

    saved = save_report(ranking, output_dir=args.output, fmt=args.format)
    for path in saved:
        console.print(f"Report saved: {path}")


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args   = parser.parse_args(argv)

    configure_logging(verbose=args.verbose)

    if args.command == "score":
        run_score(args)
    elif args.command == "rank":
        run_rank(args)
    else:
        parser.print_help()
        sys.exit(1)
