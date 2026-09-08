import os
import re
import tempfile
import pypdf
from pathlib import Path
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# Create FastAPI app
app = FastAPI()

# Setup paths
STATIC_DIR = Path(__file__).parent / "static"
UPLOAD_DIR = Path(tempfile.gettempdir()) / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Case Categories
CASE1 = "Case 1: Corroborated Fact"
CASE2 = "Case 2: Genuine Contradiction"
CASE3 = "Case 3: Apparent Contradiction (Reconciled by Context)"
CASE4 = "Case 4: Extraction/Reasoning Failure & Mitigation"

# Metric search patterns
METRIC_PATTERNS = [
    ("Revenue", r"(?:revenue|sales|income)[^\n]{0,50}?(?:rs\.?|inr|\$)?\s*([\d,]+\.?\d*)\s*(cr|crore|mn|million|billion)?"),
    ("Profit", r"(?:net profit|pat|profit)[^\n]{0,50}?(?:rs\.?|inr|\$)?\s*([\d,]+\.?\d*)\s*(cr|crore|mn|million)?"),
    ("EBITDA", r"(?:ebitda|operating profit)[^\n]{0,50}?(?:rs\.?|inr|\$)?\s*([\d,]+\.?\d*)\s*(cr|crore|mn|million)?"),
    ("Workforce", r"(?:employees|workforce|staff|headcount)[^\n]{0,30}?:\s*([\d,]+)"),
    ("Shipments", r"(?:shipments|parcels|units|volume)[^\n]{0,30}?:\s*([\d,]+\.?\d*)\s*(mn|million|cr)?"),
    ("General Metric", r"([a-zA-Z\s]{3,20})\s*[:=]\s*(?:rs\.?|inr|\$)?\s*([\d,]+\.?\d*)\s*(cr|crore|mn|million|%)?")
]

def parse_amount(val_str, unit_str=""):
    try:
        val = float(val_str.replace(",", "").strip())
        unit = (unit_str or "").lower().strip()
        if "mn" in unit or "million" in unit:
            return round(val / 10, 4)
        if "billion" in unit:
            return round(val * 100, 4)
        return val
    except:
        return 0.0

def find_year(text):
    match = re.search(r"\b(FY\s*\d{2,4}|20\d{2}|Q[1-4]\s*FY\d{2})\b", text, re.IGNORECASE)
    if match:
        return match.group(0).upper()
    return "N/A"

def extract_pdf_data(pdf_path, filename):
    facts = []
    seen_keys = set()

    try:
        reader = pypdf.PdfReader(pdf_path)
        for page_num, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            for line in text.split("\n"):
                line = line.strip()
                if not line or len(line) < 4:
                    continue

                for metric_name, pattern in METRIC_PATTERNS:
                    match = re.search(pattern, line, re.IGNORECASE)
                    if match:
                        raw_val = match.group(1)
                        unit = match.group(2) if len(match.groups()) >= 2 and match.group(2) else ""
                        if metric_name == "General Metric":
                            metric_name = f"Metric: {match.group(1).strip().title()}"
                            raw_val = match.group(2)
                            unit = match.group(3) if len(match.groups()) >= 3 and match.group(3) else ""

                        num_val = parse_amount(raw_val, unit)
                        if num_val <= 0:
                            continue

                        period = find_year(line)
                        display_val = f"{raw_val} {unit}".strip() if unit else raw_val
                        unique_key = (metric_name, display_val, period)

                        if unique_key in seen_keys:
                            continue
                        seen_keys.add(unique_key)

                        facts.append({
                            "fact_id": f"fact-{len(facts) + 1}",
                            "metric_name": metric_name,
                            "raw_value": display_val,
                            "normalized_value": num_val,
                            "unit": unit or "Value",
                            "timeframe": period,
                            "evidence": {
                                "doc_name": filename,
                                "page_number": page_num,
                                "verbatim_quote": line[:180]
                            }
                        })
    except Exception as err:
        print("Error reading PDF:", err)

    # Classify cases
    cases = {CASE1: [], CASE2: [], CASE3: [], CASE4: []}
    metric_groups = {}
    for f in facts:
        metric_groups.setdefault(f["metric_name"], []).append(f)

    case_count = 1
    for name, fact_list in metric_groups.items():
        if len(fact_list) < 2:
            continue

        for i in range(len(fact_list)):
            for j in range(i + 1, len(fact_list)):
                f1 = fact_list[i]
                f2 = fact_list[j]

                # Skip if on same page
                if f1["evidence"]["page_number"] == f2["evidence"]["page_number"]:
                    continue

                page1 = f"Page {f1['evidence']['page_number']}"
                page2 = f"Page {f2['evidence']['page_number']}"
                same_time = (f1["timeframe"] == f2["timeframe"]) and f1["timeframe"] != "N/A"
                same_num = abs(f1["normalized_value"] - f2["normalized_value"]) < 0.05 * max(f1["normalized_value"], f2["normalized_value"], 1.0)

                if same_time and same_num:
                    cases[CASE1].append({
                        "relation_id": f"rel-{case_count}",
                        "case_type": CASE1,
                        "fact_a": f1,
                        "fact_b": f2,
                        "title": f"Matching {name} ({f1['timeframe']})",
                        "reasoning": f"Both {page1} and {page2} report matching {name} of {f1['raw_value']}."
                    })
                elif same_time and not same_num:
                    cases[CASE2].append({
                        "relation_id": f"rel-{case_count}",
                        "case_type": CASE2,
                        "fact_a": f1,
                        "fact_b": f2,
                        "title": f"Conflicting {name} ({f1['timeframe']})",
                        "reasoning": f"Conflict for {name} in {f1['timeframe']}: {f1['raw_value']} ({page1}) vs {f2['raw_value']} ({page2})."
                    })
                else:
                    cases[CASE3].append({
                        "relation_id": f"rel-{case_count}",
                        "case_type": CASE3,
                        "fact_a": f1,
                        "fact_b": f2,
                        "title": f"{name} Across Different Periods",
                        "reasoning": f"{f1['raw_value']} ({page1}, {f1['timeframe']}) vs {f2['raw_value']} ({page2}, {f2['timeframe']}) — different time periods."
                    })
                case_count += 1

    # Fallback case 3 if no pairs found
    if len(facts) >= 2 and sum(len(v) for v in cases.values()) == 0:
        f1, f2 = facts[0], facts[1]
        cases[CASE3].append({
            "relation_id": "rel-1",
            "case_type": CASE3,
            "fact_a": f1,
            "fact_b": f2,
            "title": f"Comparison: {f1['metric_name']} vs {f2['metric_name']}",
            "reasoning": f"Comparing {f1['metric_name']} ({f1['raw_value']}) on Page {f1['evidence']['page_number']} with {f2['metric_name']} ({f2['raw_value']}) on Page {f2['evidence']['page_number']}."
        })

    if not facts:
        cases[CASE4].append({
            "relation_id": "rel-fail",
            "case_type": CASE4,
            "fact_a": {
                "fact_id": "none",
                "metric_name": "None",
                "raw_value": "N/A",
                "normalized_value": 0,
                "unit": "N/A",
                "timeframe": "N/A",
                "evidence": {"doc_name": filename, "page_number": 1, "verbatim_quote": "No facts extracted from document."}
            },
            "title": f"No Facts Found in {filename}",
            "reasoning": "This document contains no readable text numbers or scanned image content.",
            "handling_strategy": "Try uploading a text-based PDF report."
        })

    total_cases = sum(len(v) for v in cases.values())
    return {
        "dataset_id": f"upload-{filename}",
        "facts_extracted_count": len(facts),
        "reconciled_cases_count": total_cases,
        "cases": cases,
        "facts": facts
    }

def get_demo_data():
    f1 = {"fact_id": "d1", "metric_name": "Revenue", "raw_value": "₹36,465 Mn", "normalized_value": 36465, "unit": "INR Mn", "timeframe": "FY21", "evidence": {"doc_name": "01-delhivery-prospectus-2022.pdf", "page_number": 45, "verbatim_quote": "Revenue for Fiscal 2021 was ₹36,465 million."}}
    f2 = {"fact_id": "d2", "metric_name": "Revenue", "raw_value": "₹81,417 Mn", "normalized_value": 81417, "unit": "INR Mn", "timeframe": "FY24", "evidence": {"doc_name": "02-delhivery-annual-report-fy24.pdf", "page_number": 2, "verbatim_quote": "Revenue reached ₹81,417 million in FY24."}}
    f3 = {"fact_id": "d3", "metric_name": "Express Parcel Volume", "raw_value": "740 Mn Shipments", "normalized_value": 740, "unit": "Mn Shipments", "timeframe": "FY24", "evidence": {"doc_name": "02-delhivery-annual-report-fy24.pdf", "page_number": 2, "verbatim_quote": "Delivered 740 million express parcel shipments."}}
    f4 = {"fact_id": "d4", "metric_name": "Express Parcel Volume", "raw_value": "740 Mn Shipments", "normalized_value": 740, "unit": "Mn Shipments", "timeframe": "FY24", "evidence": {"doc_name": "03-delhivery-q4-fy24-earnings.pdf", "page_number": 14, "verbatim_quote": "FY24 volume stood at 740 Mn shipments."}}
    f5 = {"fact_id": "d5", "metric_name": "Workforce", "raw_value": "30,524 Employees", "normalized_value": 30524, "unit": "Persons", "timeframe": "FY24", "evidence": {"doc_name": "02-delhivery-annual-report-fy24.pdf", "page_number": 4, "verbatim_quote": "Direct workforce stood at 30,524 employees."}}
    f6 = {"fact_id": "d6", "metric_name": "Workforce", "raw_value": "87,422 Personnel", "normalized_value": 87422, "unit": "Persons", "timeframe": "FY24", "evidence": {"doc_name": "02-delhivery-annual-report-fy24.pdf", "page_number": 52, "verbatim_quote": "Total active personnel reached 87,422."}}

    return {
        "dataset_id": "delhivery",
        "facts_extracted_count": 6,
        "reconciled_cases_count": 3,
        "cases": {
            CASE1: [{"relation_id": "dc1", "case_type": CASE1, "fact_a": f3, "fact_b": f4, "title": "Matching Express Parcel Volume (FY24)", "reasoning": "Both Annual Report and Earnings Presentation state 740 Mn shipments for FY24."}],
            CASE2: [{"relation_id": "dc2", "case_type": CASE2, "fact_a": f5, "fact_b": f6, "title": "Conflict in Workforce Count (FY24)", "reasoning": "Page 4 states 30,524 direct employees; Page 52 states 87,422 total personnel."}],
            CASE3: [{"relation_id": "dc3", "case_type": CASE3, "fact_a": f1, "fact_b": f2, "title": "Revenue Growth (FY21 vs FY24)", "reasoning": "₹36,465 Mn (FY21) vs ₹81,417 Mn (FY24) — growth over 3 years."}],
            CASE4: []
        },
        "facts": [f1, f2, f3, f4, f5, f6]
    }

# Web Routes
@app.get("/")
def home():
    return FileResponse(str(STATIC_DIR / "index.html"))

@app.get("/api/analysis/{dataset_id}")
def get_analysis(dataset_id: str):
    return get_demo_data()

@app.post("/api/upload")
def upload_pdf(file: UploadFile = File(...)):
    save_path = UPLOAD_DIR / file.filename
    with open(save_path, "wb") as buffer:
        buffer.write(file.file.read())
    return extract_pdf_data(str(save_path), file.filename)
