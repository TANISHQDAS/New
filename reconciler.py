from typing import List, Dict
from models import Fact, ReconciliationRelation, CaseType, SourceEvidence

class FactReconciler:
    """Compares facts across documents and classifies them into the 4 Superjoin assignment cases."""

    @staticmethod
    def reconcile_facts(facts: List[Fact]) -> List[ReconciliationRelation]:
        relations = []

        # Group by metric
        grouped: Dict[str, List[Fact]] = {}
        for f in facts:
            grouped.setdefault(f.metric_name, []).append(f)

        # Check if there's only one document — if so allow same-doc comparisons across pages
        all_docs = set(f.evidence.doc_name for f in facts)
        single_doc_mode = len(all_docs) <= 1

        for metric, fact_list in grouped.items():
            if len(fact_list) < 2:
                continue

            for i in range(len(fact_list)):
                for j in range(i + 1, len(fact_list)):
                    fa = fact_list[i]
                    fb = fact_list[j]

                    same_doc = fa.evidence.doc_name == fb.evidence.doc_name
                    same_page = fa.evidence.page_number == fb.evidence.page_number

                    # In multi-doc mode: only compare across different documents
                    # In single-doc mode: compare across different pages of the same document
                    if not single_doc_mode and same_doc:
                        continue
                    if single_doc_mode and same_page:
                        continue

                    # Check temporal or metric equivalence
                    same_period = (fa.timeframe == fb.timeframe)
                    same_val = abs(fa.normalized_value - fb.normalized_value) < 0.05 * max(fa.normalized_value, fb.normalized_value, 1.0)

                    src_a = f"Page {fa.evidence.page_number}" if single_doc_mode else fa.evidence.doc_name
                    src_b = f"Page {fb.evidence.page_number}" if single_doc_mode else fb.evidence.doc_name

                    if same_period and same_val:
                        # Case 1: Corroborated Fact
                        rel = ReconciliationRelation(
                            relation_id=f"rel-corr-{i}-{j}",
                            case_type=CaseType.CORROBORATED,
                            fact_a=fa,
                            fact_b=fb,
                            title=f"Corroborated {metric} ({fa.timeframe})",
                            summary=f"Both {src_a} and {src_b} report matching {metric} of {fa.raw_value}.",
                            reasoning=f"Identical {metric} values found for period {fa.timeframe}. Value A ({fa.raw_value}) from {src_a} equals Value B ({fb.raw_value}) from {src_b}.",
                            reconciliation_factors=["Source Alignment", "Identical Time Window", "Consistent Unit Scaling"],
                            source_documents=[fa.evidence.doc_name, fb.evidence.doc_name],
                            confidence=0.98
                        )
                        relations.append(rel)

                    elif not same_period and not same_val:
                        # Case 3: Apparent Contradiction (Reconciled by Context)
                        rel = ReconciliationRelation(
                            relation_id=f"rel-ctx-{i}-{j}",
                            case_type=CaseType.RECONCILED_CONTRADICTION,
                            fact_a=fa,
                            fact_b=fb,
                            title=f"Context-Reconciled {metric} ({fa.timeframe} vs {fb.timeframe})",
                            summary=f"Apparent discrepancy between {fa.raw_value} and {fb.raw_value} is explained by different time periods ({fa.timeframe} vs {fb.timeframe}).",
                            reasoning=f"Fact A ({fa.raw_value}) from {src_a} covers {fa.timeframe}. Fact B ({fb.raw_value}) from {src_b} covers {fb.timeframe}. The difference reflects growth/change over time, not a data error.",
                            reconciliation_factors=["Temporal Horizon Difference", "Reporting Period Scope", "Accounting Vintage"],
                            source_documents=[fa.evidence.doc_name, fb.evidence.doc_name],
                            confidence=0.94
                        )
                        relations.append(rel)

                    elif same_period and not same_val:
                        # Case 2: Genuine Contradiction
                        rel = ReconciliationRelation(
                            relation_id=f"rel-gen-{i}-{j}",
                            case_type=CaseType.GENUINE_CONTRADICTION,
                            fact_a=fa,
                            fact_b=fb,
                            title=f"Conflict in {metric} for {fa.timeframe}",
                            summary=f"Conflicting {metric} for {fa.timeframe}: {fa.raw_value} ({src_a}) vs {fb.raw_value} ({src_b}).",
                            reasoning=f"{metric} for {fa.timeframe} is reported as {fa.raw_value} in {src_a}, but as {fb.raw_value} in {src_b} — an unreconciled numerical discrepancy.",
                            reconciliation_factors=["Conflicting Scope Definition", "Methodological Divergence"],
                            source_documents=[fa.evidence.doc_name, fb.evidence.doc_name],
                            confidence=0.89
                        )
                        relations.append(rel)

        return relations
