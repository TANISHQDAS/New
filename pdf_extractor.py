import pypdf
import pdfplumber
import os
import re
from typing import List, Dict, Any

class PDFExtractor:
    """Extracts structured text page-by-page with line numbers and section context."""

    @staticmethod
    def extract_pages(pdf_path: str) -> List[Dict[str, Any]]:
        pages_data = []
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        try:
            # Try pdfplumber first for better layout preservation
            with pdfplumber.open(pdf_path) as pdf:
                for idx, page in enumerate(pdf.pages):
                    text = page.extract_text(layout=False) or ""
                    tables = page.extract_tables() or []
                    pages_data.append({
                        "page_number": idx + 1,
                        "text": text,
                        "lines": [line.strip() for line in text.split("\n") if line.strip()],
                        "tables": tables,
                        "char_count": len(text)
                    })
        except Exception as e:
            # Fallback to pypdf
            reader = pypdf.PdfReader(pdf_path)
            for idx, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                pages_data.append({
                    "page_number": idx + 1,
                    "text": text,
                    "lines": [line.strip() for line in text.split("\n") if line.strip()],
                    "tables": [],
                    "char_count": len(text)
                })

        return pages_data

    @staticmethod
    def find_snippets_by_keywords(pages_data: List[Dict[str, Any]], keywords: List[str]) -> List[Dict[str, Any]]:
        matches = []
        pattern = re.compile(r'|'.join(re.escape(kw) for kw in keywords), re.IGNORECASE)
        
        for page in pages_data:
            page_num = page["page_number"]
            lines = page["lines"]
            for idx, line in enumerate(lines):
                if pattern.search(line):
                    # grab surround lines for evidence quote context
                    start_idx = max(0, idx - 1)
                    end_idx = min(len(lines), idx + 2)
                    context_snippet = " ".join(lines[start_idx:end_idx])
                    matches.append({
                        "page_number": page_num,
                        "line": line,
                        "context_snippet": context_snippet
                    })
        return matches
