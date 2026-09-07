import re
import uuid
from typing import List, Dict, Any
from models import Fact, SourceEvidence

class FactExtractor:
    """Extracts typed numerical and semantic facts from page text data."""

    METRIC_PATTERNS = [
        {
            "name": "Revenue from Operations",
            "regex": r"(?:revenue\s+from\s+operations|total\ revenue|sales\ revenue)\s*(?:of|was|reached|stood\ at)?\s*[\u20b9₹\$]?\s*([\d\.\,]+)\s*(cr|crore|crores|mn|million|billion|b)?",
            "unit_default": "INR Million",
            "tags": ["financial", "revenue"]
        },
        {
            "name": "Real GDP Growth Rate",
            "regex": r"(?:real\ gdp\ growth|gdp\ growth\ rate|gdp\ growth)\s*(?:projected|estimated|at|was)?\s*([\d\.]+)\s*(?:%|percent|per\ cent)",
            "unit_default": "%",
            "tags": ["macroeconomy", "gdp"]
        },
        {
            "name": "Headline CPI Inflation",
            "regex": r"(?:cpi\ inflation|headline\ inflation|retail\ inflation)\s*(?:averaged|declined\ to|projected\ at|was)?\s*([\d\.]+)\s*(?:%|percent|per\ cent)",
            "unit_default": "%",
            "tags": ["macroeconomy", "inflation"]
        },
        {
            "name": "Express Parcel Shipments Volume",
            "regex": r"(?:express\ parcel\ volume|delivered|shipments)\s*(?:of|was|reached)?\s*([\d\.\,]+)\s*(mn|million|crore|cr)?\s*(?:shipments|parcels)?",
            "unit_default": "Million Shipments",
            "tags": ["operational", "volume"]
        },
        {
            "name": "PIN Code Coverage",
            "regex": r"(?:pin\ code\ reach|serviced|covering)\s*([\d\.\,]+)\s*(?:pin\ codes)?",
            "unit_default": "PIN Codes",
            "tags": ["operational", "reach"]
        },
        {
            "name": "Foreign Exchange Reserves",
            "regex": r"(?:forex\ reserves|foreign\ exchange\ reserves)\s*(?:stood\ at|reached|was)?\s*[\$₹]?\s*([\d\.\,]+)\s*(billion|b|mn|million)?",
            "unit_default": "USD Billion",
            "tags": ["macroeconomy", "forex"]
        }
    ]

    @classmethod
    def parse_number(cls, val_str: str, multiplier_unit: str = "") -> float:
        clean = val_str.replace(",", "").strip()
        try:
            num = float(clean)
            mult = multiplier_unit.lower()
            if "cr" in mult or "crore" in mult:
                return num * 10.0  # converted to millions or kept standard
            elif "billion" in mult or "b" in mult:
                return num * 1000.0
            return num
        except ValueError:
            return 0.0

    @classmethod
    def extract_facts_from_pages(cls, doc_name: str, pages_data: List[Dict[str, Any]]) -> List[Fact]:
        facts = []
        for page in pages_data:
            page_num = page["page_number"]
            text = page["text"]
            lines = page["lines"]

            for line in lines:
                line_lower = line.lower()
                for pat in cls.METRIC_PATTERNS:
                    m = re.search(pat["regex"], line_lower)
                    if m:
                        raw_val = m.group(1)
                        mult = m.group(2) if len(m.groups()) >= 2 and m.group(2) else ""
                        norm_val = cls.parse_number(raw_val, mult)

                        # Detect period
                        period = "FY24"
                        if "fy25" in line_lower or "2024-25" in line_lower or "2025" in line_lower:
                            period = "FY25"
                        elif "fy23" in line_lower or "2022-23" in line_lower:
                            period = "FY23"
                        elif "fy21" in line_lower or "fiscal 2021" in line_lower:
                            period = "FY21"

                        evidence = SourceEvidence(
                            doc_id=doc_name.lower().replace(" ", "-"),
                            doc_name=doc_name,
                            page_number=page_num,
                            verbatim_quote=line[:200],
                            section_title=f"Page {page_num} Extraction",
                            context_snippet=line
                        )

                        fact = Fact(
                            fact_id=f"fact-{uuid.uuid4().hex[:8]}",
                            entity="Delhivery Limited" if "delhivery" in doc_name.lower() else "Indian Economy",
                            metric_name=pat["name"],
                            raw_value=f"{raw_val} {mult}".strip(),
                            normalized_value=norm_val,
                            unit=pat["unit_default"],
                            timeframe=period,
                            scope="Consolidated",
                            evidence=evidence,
                            confidence=0.92,
                            tags=pat["tags"]
                        )
                        facts.append(fact)
        return facts
