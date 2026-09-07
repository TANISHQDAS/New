# ⚡ Fact Knowledge Layer Engine

> **Superjoin Engineering Intern Hiring Assignment (VIT 2026)**  
> **Candidate:** Abhi Pandey  
> **Registration Number:** 23BAI10909  
> **Dataset Path:** `C:\Users\tanis\Downloads\QB1-main\starter-datasets`  
> **UI Theme:** AWS CloudScape Console Theme (Squid Ink Navy `#232f3e` & AWS Orange `#FF9900`)

---

## 📌 Executive Overview

Important facts in corporate filings and macroeconomic reports are often scattered across documents, stated in different ways, supported by corroborating evidence, or contradicted elsewhere.

This project implements a complete **Fact Knowledge Layer System** that:
1. **Extracts** structured numerical and semantic facts from unstructured PDF documents.
2. **Grounds & Links** every extracted fact to source evidence (verbatim text quote, page number, document name).
3. **Reconciles & Classifies** cross-document relationships into the four required Superjoin assignment cases:
   - **Case 1: Corroborated Fact Across Documents**
   - **Case 2: Genuine or Likely Contradiction**
   - **Case 3: Apparent Contradiction Reconciled by Context** (Time, Scope, Units)
   - **Case 4: Extraction/Reasoning Failure & Automated Mitigation**

---

## 🚀 Setup and Run Instructions

### Prerequisites
- Python 3.10+
- Internet connection (for initial package downloads if needed)

### Quickstart Command

```bash
# 1. Navigate to project root directory
cd C:\Users\tanis\.gemini\antigravity\scratch\fact-knowledge-layer

# 2. Run the FastAPI Server
python main.py
```

Open your browser and navigate to:
👉 **[http://127.0.0.1:8000](http://127.0.0.1:8000)**

---

## 🎥 Video Demo

- **Video Demo Link:** `[Insert YouTube / Loom / Drive Demo Video Link Here]` *(Duration: < 3 minutes)*
- **Demo Script Highlights:**
  1. **0:00 - 0:30**: Introduction to the AWS-styled interface by Abhi Pandey (23BAI10909) and dataset loading from `C:\Users\tanis\Downloads\QB1-main\starter-datasets`.
  2. **0:30 - 1:15**: Demonstration of **Case 1 (Corroborated Express Parcel Volume / CPI Inflation)** and **Case 2 (Genuine Contradiction in Workforce Count & RBI vs IMF GDP Projections)**.
  3. **1:15 - 2:00**: Demonstration of **Case 3 (Apparent Contradiction Reconciled by Context)** showing FY21 vs FY24 vs Q4 FY24 revenue scaling.
  4. **2:00 - 2:30**: Demonstration of **Case 4 (Extraction/Reasoning Failure Mitigation)** showing how multi-page footnote dissociation is flagged and resolved.
  5. **2:30 - 3:00**: Real-time PDF Upload demonstration with arbitrary document processing.

---

## 🧠 Approach & Architecture

### System Pipeline

```
┌────────────────────────┐      ┌─────────────────────────┐      ┌──────────────────────────┐
│   PDF Source Upload    │ ───► │  Structure-Aware Parser │ ───► │ Fact Extractor & Scoper  │
│ (Delhivery / Macro /   │      │ (pdfplumber + pypdf)    │      │ (Regex + Semantic Engine)│
│ Custom User Upload)    │      └─────────────────────────┘      └──────────────────────────┘
└────────────────────────┘                                                    │
                                                                              ▼
┌────────────────────────┐      ┌─────────────────────────┐      ┌──────────────────────────┐
│  AWS CloudScape UI     │ ◄─── │  REST API (FastAPI)     │ ◄─── │ Cross-Doc Reconciler     │
│ (Abhi Pandey 23BAI10909│      │  JSON Analysis Server   │      │ (4 Superjoin Cases Engine│
└────────────────────────┘      └─────────────────────────┘      └──────────────────────────┘
```

### Key Engineering Decisions & Trade-Offs

1. **Deterministic Grounding vs Hallucination Risks**:
   - *Decision:* Every extracted fact is strictly bound to a `SourceEvidence` object containing `page_number`, `verbatim_quote`, `document_id`, and `context_snippet`.
   - *Trade-off:* Avoids ungrounded LLM hallucinated facts while providing 100% auditability for reviewers.

2. **Contextual Disambiguation Engine (Case 3)**:
   - *Decision:* Implemented automatic normalization for reporting windows (FY21 vs FY24 vs Q4), accounting scales (INR Millions vs INR Crores), and entity scopes (Direct Payroll vs Total Active Personnel).
   - *Trade-off:* Prevents false positive contradiction alerts when figures naturally differ due to temporal growth or unit definitions.

3. **Footnote & Scope Discrepancy Flagging (Case 4)**:
   - *Decision:* When table extraction encounters unattached footnotes (e.g. ESOP exclusion notes on adjacent pages), the system assigns a lower confidence rating and logs a structured mitigation strategy.

---

## 📊 Grounded Demonstration of the 4 Cases

### Case 1: Corroborated Fact Across Documents
- **Fact:** FY24 Express Parcel Shipment Volume = **740 Million shipments**.
- **Document A:** `02-delhivery-annual-report-fy24-excerpt.pdf` (Page 2) - Quote: *"Express parcel volume reached 740 million shipments in FY24."*
- **Document B:** `03-delhivery-q4-fy24-earnings-presentation.pdf` (Page 14) - Quote: *"FY24 Express Parcel volume stood at 740 Mn shipments."*
- **Reasoning:** Identical values, identical time period (FY24), matching operational scope across independent disclosures.

### Case 2: Genuine Contradiction
- **Fact:** Direct GDP Growth Rate Projections for FY25 (India Macroeconomy).
- **Document A:** `02-rbi-annual-report-2024-25-excerpt.pdf` (Page 27) - Quote: *"Real GDP growth for 2024-25 is projected at 7.0 per cent."*
- **Document B:** `03-imf-india-2025-article-iv-excerpt.pdf` (Page 1) - Quote: *"Real GDP growth is estimated at 6.8 percent in FY2024/25."*
- **Reasoning:** Direct conflict (7.0% vs 6.8%) for the exact same fiscal period (FY25) between domestic central bank and international multilateral staff baseline models.

### Case 3: Apparent Contradiction Reconciled by Context
- **Fact:** Delhivery Revenue Figures (₹3,646.53 Cr vs ₹8,141.70 Cr vs ₹2,076 Cr).
- **Document A:** `01-delhivery-prospectus-2022-excerpt.pdf` (Page 45) - FY21 Revenue = **₹36,465.27 Million (₹3,646.53 Cr)**.
- **Document B:** `02-delhivery-annual-report-fy24-excerpt.pdf` (Page 2) - FY24 Revenue = **₹81,417 Million (₹8,141.70 Cr)**.
- **Document C:** `03-delhivery-q4-fy24-earnings-presentation.pdf` (Page 14) - Q4 FY24 Revenue = **₹2,076 Cr**.
- **Reasoning:** Reconciled by **Temporal Evolution** (3-year 123% compound business scaling) and **Reporting Horizon Scope** (Annual full-year vs single-quarter Q4).

### Case 4: Extraction/Reasoning Failure & Mitigation
- **Scenario:** Multi-Page Footnote Dissociation (Prospectus 2022, Page 44-45).
- **Issue:** PDF table parser extracts raw row `EBITDA: (1,003.79) Million` on Page 44, but misses Footnote (3) on Page 45 stating ESOP expenses are excluded.
- **Mitigation:** Enforces cross-page footnote binding heuristics. Flags raw fact with `confidence: 0.68`, normalizes metric tag to `Adjusted EBITDA (ex-ESOP)`, and prevents downstream reconciliation errors.

---

## 🛠️ Limitations and Next Steps

1. **Scanned PDF Support (OCR)**:
   - *Current Limitation:* Standard text extraction relies on embedded vector text. Scanned raster images require Tesseract / AWS Textract OCR.
   - *Next Step:* Integrate Tesseract OCR fallback for scanned legacy PDFs.

2. **Complex Multi-Header Table Resolution**:
   - *Current Limitation:* Nested multi-row table headers (e.g. nested sub-segment breakdowns) can occasionally blur metric boundaries.
   - *Next Step:* Implement graph-based layout parsing using layoutLM / pdfplumber spatial bounding boxes.

---

## 📝 Additional Notes

- **Author:** Abhi Pandey (23BAI10909)
- **Institution:** VIT
- **Target Role:** Superjoin Engineering Intern (2026 Batch)
- **UI Design System:** Custom AWS CloudScape theme implementation featuring Amazon Ember typography, Squid Ink header (#232f3e), and AWS Orange highlights (#FF9900).
