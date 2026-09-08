import re, shutil, tempfile, pypdf
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

STATIC = Path(__file__).parent / "static"
UPLOADS = Path(tempfile.gettempdir()) / "uploads"
UPLOADS.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")

C_CORR = "Case 1: Corroborated Fact"
C_GEN  = "Case 2: Genuine Contradiction"
C_REC  = "Case 3: Apparent Contradiction (Reconciled by Context)"
C_FAIL = "Case 4: Extraction/Reasoning Failure & Mitigation"

# Broad extraction patterns covering major & minor numerical facts across any PDF
PATTERNS = [
    ("Revenue / Income", r"(?:revenue|sales|income|turnover|earnings)[^\n]{0,50}?(?:rs\.?|inr|\$|€|£)?\s*([\d,]+\.?\d*)\s*(cr|crore|mn|million|billion|lakh)?", "Currency"),
    ("Profit / PAT", r"(?:net profit|pat|profit|margin)[^\n]{0,50}?(?:rs\.?|inr|\$|€|£)?\s*([\d,]+\.?\d*)\s*(cr|crore|mn|million|billion|lakh)?", "Currency"),
    ("EBITDA / Operating Profit", r"(?:ebitda|operating profit)[^\n]{0,50}?(?:rs\.?|inr|\$|€|£)?\s*([\d,]+\.?\d*)\s*(cr|crore|mn|million)?", "Currency"),
    ("Workforce / Employees", r"(?:employees|workforce|personnel|staff|headcount)[^\n]{0,40}?:\s*([\d,]+)", "Persons"),
    ("Volume / Shipments", r"(?:shipments|parcels|units|volume|quantity)[^\n]{0,30}?:\s*([\d,]+\.?\d*)\s*(mn|million|cr|lakh)?", "Units"),
    ("Total Assets / Capital", r"(?:total assets|assets|capital|investment)[^\n]{0,50}?(?:rs\.?|inr|\$|€|£)?\s*([\d,]+\.?\d*)\s*(cr|crore|mn|million|billion)?", "Currency"),
    ("Debt / Liabilities", r"(?:debt|borrowings|liabilities)[^\n]{0,50}?(?:rs\.?|inr|\$|€|£)?\s*([\d,]+\.?\d*)\s*(cr|crore|mn|million|billion)?", "Currency"),
    ("Rate / Percentage", r"(?:rate|percentage|growth|inflation|gdp|roi|roe|interest|share)[^\n]{0,40}?:\s*([\d\.]+)\s*(?:%|percent)", "%"),
    ("General Metric / Value", r"([a-zA-Z\s]{3,25})\s*[:=]\s*(?:rs\.?|inr|\$|€|£)?\s*([\d,]+\.?\d*)\s*(cr|crore|mn|million|billion|%|units|kg|m)?", "Value")
]

PERIOD_PATTERNS = [
    (r"q[1-4]\s*fy\s*\d{2,4}", lambda m: m.group(0).upper()),
    (r"fy\s*\d{2,4}|20\d{2}[-–]\d{2,4}", lambda m: m.group(0).upper()),
    (r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+20\d{2}", lambda m: m.group(0).title()),
    (r"20\d{2}", lambda m: m.group(0))
]

def parse_num(val, mult=""):
    try:
        n = float(str(val).replace(",", "").strip())
        m = (mult or "").lower().strip()
        if "lakh" in m: return round(n / 100, 4)
        if "mn" in m or "million" in m: return round(n / 10, 4)
        if "billion" in m or m == "b": return round(n * 100, 4)
        return n
    except:
        return 0.0

def detect_period(text):
    for pat, formatter in PERIOD_PATTERNS:
        m = re.search(pat, text, re.IGNORECASE)
        if m: return formatter(m)
    return "N/A"

def process_pdf(pdf_path, filename):
    try:
        reader = pypdf.PdfReader(pdf_path)
    except Exception as e:
        return {"dataset_id": f"upload-{filename}", "facts_extracted_count": 0, "reconciled_cases_count": 1,
                "cases": {C_CORR:[], C_GEN:[], C_REC:[], C_FAIL:[{"relation_id":"r-fail","case_type":C_FAIL,"fact_a":None,"title":"Unreadable PDF","reasoning":str(e)}]}, "facts":[]}

    facts, seen = [], set()

    for idx, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        for line in text.split("\n"):
            line_str = line.strip()
            if not line_str or len(line_str) < 5: continue
            ll = line_str.lower()

            for name, reg, unit in PATTERNS:
                m = re.search(reg, ll)
                if m:
                    if name == "General Metric / Value":
                        label_raw, raw_val = m.group(1).strip().title(), m.group(2)
                        mult = m.group(3) if len(m.groups()) >= 3 and m.group(3) else ""
                        metric_name = f"Metric: {label_raw}"
                    else:
                        raw_val = m.group(1)
                        mult = m.group(2) if len(m.groups()) >= 2 and m.group(2) else ""
                        metric_name = name

                    norm = parse_num(raw_val, mult)
                    if norm <= 0: continue
                    period = detect_period(line_str)
                    raw_str = f"{raw_val} {mult}".strip() if mult else raw_val
                    key = (metric_name, raw_str, period)

                    if key in seen: continue
                    seen.add(key)

                    facts.append({
                        "fact_id": f"f-{len(facts)+1}",
                        "metric_name": metric_name,
                        "raw_value": raw_str,
                        "normalized_value": norm,
                        "unit": unit,
                        "timeframe": period,
                        "evidence": {"doc_name": filename, "page_number": idx + 1, "verbatim_quote": line_str[:200]}
                    })

    cases = {C_CORR: [], C_GEN: [], C_REC: [], C_FAIL: []}
    grouped = {}
    for f in facts: grouped.setdefault(f["metric_name"], []).append(f)

    rel_id = 1
    # Check metric pairs for cases
    for metric, lst in grouped.items():
        if len(lst) < 2: continue
        for i in range(len(lst)):
            for j in range(i + 1, len(lst)):
                a, b = lst[i], lst[j]
                if a["evidence"]["page_number"] == b["evidence"]["page_number"]: continue
                src_a, src_b = f"Page {a['evidence']['page_number']}", f"Page {b['evidence']['page_number']}"
                same_period = (a["timeframe"] == b["timeframe"]) and a["timeframe"] != "N/A"
                same_val = abs(a["normalized_value"] - b["normalized_value"]) < 0.05 * max(a["normalized_value"], b["normalized_value"], 1.0)

                if same_period and same_val:
                    cases[C_CORR].append({"relation_id": f"r-{rel_id}", "case_type": C_CORR, "fact_a": a, "fact_b": b, "title": f"Matching {metric} ({a['timeframe']})", "reasoning": f"{metric} = {a['raw_value']} matched in {src_a} and {src_b}."})
                elif same_period and not same_val:
                    cases[C_GEN].append({"relation_id": f"r-{rel_id}", "case_type": C_GEN, "fact_a": a, "fact_b": b, "title": f"Conflict in {metric} ({a['timeframe']})", "reasoning": f"{metric} for {a['timeframe']}: {a['raw_value']} ({src_a}) vs {b['raw_value']} ({src_b})."})
                else:
                    cases[C_REC].append({"relation_id": f"r-{rel_id}", "case_type": C_REC, "fact_a": a, "fact_b": b, "title": f"{metric}: {a['timeframe']} vs {b['timeframe']}", "reasoning": f"{a['raw_value']} ({src_a}, {a['timeframe']}) vs {b['raw_value']} ({src_b}, {b['timeframe']}) — reconciled by context."})
                rel_id += 1

    # Cross-metric context reconciliation if no direct metric duplicates
    if len(facts) >= 2 and sum(len(v) for v in cases.values()) == 0:
        a, b = facts[0], facts[1]
        cases[C_REC].append({
            "relation_id": "r-1", "case_type": C_REC, "fact_a": a, "fact_b": b,
            "title": f"Context Comparison: {a['metric_name']} vs {b['metric_name']}",
            "reasoning": f"{a['metric_name']} ({a['raw_value']}, Page {a['evidence']['page_number']}) vs {b['metric_name']} ({b['raw_value']}, Page {b['evidence']['page_number']}) — different metrics & context."
        })

    if not facts:
        cases[C_FAIL].append({
            "relation_id": "r-fail", "case_type": C_FAIL,
            "fact_a": {"fact_id": "nf", "metric_name": "None", "raw_value": "N/A", "normalized_value": 0, "unit": "N/A", "timeframe": "N/A", "evidence": {"doc_name": filename, "page_number": 1, "verbatim_quote": "No numerical facts found."}},
            "title": f"No Numerical Facts Found in {filename}", "reasoning": "Document contains scanned images or non-numerical text layer."
        })

    return {"dataset_id": f"upload-{filename}", "facts_extracted_count": len(facts), "reconciled_cases_count": sum(len(v) for v in cases.values()), "cases": cases, "facts": facts}

def delhivery_demo():
    f1 = {"fact_id":"d1","metric_name":"Revenue","raw_value":"₹36,465 Mn","normalized_value":36465,"unit":"INR Mn","timeframe":"FY21","evidence":{"doc_name":"01-delhivery-prospectus-2022.pdf","page_number":45,"verbatim_quote":"Revenue for Fiscal 2021 was ₹36,465 million."}}
    f2 = {"fact_id":"d2","metric_name":"Revenue","raw_value":"₹81,417 Mn","normalized_value":81417,"unit":"INR Mn","timeframe":"FY24","evidence":{"doc_name":"02-delhivery-annual-report-fy24.pdf","page_number":2,"verbatim_quote":"Revenue reached ₹81,417 million in FY24."}}
    f3 = {"fact_id":"d3","metric_name":"Express Parcel Volume","raw_value":"740 Mn Shipments","normalized_value":740,"unit":"Mn Shipments","timeframe":"FY24","evidence":{"doc_name":"02-delhivery-annual-report-fy24.pdf","page_number":2,"verbatim_quote":"Delivered 740 million express parcel shipments."}}
    f4 = {"fact_id":"d4","metric_name":"Express Parcel Volume","raw_value":"740 Mn Shipments","normalized_value":740,"unit":"Mn Shipments","timeframe":"FY24","evidence":{"doc_name":"03-delhivery-q4-fy24-earnings.pdf","page_number":14,"verbatim_quote":"FY24 volume stood at 740 Mn shipments."}}
    f5 = {"fact_id":"d5","metric_name":"Workforce","raw_value":"30,524 Employees","normalized_value":30524,"unit":"Persons","timeframe":"FY24","evidence":{"doc_name":"02-delhivery-annual-report-fy24.pdf","page_number":4,"verbatim_quote":"Direct workforce stood at 30,524 employees."}}
    f6 = {"fact_id":"d6","metric_name":"Workforce","raw_value":"87,422 Personnel","normalized_value":87422,"unit":"Persons","timeframe":"FY24","evidence":{"doc_name":"02-delhivery-annual-report-fy24.pdf","page_number":52,"verbatim_quote":"Total active personnel reached 87,422."}}
    
    return {
        "dataset_id": "delhivery", "facts_extracted_count": 6, "reconciled_cases_count": 3,
        "cases": {
            C_CORR: [{"relation_id":"dc1","case_type":C_CORR,"fact_a":f3,"fact_b":f4,"title":"Matching Express Parcel Volume (FY24)","reasoning":"Both annual report and earnings presentation confirm 740 Mn shipments."}],
            C_GEN:  [{"relation_id":"dc2","case_type":C_GEN,"fact_a":f5,"fact_b":f6,"title":"Conflict in Workforce Count (FY24)","reasoning":"Page 4 states 30,524 direct employees; Page 52 states 87,422 total personnel."}],
            C_REC:  [{"relation_id":"dc3","case_type":C_REC,"fact_a":f1,"fact_b":f2,"title":"Revenue: FY21 vs FY24","reasoning":"₹36,465 Mn (FY21) vs ₹81,417 Mn (FY24) — growth over time."}],
            C_FAIL: []
        },
        "facts": [f1, f2, f3, f4, f5, f6]
    }

@app.get("/")
def index(): return FileResponse(str(STATIC / "index.html"))

@app.get("/api/analysis/{dataset_id}")
def get_analysis(dataset_id: str): return delhivery_demo()

@app.post("/api/upload")
def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"): raise HTTPException(400, "PDF only")
    path = UPLOADS / file.filename
    with open(path, "wb") as f: shutil.copyfileobj(file.file, f)
    return process_pdf(str(path), file.filename)
