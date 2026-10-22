from typing import Any, Optional
from models.schema_global import Disease, Drug, Symptom
from wrappers.base_wrapper import BaseWrapper


class HPOWrapper(BaseWrapper):
    """Transforme un terme de requête HPO en entité Symptom."""

    def map_raw_to_drug(self, raw_data: Any) -> Optional[None]:
        return None

    def map_raw_to_disease(self, raw_data: Any) -> Optional[None]:
        return None

    def map_raw_to_symptom(self, raw_data: Any) -> Optional[Symptom]:
        if isinstance(raw_data, str) and raw_data.strip():
            normalized = raw_data.strip()
            return Symptom(id=f"hpo-search:{normalized.lower()}", name=normalized)
        return None

    def map_symptom_to_disease(self, raw_data: Any) -> Optional[None]:
        return None

    def map_disease_to_drug(self, raw_data: Any) -> Optional[None]:
        return None
