# HireLens

An NLP-based mini ATS and resume analysis system built in Python.

HireLens analyzes resumes against job descriptions using keyword matching,
semantic similarity, entity extraction, and composite scoring to rank candidates.

---

## Requirements

- Python 3.11
- Git

---

## Quickstart

1. Clone the repo
   git clone https://github.com/YOUR_USERNAME/HireLens.git
   cd HireLens

2. Create and activate virtual environment
   python -m venv hirelens_env
   source hirelens_env/Scripts/activate  (Windows Git Bash)

3. Install dependencies
   pip install --upgrade pip
   pip install -r requirements.txt

4. Run first-time setup (downloads models and corpora)
   python run_once_setup.py

5. Run HireLens
   python main.py --help

---

## Project Structure

    HireLens/
    core/                  NLP engine, parser, scorer, ranker, extractor
    models/                Pydantic data models
    utils/                 File handler, text cleaner, config
    reports/               Report generator
    data/
        resumes/           Drop resumes here (.pdf / .docx / .txt)
        job_descriptions/  Drop job description files here
        output/            Generated reports saved here
    main.py
    cli.py
    run_once_setup.py
    requirements.txt

---

## License

MIT
