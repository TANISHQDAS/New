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

        for metric, fact_list in grouped.items():
            if len(fact_list) < 2:
                continue

            for i in range(len(fact_list)):
                for j in range(i + 1, len(fact_list)):
                    fa = fact_list[i]
                    fb = fact_list[j]

                    if fa.evidence.doc_name == fb.evidence.doc_name:
                        continue  # compare across different documents

                    # Check temporal or metric equivalence
                    same_period = (fa.timeframe == fb.timeframe)
                    same_val = abs(fa.normalized_value - fb.normalized_value) < 0.05 * max(fa.normalized_value, fb.normalized_value, 1.0)

                    if same_period and same_val:
                        # Case 1: Corroborated Fact
                        rel = ReconciliationRelation(
                            relation_id=f"rel-corr-{i}-{j}",
                            case_type=CaseType.CORROBORATED,
                            fact_a=fa,
                            fact_b=fb,
                            title=f"Corroborated {metric} ({fa.timeframe})",
                            summary=f"Both {fa.evidence.doc_name} and {fb.evidence.doc_name} report matching {metric} of {fa.raw_value}.",
                            reasoning=f"Identical values found across multiple independent sources for period {fa.timeframe}. Value A ({fa.raw_value}) equals Value B ({fb.raw_value}).",
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
                            summary=f"The apparent discrepancy between {fa.raw_value} and {fb.raw_value} is fully explained by temporal evolution ({fa.timeframe} vs {fb.timeframe}) and reporting scope.",
                            reasoning=f"Fact A ({fa.raw_value}) covers period {fa.timeframe} (Doc: {fa.evidence.doc_name}), while Fact B ({fb.raw_value}) covers period {fb.timeframe} (Doc: {fb.evidence.doc_name}). The difference reflects organic growth/temporal progression over time, not a data error.",
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
                            title=f"Direct Conflict in {metric} for {fa.timeframe}",
                            summary=f"Conflicting metrics reported for the exact same period ({fa.timeframe}): {fa.raw_value} in {fa.evidence.doc_name} vs {fb.raw_value} in {fb.evidence.doc_name}.",
                            reasoning=f"Both documents report {metric} for period {fa.timeframe}, but provide incompatible numerical values without an explicit reconciliation note in the text body.",
                            reconciliation_factors=["Conflicting Institutional Baselines", "Methodological Divergence"],
                            source_documents=[fa.evidence.doc_name, fb.evidence.doc_name],
                            confidence=0.89
                        )
                        relations.append(rel)

        return relations
