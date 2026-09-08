import os, re, tempfile, pypdf
from pathlib import Path
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI()

STATIC_DIR = Path(__file__).parent / "static"
UPLOAD_DIR = Path(tempfile.gettempdir()) / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

C1 = "Case 1: Corroborated Fact"
C2 = "Case 2: Genuine Contradiction"
C3 = "Case 3: Apparent Contradiction (Reconciled by Context)"
C4 = "Case 4: Extraction/Reasoning Failure & Mitigation"

PATTERNS = [
    ("Revenue", r"(?:revenue|sales|income)[^\n]{0,60}?(?:rs\.?|inr|\$|₹|■)?\s*([\d,]+\.?\d*)\s*(cr|crore|mn|million|billion|lakh)?"),
    ("Profit", r"(?:net profit|pat|profit)[^\n]{0,60}?(?:rs\.?|inr|\$|₹|■)?\s*([\d,]+\.?\d*)\s*(cr|crore|mn|million|billion|lakh)?"),
    ("EBITDA", r"(?:ebitda|operating profit)[^\n]{0,60}?(?:rs\.?|inr|\$|₹|■)?\s*([\d,]+\.?\d*)\s*(cr|crore|mn|million|%|percent)?"),
    ("Workforce", r"(?:employees|workforce|staff|headcount)[^\n]{0,40}?:\s*([\d,]+)"),
    ("Express Parcel Volume", r"(?:shipments|parcels|volume)[^\n]{0,40}?:\s*([\d,]+\.?\d*)\s*(mn|million|cr|lakh)?")
]

def parse_num(val_str, unit=""):
    try:
        val = float(val_str.replace(",", "").strip())
        u = (unit or "").lower()
        if "mn" in u or "million" in u: return round(val / 10, 4)
        if "billion" in u: return round(val * 100, 4)
        return val
    except:
        return 0.0

def get_period(text):
    m = re.search(r"\b(Q[1-4]\s*FY\s*\d{2,4}|FY\s*\d{2,4}|20\d{2})\b", text, re.I)
    return m.group(0).upper() if m else "N/A"

def extract_pdf_data(pdf_path, filename):
    facts, seen = [], set()
    try:
        reader = pypdf.PdfReader(pdf_path)
        for p_num, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            for line in text.split("\n"):
                line = line.strip()
                if not line or len(line) < 4: continue

                clean_line = re.sub(r"\b(Q[1-4]\s*FY\s*\d{2,4}|FY\s*\d{2,4}|20\d{2})\b", "", line, flags=re.I)
                for name, pat in PATTERNS:
                    m = re.search(pat, clean_line, re.I)
                    if m:
                        raw_val = m.group(1)
                        unit = m.group(2) if len(m.groups()) >= 2 and m.group(2) else ""
                        num_val = parse_num(raw_val, unit)
                        if num_val <= 0: continue

                        period = get_period(line)
                        display_val = f"{raw_val} {unit}".strip() if unit else raw_val
                        key = (name, display_val, period)

                        if key in seen: continue
                        seen.add(key)

                        facts.append({
                            "fact_id": f"fact-{len(facts) + 1}",
                            "metric_name": name,
                            "raw_value": display_val,
                            "normalized_value": num_val,
                            "unit": unit or "Value",
                            "timeframe": period,
                            "evidence": {"doc_name": filename, "page_number": p_num, "verbatim_quote": line[:180]}
                        })
    except Exception as e:
        print("PDF error:", e)

    cases = {C1: [], C2: [], C3: [], C4: []}
    grouped = {}
    for f in facts: grouped.setdefault(f["metric_name"], []).append(f)

    c_id = 1
    for name, f_list in grouped.items():
        if len(f_list) < 2: continue
        for i in range(len(f_list)):
            for j in range(i + 1, len(f_list)):
                f1, f2 = f_list[i], f_list[j]
                p1, p2 = f"Page {f1['evidence']['page_number']}", f"Page {f2['evidence']['page_number']}"
                same_t = (f1["timeframe"] == f2["timeframe"]) and f1["timeframe"] != "N/A"
                same_v = abs(f1["normalized_value"] - f2["normalized_value"]) < 0.05 * max(f1["normalized_value"], f2["normalized_value"], 1.0)

                if same_t and same_v:
                    cases[C1].append({"relation_id": f"rel-{c_id}", "case_type": C1, "fact_a": f1, "fact_b": f2, "title": f"Matching {name} ({f1['timeframe']})", "reasoning": f"Both {p1} and {p2} report matching {name} of {f1['raw_value']}."})
                elif same_t and not same_v:
                    cases[C2].append({"relation_id": f"rel-{c_id}", "case_type": C2, "fact_a": f1, "fact_b": f2, "title": f"Conflict in {name} ({f1['timeframe']})", "reasoning": f"{p1} states {f1['raw_value']}; {p2} states {f2['raw_value']}."})
                else:
                    cases[C3].append({"relation_id": f"rel-{c_id}", "case_type": C3, "fact_a": f1, "fact_b": f2, "title": f"{name} Growth ({f1['timeframe']} vs {f2['timeframe']})", "reasoning": f"{f1['raw_value']} ({f1['timeframe']}) vs {f2['raw_value']} ({f2['timeframe']}) — growth over time."})
                c_id += 1

    if len(facts) >= 2 and sum(len(v) for v in cases.values()) == 0:
        f1, f2 = facts[0], facts[1]
        cases[C3].append({"relation_id": "rel-1", "case_type": C3, "fact_a": f1, "fact_b": f2, "title": f"Comparison: {f1['metric_name']} vs {f2['metric_name']}", "reasoning": f"Comparing {f1['metric_name']} ({f1['raw_value']}) on Page {f1['evidence']['page_number']} with {f2['metric_name']} ({f2['raw_value']}) on Page {f2['evidence']['page_number']}."})

    if not facts:
        cases[C4].append({"relation_id": "rel-fail", "case_type": C4, "fact_a": {"fact_id": "none", "metric_name": "None", "raw_value": "N/A", "normalized_value": 0, "unit": "N/A", "timeframe": "N/A", "evidence": {"doc_name": filename, "page_number": 1, "verbatim_quote": "No facts extracted."}}, "title": f"No Facts Found in {filename}", "reasoning": "Document contains no readable text numbers or scanned image content."})

    return {"dataset_id": f"upload-{filename}", "facts_extracted_count": len(facts), "reconciled_cases_count": sum(len(v) for v in cases.values()), "cases": cases, "facts": facts}

def get_demo_data():
    f1 = {"fact_id": "d1", "metric_name": "Revenue", "raw_value": "₹36,465 Mn", "normalized_value": 36465, "unit": "INR Mn", "timeframe": "FY21", "evidence": {"doc_name": "01-delhivery-prospectus-2022.pdf", "page_number": 45, "verbatim_quote": "Revenue for Fiscal 2021 was ₹36,465 million."}}
    f2 = {"fact_id": "d2", "metric_name": "Revenue", "raw_value": "₹81,417 Mn", "normalized_value": 81417, "unit": "INR Mn", "timeframe": "FY24", "evidence": {"doc_name": "02-delhivery-annual-report-fy24.pdf", "page_number": 2, "verbatim_quote": "Revenue reached ₹81,417 million in FY24."}}
    f3 = {"fact_id": "d3", "metric_name": "Express Parcel Volume", "raw_value": "740 Mn Shipments", "normalized_value": 740, "unit": "Mn Shipments", "timeframe": "FY24", "evidence": {"doc_name": "02-delhivery-annual-report-fy24.pdf", "page_number": 2, "verbatim_quote": "Delivered 740 million express parcel shipments."}}
    f4 = {"fact_id": "d4", "metric_name": "Express Parcel Volume", "raw_value": "740 Mn Shipments", "normalized_value": 740, "unit": "Mn Shipments", "timeframe": "FY24", "evidence": {"doc_name": "03-delhivery-q4-fy24-earnings.pdf", "page_number": 14, "verbatim_quote": "FY24 volume stood at 740 Mn shipments."}}
    f5 = {"fact_id": "d5", "metric_name": "Workforce", "raw_value": "30,524 Employees", "normalized_value": 30524, "unit": "Persons", "timeframe": "FY24", "evidence": {"doc_name": "02-delhivery-annual-report-fy24.pdf", "page_number": 4, "verbatim_quote": "Direct workforce stood at 30,524 employees."}}
    f6 = {"fact_id": "d6", "metric_name": "Workforce", "raw_value": "87,422 Personnel", "normalized_value": 87422, "unit": "Persons", "timeframe": "FY24", "evidence": {"doc_name": "02-delhivery-annual-report-fy24.pdf", "page_number": 52, "verbatim_quote": "Total active personnel reached 87,422."}}

    return {
        "dataset_id": "delhivery", "facts_extracted_count": 6, "reconciled_cases_count": 3,
        "cases": {
            C1: [{"relation_id": "dc1", "case_type": C1, "fact_a": f3, "fact_b": f4, "title": "Matching Express Parcel Volume (FY24)", "reasoning": "Both Annual Report and Earnings Presentation state 740 Mn shipments for FY24."}],
            C2: [{"relation_id": "dc2", "case_type": C2, "fact_a": f5, "fact_b": f6, "title": "Conflict in Workforce Count (FY24)", "reasoning": "Page 4 states 30,524 direct employees; Page 52 states 87,422 total personnel."}],
            C3: [{"relation_id": "dc3", "case_type": C3, "fact_a": f1, "fact_b": f2, "title": "Revenue Growth (FY21 vs FY24)", "reasoning": "₹36,465 Mn (FY21) vs ₹81,417 Mn (FY24) — growth over 3 years."}],
            C4: []
        },
        "facts": [f1, f2, f3, f4, f5, f6]
    }

@app.get("/")
def home(): return FileResponse(str(STATIC_DIR / "index.html"))

@app.get("/api/analysis/{dataset_id}")
def get_analysis(dataset_id: str): return get_demo_data()

@app.post("/api/upload")
def upload_pdf(file: UploadFile = File(...)):
    save_path = UPLOAD_DIR / file.filename
    with open(save_path, "wb") as buffer: buffer.write(file.file.read())
    return extract_pdf_data(str(save_path), file.filename)
