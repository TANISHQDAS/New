import re
import uuid
from typing import List, Dict, Any
from models import Fact, SourceEvidence

class FactExtractor:
    """Extracts numerical facts from financial/business PDFs."""

    # Each pattern: named metric, regex that captures (value, optional_unit)
    # Patterns require the value to come AFTER a currency or clear numeric context
    # to avoid matching bare year numbers like "FY24"
    METRIC_PATTERNS = [
        {
            "name": "Revenue",
            "regex": r"(?:revenue from operations|total revenue|sales revenue|net revenue|revenue)[^\n]{0,60}?(?:rs\.?|inr|usd|\$|rs)\s*([\d,]+\.?\d*)\s*(cr|crore|crores|mn|million|billion|lakh|lakhs)?",
            "unit_default": "INR Cr",
            "tags": ["financial", "revenue"]
        },
        {
            "name": "Net Profit",
            "regex": r"(?:net profit|profit after tax|pat|net income)[^\n]{0,60}?(?:rs\.?|inr|\$)\s*([\d,]+\.?\d*)\s*(cr|crore|crores|mn|million|billion|lakh|lakhs)?",
            "unit_default": "INR Cr",
            "tags": ["financial", "profit"]
        },
        {
            "name": "EBITDA",
            "regex": r"(?:ebitda|operating profit)[^\n]{0,60}?(?:rs\.?|inr|\$)\s*([\d,]+\.?\d*)\s*(cr|crore|crores|mn|million|billion|lakh|lakhs)?",
            "unit_default": "INR Cr",
            "tags": ["financial", "ebitda"]
        },
        {
            "name": "Total Assets",
            "regex": r"(?:total assets?)[^\n]{0,60}?(?:rs\.?|inr|\$)\s*([\d,]+\.?\d*)\s*(cr|crore|crores|mn|million|billion|lakh|lakhs)?",
            "unit_default": "INR Cr",
            "tags": ["financial", "assets"]
        },
        {
            "name": "Market Capitalization",
            "regex": r"(?:market cap(?:ital(?:isation|ization)?)?)[^\n]{0,60}?(?:rs\.?|inr|\$)\s*([\d,]+\.?\d*)\s*(cr|crore|crores|mn|million|billion|lakh)?",
            "unit_default": "INR Cr",
            "tags": ["financial", "market_cap"]
        },
        {
            "name": "Earnings Per Share",
            "regex": r"(?:eps|earnings per share|basic eps|diluted eps)[^\n]{0,60}?(?:rs\.?|inr|\$)\s*([\d,]+\.?\d*)",
            "unit_default": "INR per Share",
            "tags": ["financial", "eps"]
        },
        {
            "name": "Debt / Borrowings",
            "regex": r"(?:total debt|borrowings|long.term debt|short.term debt|outstanding debt)[^\n]{0,60}?(?:rs\.?|inr|\$)\s*([\d,]+\.?\d*)\s*(cr|crore|crores|mn|million|billion|lakh)?",
            "unit_default": "INR Cr",
            "tags": ["financial", "debt"]
        },
        {
            "name": "Return on Equity",
            "regex": r"(?:roe|return on equity)\s+(?:for\s+\w+\s+)?(?:was|is|stood at|of)?\s*([\d\.]+)\s*(?:%|percent|per cent)",
            "unit_default": "%",
            "tags": ["financial", "roe"]
        },
        {
            "name": "Workforce / Headcount",
            "regex": r"(?:total employees|full-time employees|workforce|headcount|total personnel|contractual staff)[^\n]{0,40}?:\s*([\d,]+)\s*(?:employees|persons|people|members|staff)?",
            "unit_default": "Persons",
            "tags": ["hr", "workforce"]
        },
        {
            "name": "Shipment / Volume",
            "regex": r"(?:total shipments|shipments delivered|parcels delivered)[^\n]{0,30}?:\s*([\d,]+\.?\d*)\s*(mn|million|cr|crore|lakh|billion)?",
            "unit_default": "Units",
            "tags": ["operational", "volume"]
        },
        {
            "name": "Interest Rate",
            "regex": r"(?:interest rate|repo rate|lending rate|borrowing rate)[^\n]{0,40}?:\s*([\d\.]+)\s*(?:%|percent|per cent)",
            "unit_default": "%",
            "tags": ["financial", "interest"]
        },
        {
            "name": "GDP Growth Rate",
            "regex": r"(?:gdp growth|real gdp|economic growth)[^\n]{0,30}?([\d\.]+)\s*(?:%|percent|per cent)",
            "unit_default": "%",
            "tags": ["macroeconomy", "gdp"]
        },
        {
            "name": "Inflation Rate",
            "regex": r"(?:cpi inflation|wpi inflation|headline inflation|retail inflation)[^\n]{0,30}?([\d\.]+)\s*(?:%|percent|per cent)",
            "unit_default": "%",
            "tags": ["macroeconomy", "inflation"]
        },
        {
            "name": "Foreign Exchange Reserves",
            "regex": r"(?:forex reserves|foreign exchange reserves|gross international reserves)[^\n]{0,30}?(?:usd|us\$|\$)?\s*([\d,]+\.?\d*)\s*(billion|b|mn|million)?",
            "unit_default": "USD Billion",
            "tags": ["macroeconomy", "forex"]
        }
    ]

    PERIOD_PATTERNS = [
        (r"\bq4\s*fy\s*25\b|\bq4\s*2024[-–]25\b", "Q4 FY25"),
        (r"\bq4\s*fy\s*24\b|\bq4\s*2023[-–]24\b|q4fy24", "Q4 FY24"),
        (r"\bq3\s*fy\s*24\b|\bq3\s*2023[-–]24\b", "Q3 FY24"),
        (r"\bq2\s*fy\s*24\b|\bq2\s*2023[-–]24\b", "Q2 FY24"),
        (r"\bq1\s*fy\s*24\b|\bq1\s*2023[-–]24\b", "Q1 FY24"),
        (r"\bfy\s*25\b|2024[-–]25\b|fiscal\s+2025", "FY25"),
        (r"\bfy\s*24\b|2023[-–]24\b|fiscal\s+2024|fy2024", "FY24"),
        (r"\bfy\s*23\b|2022[-–]23\b|fiscal\s+2023|fy2023", "FY23"),
        (r"\bfy\s*22\b|2021[-–]22\b|fiscal\s+2022|fy2022", "FY22"),
        (r"\bfy\s*21\b|2020[-–]21\b|fiscal\s+2021|fy2021", "FY21"),
        (r"\bmarch\s+2024\b|\bmar[-–]24\b", "March 2024"),
        (r"\bmarch\s+2023\b|\bmar[-–]23\b", "March 2023"),
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
            mult = (multiplier_unit or "").lower().strip()
            if "lakh" in mult:
                return round(num / 100.0, 4)   # lakhs -> crores
            elif "cr" in mult or "crore" in mult:
                return num
            elif "mn" in mult or "million" in mult:
                return round(num / 10.0, 4)    # millions -> crores
            elif "billion" in mult or mult == "b":
                return round(num * 100.0, 4)   # billions -> crores
            return num
        except ValueError:
            return 0.0

    @classmethod
    def guess_entity(cls, doc_name: str) -> str:
        name_lower = doc_name.lower()
        if "delhivery" in name_lower:
            return "Delhivery Limited"
        if "rbi" in name_lower or "reserve bank" in name_lower:
            return "Reserve Bank of India"
        if "imf" in name_lower:
            return "IMF"
        if "economic survey" in name_lower or "ministry" in name_lower:
            return "Indian Economy"
        # Use first 3 words from filename as entity name
        words = re.findall(r"[a-zA-Z]+", doc_name)
        return " ".join(w.capitalize() for w in words[:3]) if words else doc_name

    @classmethod
    def extract_facts_from_pages(cls, doc_name: str, pages_data: List[Dict[str, Any]]) -> List[Fact]:
        facts = []
        seen = set()
        entity = cls.guess_entity(doc_name)

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

                        # Skip obviously wrong small numbers (year fragments like "23", "24")
                        if norm_val < 1.0 and pat["unit_default"] not in ("%", "INR per Share"):
                            continue
                        if norm_val == 0.0:
                            continue

                        period = cls.detect_period(line)

                        raw_value_str = raw_val.replace(",", "")
                        if mult:
                            raw_value_str = f"{raw_val} {mult.capitalize()}"

                        dedup_key = (pat["name"], raw_value_str.strip(), period)
                        if dedup_key in seen:
                            continue
                        seen.add(dedup_key)

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
                            raw_value=raw_value_str.strip(),
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
