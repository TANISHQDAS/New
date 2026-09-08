import os
import re
from typing import List, Dict, Any

class PDFExtractor:
    """Extracts text page-by-page using pypdf (pure Python, works on Vercel)."""

    @staticmethod
    def extract_pages(pdf_path: str) -> List[Dict[str, Any]]:
        import pypdf

        pages_data = []
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        try:
            reader = pypdf.PdfReader(pdf_path)
            for idx, page in enumerate(reader.pages):
                try:
                    text = page.extract_text() or ""
                except Exception:
                    text = ""
                lines = [line.strip() for line in text.split("\n") if line.strip()]
                pages_data.append({
                    "page_number": idx + 1,
                    "text": text,
                    "lines": lines,
                    "tables": [],
                    "char_count": len(text)
                })
        except Exception as e:
            print(f"Error reading PDF {pdf_path}: {e}")

        if not pages_data:
            pages_data.append({
                "page_number": 1,
                "text": "",
                "lines": [],
                "tables": [],
                "char_count": 0
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
                    start_idx = max(0, idx - 1)
                    end_idx = min(len(lines), idx + 2)
                    context_snippet = " ".join(lines[start_idx:end_idx])
                    matches.append({
                        "page_number": page_num,
                        "line": line,
                        "context_snippet": context_snippet
                    })
        return matches
