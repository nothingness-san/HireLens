# HireLens - Setup Guide

## Prerequisites

- Python 3.11 (required — 3.12+ may have compatibility issues with some dependencies)
- Git

Download Python 3.11 from: https://www.python.org/downloads/release/python-3119/
During installation, check "Add Python to PATH".

---

## Step 1 — Clone the repository

    git clone https://github.com/YOUR_USERNAME/HireLens.git
    cd HireLens

---

## Step 2 — Create a virtual environment

Windows (Command Prompt or Git Bash):

    python -m venv hirelens_env
    hirelens_env\Scripts\activate

macOS / Linux:

    python3.11 -m venv hirelens_env
    source hirelens_env/bin/activate

You should see (hirelens_env) in your terminal prompt.

---

## Step 3 — Install dependencies

    pip install --upgrade pip
    pip install -r requirements.txt

This will take 3-7 minutes depending on your internet speed.
It downloads spaCy, sentence-transformers, PyTorch, and other packages.

---

## Step 4 — Run first-time setup

    python run_once_setup.py

This downloads:
- spaCy English model (en_core_web_md, ~43MB)
- NLTK corpora (punkt, stopwords, wordnet, etc.)
- Sentence Transformer model (all-MiniLM-L6-v2, ~90MB)
- Creates your .env file from .env.example

Only needs to be run once.

---

## Step 5 — Verify setup

    python verify_env.py

All items should show as confirmed. If any fail, re-run Step 3 or Step 4.

---

## Step 6 — Add your files

Place resume files (.pdf, .docx, or .txt) in:

    data/resumes/

Place job description files (.pdf, .docx, or .txt) in:

    data/job_descriptions/

---

## Step 7 — Run HireLens

Score a single resume against a job description:

    python main.py score --resume data/resumes/your_resume.pdf --jd data/job_descriptions/your_jd.pdf

Rank multiple resumes:

    python main.py rank --resumes data/resumes/ --jd data/job_descriptions/your_jd.pdf

View all options:

    python main.py --help
    python main.py score --help
    python main.py rank --help

---

## Output

Reports are saved to data/output/ in both JSON and PDF formats by default.

To change the output format:

    python main.py score --resume ... --jd ... --format json
    python main.py score --resume ... --jd ... --format pdf

---

## Adjusting Scoring Weights

Open .env and modify the weights (they must sum to 1.0):

    WEIGHT_KEYWORD_MATCH=0.30
    WEIGHT_SEMANTIC_SIMILARITY=0.30
    WEIGHT_SKILLS=0.20
    WEIGHT_EXPERIENCE=0.10
    WEIGHT_EDUCATION=0.10

---

## Troubleshooting

spaCy model not found:
    python -m pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_md-3.7.1/en_core_web_md-3.7.1-py3-none-any.whl

NLTK data missing:
    python -c "import nltk; [nltk.download(x) for x in ['punkt','punkt_tab','stopwords','wordnet','averaged_perceptron_tagger','omw-1.4']]"

Sentence transformer missing:
    python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

Virtual environment not activating on Windows:
    Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
