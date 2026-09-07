from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum

class CaseType(str, Enum):
    CORROBORATED = "Case 1: Corroborated Fact"
    GENUINE_CONTRADICTION = "Case 2: Genuine Contradiction"
    RECONCILED_CONTRADICTION = "Case 3: Apparent Contradiction (Reconciled by Context)"
    EXTRACTION_FAILURE = "Case 4: Extraction/Reasoning Failure & Mitigation"

class SourceEvidence(BaseModel):
    doc_id: str
    doc_name: str
    page_number: int
    verbatim_quote: str
    section_title: Optional[str] = "General Document Body"
    context_snippet: Optional[str] = None

class Fact(BaseModel):
    fact_id: str
    entity: str
    metric_name: str
    raw_value: str
    normalized_value: float
    unit: str
    timeframe: str
    scope: str = "Consolidated"
    evidence: SourceEvidence
    confidence: float = 0.95
    tags: List[str] = []

class ReconciliationRelation(BaseModel):
    relation_id: str
    case_type: CaseType
    fact_a: Fact
    fact_b: Optional[Fact] = None
    title: str
    summary: str
    reasoning: str
    reconciliation_factors: List[str] = []
    source_documents: List[str]
    confidence: float = 0.90
    handling_strategy: Optional[str] = None  # For Case 4

class DatasetSummary(BaseModel):
    dataset_id: str
    title: str
    description: str
    doc_count: int
    documents: List[str]

class AnalysisResponse(BaseModel):
    student_name: str = "Abhi Pandey"
    student_id: str = "23BAI10909"
    dataset_id: str
    facts_extracted_count: int
    reconciled_cases_count: int
    cases: Dict[str, List[ReconciliationRelation]]
    facts: List[Fact]
