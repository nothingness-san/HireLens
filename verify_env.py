import sys
import importlib

REQUIRED = [
    ("spacy",                 "spaCy"),
    ("nltk",                  "NLTK"),
    ("sentence_transformers", "Sentence Transformers"),
    ("sklearn",               "scikit-learn"),
    ("numpy",                 "NumPy"),
    ("fitz",                  "PyMuPDF"),
    ("docx",                  "python-docx"),
    ("pydantic",              "Pydantic"),
    ("rich",                  "Rich"),
    ("fpdf",                  "FPDF2"),
    ("tqdm",                  "tqdm"),
    ("dotenv",                "python-dotenv"),
    ("regex",                 "regex"),
]

print(f"Python: {sys.version}\n")
all_ok = True
for module, name in REQUIRED:
    try:
        importlib.import_module(module)
        print(f"  ✅  {name}")
    except ImportError:
        print(f"  ❌  {name}  <- NOT INSTALLED")
        all_ok = False

try:
    import spacy
    spacy.load("en_core_web_md")
    print(f"  ✅  spaCy model (en_core_web_md)")
except OSError:
    print(f"  ❌  spaCy model missing")
    all_ok = False

print("\n" + ("🎉 Environment ready!" if all_ok else "⚠️  Fix the issues above."))
