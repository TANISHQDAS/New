import os
import pypdf
from pathlib import Path

DATASET_ROOT = Path(r"C:\Users\tanis\Downloads\QB1-main\starter-datasets")

def inspect_pdf(pdf_path):
    print(f"\n--- Inspecting {pdf_path.name} ---")
    reader = pypdf.PdfReader(pdf_path)
    print(f"Total pages: {len(reader.pages)}")
    for i in [0, 1, 2, len(reader.pages)//2, len(reader.pages)-1]:
        if i < len(reader.pages):
            text = reader.pages[i].extract_text()
            first_line = text.strip().split("\n")[0] if text else "EMPTY"
            print(f"  Page {i+1} first line: {first_line[:100]}")

if __name__ == "__main__":
    for folder in ["delhivery", "india-macroeconomy"]:
        folder_path = DATASET_ROOT / folder
        if folder_path.exists():
            for file in folder_path.glob("*.pdf"):
                inspect_pdf(file)
