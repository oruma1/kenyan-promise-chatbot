"""Loads PDF and text documents"""

import os
from pathlib import Path
import PyPDF2
from bs4 import BeautifulSoup


def load_pdf(file_path: str) -> str:
    text = ""
    try:
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
    return text


def load_txt(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def load_html(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        soup = BeautifulSoup(f.read(), "html.parser")
        return soup.get_text()


def load_document(file_path: str) -> dict:
    path = Path(file_path)
    ext = path.suffix.lower()

    if ext == ".pdf":
        text = load_pdf(file_path)
    elif ext == ".txt":
        text = load_txt(file_path)
    elif ext in [".html", ".htm"]:
        text = load_html(file_path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")

    filename = path.stem.lower()
    year = 2022 if "2022" in filename else (2017 if "2017" in filename else 0)

    party = "Unknown"
    if "azimio" in filename or "raila" in filename:
        party = "Azimio La Umoja"
    elif "kenya_kwanza" in filename or "ruto" in filename or "uda" in filename:
        party = "Kenya Kwanza"
    elif "jubilee" in filename or "uhuru" in filename:
        party = "Jubilee Party"
    elif "odm" in filename:
        party = "ODM"
    elif "nasa" in filename:
        party = "NASA"

    return {
        "document_id": path.stem,
        "title": path.stem.replace("_", " ").title(),
        "year": year,
        "party": party,
        "file_path": str(path),
        "text": text,
        "source_type": "manifesto" if "manifesto" in filename else "speech"
    }


def load_all_documents(folder: str) -> list:
    documents = []
    folder_path = Path(folder)

    if not folder_path.exists():
        print(f"Folder not found: {folder}")
        return documents

    for file in folder_path.iterdir():
        if file.suffix.lower() in [".pdf", ".txt", ".html", ".htm"]:
            try:
                doc = load_document(str(file))
                if doc["text"].strip():
                    documents.append(doc)
                    print(f"[OK] Loaded: {file.name} ({len(doc['text'])} chars)")
            except Exception as e:
                print(f"[FAIL] {file.name}: {e}")

    return documents