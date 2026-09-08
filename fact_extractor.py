import re
import uuid
from typing import List, Dict, Any
from models import Fact, SourceEvidence

class FactExtractor:
    """Extracts numerical facts from any financial/business PDF using broad regex patterns."""

    # Broad patterns that match common financial metrics in any PDF
    METRIC_PATTERNS = [
        {
            "name": "Revenue",
            "regex": r"(?:revenue|sales|turnover|income from operations|total income)[^\n]{0,40}?[₹\$]?\s*([\d,]+\.?\d*)\s*(cr|crore|crores|mn|million|billion|lakh|lakhs|b|k)?",
            "unit_default": "INR",
            "tags": ["financial", "revenue"]
        },
        {
            "name": "Net Profit / Loss",
            "regex": r"(?:net profit|net loss|profit after tax|pat|loss after tax)[^\n]{0,40}?[₹\$]?\s*([\d,]+\.?\d*)\s*(cr|crore|crores|mn|million|billion|lakh|lakhs)?",
            "unit_default": "INR",
            "tags": ["financial", "profit"]
        },
        {
            "name": "EBITDA",
            "regex": r"(?:ebitda|operating profit|operating income)[^\n]{0,40}?[₹\$]?\s*([\d,]+\.?\d*)\s*(cr|crore|crores|mn|million|billion|lakh|lakhs)?",
            "unit_default": "INR",
            "tags": ["financial", "ebitda"]
        },
        {
            "name": "Total Assets",
            "regex": r"(?:total assets|total asset)[^\n]{0,40}?[₹\$]?\s*([\d,]+\.?\d*)\s*(cr|crore|crores|mn|million|billion|lakh|lakhs)?",
            "unit_default": "INR",
            "tags": ["financial", "assets"]
        },
        {
            "name": "Market Capitalization",
            "regex": r"(?:market cap|market capitalisation|market capitalization)[^\n]{0,40}?[₹\$]?\s*([\d,]+\.?\d*)\s*(cr|crore|crores|mn|million|billion|lakh)?",
            "unit_default": "INR",
            "tags": ["financial", "market_cap"]
        },
        {
            "name": "Earnings Per Share",
            "regex": r"(?:eps|earnings per share|basic eps|diluted eps)[^\n]{0,40}?[₹\$]?\s*([\d,]+\.?\d*)",
            "unit_default": "INR per Share",
            "tags": ["financial", "eps"]
        },
        {
            "name": "Workforce / Headcount",
            "regex": r"(?:employees|workforce|headcount|staff|personnel|team members)[^\n]{0,40}?([\d,]+)\s*(?:employees|persons|people|members|staff)?",
            "unit_default": "Persons",
            "tags": ["hr", "workforce"]
        },
        {
            "name": "GDP Growth Rate",
            "regex": r"(?:gdp growth|real gdp|economic growth)[^\n]{0,30}?([\d\.]+)\s*(?:%|percent|per cent)",
            "unit_default": "%",
            "tags": ["macroeconomy", "gdp"]
        },
        {
            "name": "Inflation Rate",
            "regex": r"(?:inflation|cpi|wpi|price rise)[^\n]{0,30}?([\d\.]+)\s*(?:%|percent|per cent)",
            "unit_default": "%",
            "tags": ["macroeconomy", "inflation"]
        },
        {
            "name": "Interest Rate",
            "regex": r"(?:interest rate|repo rate|lending rate|borrowing rate|yield)[^\n]{0,30}?([\d\.]+)\s*(?:%|percent|per cent)",
            "unit_default": "%",
            "tags": ["financial", "interest"]
        },
        {
            "name": "Debt / Borrowings",
            "regex": r"(?:total debt|borrowings|long.term debt|short.term debt|outstanding debt)[^\n]{0,40}?[₹\$]?\s*([\d,]+\.?\d*)\s*(cr|crore|crores|mn|million|billion|lakh)?",
            "unit_default": "INR",
            "tags": ["financial", "debt"]
        },
        {
            "name": "Return on Equity",
            "regex": r"(?:roe|return on equity)[^\n]{0,30}?([\d\.]+)\s*(?:%|percent|per cent)",
            "unit_default": "%",
            "tags": ["financial", "roe"]
        },
        {
            "name": "Shipment / Volume",
            "regex": r"(?:shipments?|parcels?|orders?|deliveries|volume)[^\n]{0,30}?([\d,]+\.?\d*)\s*(mn|million|cr|crore|lakh|billion|k)?",
            "unit_default": "Units",
            "tags": ["operational", "volume"]
        }
    ]

    # Period detection patterns
    PERIOD_PATTERNS = [
        (r"\bfy\s?25\b|2024[-–]25\b|fiscal 2025", "FY25"),
        (r"\bfy\s?24\b|2023[-–]24\b|fiscal 2024|fy2024", "FY24"),
        (r"\bfy\s?23\b|2022[-–]23\b|fiscal 2023|fy2023", "FY23"),
        (r"\bfy\s?22\b|2021[-–]22\b|fiscal 2022|fy2022", "FY22"),
        (r"\bfy\s?21\b|2020[-–]21\b|fiscal 2021|fy2021", "FY21"),
        (r"\bq4\b.*\bfy\s?24\b|\bfy\s?24\b.*\bq4\b|q4 fy24|q4fy24", "Q4 FY24"),
        (r"\bq3\b.*\bfy\s?24\b|\bfy\s?24\b.*\bq3\b", "Q3 FY24"),
        (r"\bq2\b.*\bfy\s?24\b|\bfy\s?24\b.*\bq2\b", "Q2 FY24"),
        (r"\bq1\b.*\bfy\s?24\b|\bfy\s?24\b.*\bq1\b", "Q1 FY24"),
        (r"\b2024\b", "2024"),
        (r"\b2023\b", "2023"),
        (r"\b2022\b", "2022"),
    ]

    @classmethod
    def detect_period(cls, text: str) -> str:
        t = text.lower()
        for pattern, label in cls.PERIOD_PATTERNS:
            if re.search(pattern, t):
                return label
        return "N/A"

    @classmethod
    def parse_number(cls, val_str: str, multiplier_unit: str = "") -> float:
        clean = val_str.replace(",", "").strip()
        try:
            num = float(clean)
            mult = (multiplier_unit or "").lower()
            if "lakh" in mult:
                return num / 10.0  # lakhs to crores
            elif "cr" in mult or "crore" in mult:
                return num
            elif "mn" in mult or "million" in mult:
                return num / 10.0  # millions to crores approx
            elif "billion" in mult or "b" == mult:
                return num * 100.0
            return num
        except ValueError:
            return 0.0

    @classmethod
    def extract_facts_from_pages(cls, doc_name: str, pages_data: List[Dict[str, Any]]) -> List[Fact]:
        facts = []
        seen = set()  # deduplicate by (metric, value, period)

        for page in pages_data:
            page_num = page["page_number"]
            lines = page["lines"]

            for line in lines:
                line_lower = line.lower()
                for pat in cls.METRIC_PATTERNS:
                    m = re.search(pat["regex"], line_lower)
                    if m:
                        raw_val = m.group(1)
                        mult = m.group(2) if len(m.groups()) >= 2 and m.group(2) else ""
                        norm_val = cls.parse_number(raw_val, mult)

                        if norm_val == 0.0:
                            continue  # skip zero/unparseable values

                        period = cls.detect_period(line)

                        # Build readable raw value string
                        raw_value_str = raw_val
                        if mult:
                            raw_value_str = f"{raw_val} {mult.capitalize()}"

                        dedup_key = (pat["name"], raw_val, period)
                        if dedup_key in seen:
                            continue
                        seen.add(dedup_key)

                        # Guess entity from doc name or context
                        entity = "Unknown Entity"
                        if "delhivery" in doc_name.lower():
                            entity = "Delhivery Limited"
                        elif any(w in doc_name.lower() for w in ["rbi", "reserve bank"]):
                            entity = "Reserve Bank of India"
                        elif any(w in doc_name.lower() for w in ["imf", "international monetary"]):
                            entity = "IMF"
                        elif any(w in doc_name.lower() for w in ["economic survey", "ministry"]):
                            entity = "Indian Economy"
                        else:
                            # Try to guess from doc name words
                            words = re.findall(r"[a-zA-Z]+", doc_name)
                            entity = " ".join(w.capitalize() for w in words[:3]) if words else doc_name

                        evidence = SourceEvidence(
                            doc_id=doc_name.lower().replace(" ", "-"),
                            doc_name=doc_name,
                            page_number=page_num,
                            verbatim_quote=line[:250],
                            section_title=f"Page {page_num}",
                            context_snippet=line[:250]
                        )

                        fact = Fact(
                            fact_id=f"fact-{uuid.uuid4().hex[:8]}",
                            entity=entity,
                            metric_name=pat["name"],
                            raw_value=raw_value_str,
                            normalized_value=norm_val,
                            unit=pat["unit_default"],
                            timeframe=period,
                            scope="Extracted",
                            evidence=evidence,
                            confidence=0.85,
                            tags=pat["tags"]
                        )
                        facts.append(fact)

        return facts
