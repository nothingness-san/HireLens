"""
HireLens - First-time setup script.
Run this once after cloning the repo and installing requirements.txt

    python run_once_setup.py
"""

import subprocess
import sys
import os
import shutil


def run(cmd: list[str], desc: str) -> bool:
    print(f"{desc}...")
    result = subprocess.run(cmd, capture_output=False)
    if result.returncode == 0:
        print(f"{desc} - done")
        return True
    else:
        print(f"{desc} - FAILED")
        return False


def download_nltk() -> bool:
    print("Downloading NLTK corpora...")
    try:
        import nltk
        packages = [
            'punkt', 'punkt_tab', 'stopwords',
            'wordnet', 'averaged_perceptron_tagger', 'omw-1.4'
        ]
        for pkg in packages:
            nltk.download(pkg, quiet=True)
        print("NLTK corpora - done")
        return True
    except Exception as e:
        print(f"NLTK download failed: {e}")
        return False


def cache_sentence_transformer() -> bool:
    print("Caching Sentence Transformer model (~90MB)...")
    try:
        from sentence_transformers import SentenceTransformer
        SentenceTransformer('all-MiniLM-L6-v2')
        print("Sentence Transformer model - done")
        return True
    except Exception as e:
        print(f"Sentence Transformer failed: {e}")
        return False


def copy_env() -> bool:
    if not os.path.exists('.env'):
        if os.path.exists('.env.example'):
            shutil.copy('.env.example', '.env')
            print(".env created from .env.example")
        else:
            print("No .env.example found - skipping")
    else:
        print(".env already exists - skipping")
    return True


if __name__ == "__main__":
    print("=" * 50)
    print("HireLens - First-time Setup")
    print("=" * 50)

    results = [
        run(
            [sys.executable, "-m", "pip", "install",
             "https://github.com/explosion/spacy-models/releases/download/en_core_web_md-3.7.1/en_core_web_md-3.7.1-py3-none-any.whl"],
            "Installing spaCy model (en_core_web_md)"
        ),
        download_nltk(),
        cache_sentence_transformer(),
        copy_env(),
    ]

    print("\n" + "=" * 50)
    if all(results):
        print("Setup complete. You are ready to use HireLens.")
        print("Next: python main.py --help")
    else:
        print("Some steps failed. Check the errors above.")
    print("=" * 50)
