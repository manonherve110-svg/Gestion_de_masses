from typing import Any, Dict, Optional, Tuple
from models.schema_global import Disease, Drug, Symptom
from wrappers.base_wrapper import BaseWrapper


class SiderWrapper(BaseWrapper):
    """Transforme les tuples SIDER en entités du schéma global."""

    def _normalize_name(self, stitch_id: str, term: str) -> str:
        return term.strip() or stitch_id.strip() or "Unknown Drug"

    def _parse_raw(self, raw_data: Any) -> Optional[Tuple[str, str, str, str, str, str]]:
        relation = "side_effect"
        if isinstance(raw_data, dict) and "data" in raw_data and "relation" in raw_data:
            relation = raw_data["relation"]
            tuple_data = raw_data["data"]
        elif isinstance(raw_data, tuple):
            tuple_data = raw_data
        else:
            return None

        stitch_id, cui, meddra_type, term, frequency = "", "", "", "", ""

        if relation == "side_effect":
            if len(tuple_data) == 4:
                stitch_id, cui, term, frequency = tuple_data
            elif len(tuple_data) == 3:
                stitch_id, term, frequency = tuple_data
        else: # indication
            if len(tuple_data) == 4:
                stitch_id, cui, meddra_type, term = tuple_data
            elif len(tuple_data) == 3:
                stitch_id, cui, term = tuple_data
            elif len(tuple_data) == 2:
                stitch_id, term = tuple_data

        return stitch_id, cui, meddra_type, term, relation, str(frequency or "")

    def _eval_frequency(self, freq: str) -> float:
        freq = freq.lower()
        if not freq:
            return 0.0
        if "frequent" in freq or "très" in freq or "très fréquent" in freq:
            return 5.0
        if "%" in freq:
            try:
                val = float(freq.replace("%", "").strip())
                if val > 10.0:
                    return 5.0
                elif val < 1.0:
                    return 2.0
            except:
                pass
        if "rare" in freq:
            return 2.0
        return 0.0

    def map_raw_to_drug(self, raw_data: Any) -> Optional[Drug]:
        parsed = self._parse_raw(raw_data)
        if not parsed:
            return None

        stitch_id, _, _, term, relation, frequency = parsed
        
        clin_score = self._eval_frequency(frequency)
        drug = Drug(
            id=stitch_id, 
            name=self._normalize_name(stitch_id, term),
            pertinence_score=10.0,
            clinical_score=clin_score
        )
        if relation == "indication":
            drug.indications.append(term)
        else:
            drug.side_effects.append(term)
        return drug

    def map_raw_to_disease(self, raw_data: Any) -> Optional[Disease]:
        parsed = self._parse_raw(raw_data)
        if not parsed:
            return None

        stitch_id, cui, _, term, relation, frequency = parsed
        if relation != "indication":
            return None

        return Disease(
            id=cui or f"sider-disease:{stitch_id}",
            name=term,
            symptoms=[],
            treatments=[self._normalize_name(stitch_id, term)],
            pertinence_score=10.0,
            clinical_score=0.0
        )

    def map_raw_to_symptom(self, raw_data: Any) -> Optional[Symptom]:
        parsed = self._parse_raw(raw_data)
        if not parsed:
            return None

        _, cui, _, term, _, _ = parsed
        return Symptom(id=cui or f"sider-symptom:{term}", name=term)

    def map_symptom_to_disease(self, raw_data: Any) -> Optional[Disease]:
        return self.map_raw_to_disease(raw_data)

    def map_disease_to_drug(self, raw_data: Any) -> Optional[Drug]:
        return self.map_raw_to_drug(raw_data)
