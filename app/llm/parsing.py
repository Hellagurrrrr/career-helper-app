"""Extract plain text from an uploaded CV (PDF / DOC[X] / TXT).

Parsers are imported lazily so the module is import-safe in mock mode. Unknown
or unreadable files degrade to a best-effort UTF-8 decode rather than raising,
so the extraction pipeline always has *something* to feed the model.
"""

from __future__ import annotations

import io


def extract_text(filename: str, contents: bytes) -> str:
    """Return the text content of a CV file based on its extension."""
    name = (filename or "").lower()
    if name.endswith(".pdf"):
        return _from_pdf(contents)
    if name.endswith(".docx"):
        return _from_docx(contents)
    # .doc (legacy binary) has no pure-python reader here; fall back to decode.
    return _from_plain(contents)


def _from_pdf(contents: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - optional extra
        raise RuntimeError(
            "pypdf is not installed. Install the real-AI extras from "
            "requirements.txt to parse PDF resumes."
        ) from exc

    reader = PdfReader(io.BytesIO(contents))
    pages = [(page.extract_text() or "") for page in reader.pages]
    return "\n".join(pages).strip()


def _from_docx(contents: bytes) -> str:
    try:
        import docx  # python-docx
    except ImportError as exc:  # pragma: no cover - optional extra
        raise RuntimeError(
            "python-docx is not installed. Install the real-AI extras from "
            "requirements.txt to parse DOCX resumes."
        ) from exc

    document = docx.Document(io.BytesIO(contents))
    return "\n".join(p.text for p in document.paragraphs).strip()


def _from_plain(contents: bytes) -> str:
    return contents.decode("utf-8", errors="ignore").strip()
