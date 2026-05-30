# HireLens

An NLP-based mini ATS (Applicant Tracking System) and resume analysis system built in Python. Parses resumes, extracts structured data, scores candidates against job descriptions, and generates detailed reports.

---

## What it does

- Parses PDF, DOCX, and TXT resumes
- Extracts skills, experience, education, and certifications using spaCy NER and regex
- Scores resumes across five components: keyword match, semantic similarity, skill match, experience, and education
- Ranks multiple candidates against a single job description
- Exports results as JSON and PDF reports

---

## Requirements

- Python 3.11
- Git

---

## Setup

1. Clone the repository

        git clone https://github.com/YOUR_USERNAME/HireLens.git
        cd HireLens

2. Create and activate a virtual environment

        python -m venv hirelens_env

        Windows:
        hirelens_env\Scriptsctivate

        macOS / Linux:
        source hirelens_env/bin/activate

3. Install dependencies

        pip install --upgrade pip
        pip install -r requirements.txt

4. Run first-time setup

        python run_once_setup.py

---

## Usage

Score a single resume against a job description:

        python main.py score --resume data/resumes/resume.pdf --jd data/job_descriptions/jd.txt

Rank multiple resumes:

        python main.py rank --resumes data/resumes/ --jd data/job_descriptions/jd.txt

Options:

        --format   json | pdf | both (default: both)
        --top-n    number of top candidates to show
        --output   custom output directory
        --verbose  enable debug logging

Reports are saved to data/output/.

---

## Project Structure

        HireLens/
        core/
            extractor.py       skill, education, experience extraction
            nlp_engine.py      TF-IDF, semantic similarity, keyword extraction
            parser.py          resume section segmentation and contact extraction
            ranker.py          batch processing and candidate ranking
            scorer.py          composite ATS scoring engine
        models/
            resume.py          Resume data model
            job.py             JobDescription data model
            result.py          AnalysisResult and RankingResult models
        utils/
            config.py          configuration and constants
            file_handler.py    PDF, DOCX, TXT file reader
            text_cleaner.py    text preprocessing utilities
        reports/
            report_generator.py  JSON and PDF report generation
        data/
            resumes/           place resume files here
            job_descriptions/  place job description files here
            output/            generated reports saved here
        main.py
        cli.py
        run_once_setup.py
        requirements.txt

---

## Scoring Components

| Component           | Weight | Description                              |
|---------------------|--------|------------------------------------------|
| Keyword Match       | 30%    | TF-IDF keyword overlap with JD           |
| Semantic Similarity | 30%    | Sentence embedding cosine similarity     |
| Skill Match         | 20%    | Direct skill set comparison              |
| Experience          | 10%    | Years of experience vs requirement       |
| Education           | 10%    | Degree level vs requirement              |

Weights are configurable via the .env file.

---

## Tech Stack

- spaCy - NLP and named entity recognition
- sentence-transformers - semantic similarity
- scikit-learn - TF-IDF vectorization
- PyMuPDF - PDF parsing
- python-docx - DOCX parsing
- Pydantic - data validation
- Rich - terminal output
- fpdf2 - PDF report generation

---

## License

MIT
