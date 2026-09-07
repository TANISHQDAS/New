import pypdf
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

DATASET_ROOT = Path(r"C:\Users\tanis\Downloads\QB1-main\starter-datasets")

def search_pdf(pdf_path):
    print(f"\n==========================================")
    print(f"SEARCHING: {pdf_path.name}")
    print(f"==========================================")
    reader = pypdf.PdfReader(pdf_path)
    for idx, page in enumerate(reader.pages):
        text = page.extract_text()
        if not text:
            continue
        for line in text.split("\n"):
            line_lower = line.lower()
            if any(kw in line_lower for kw in ["revenue", "gdp", "ebitda", "express parcel", "pincode", "pin code", "inflation"]):
                if re.search(r'\d', line):
                    cleaned = line.strip().encode('ascii', 'replace').decode('ascii')
                    print(f"Page {idx+1}: {cleaned[:140]}")

if __name__ == "__main__":
    for folder in ["delhivery", "india-macroeconomy"]:
        folder_path = DATASET_ROOT / folder
        for file in folder_path.glob("*.pdf"):
            search_pdf(file)
