from typing import Optional
from models.schema_global import Disease, Drug, Symptom
from wrappers.base_wrapper import BaseWrapper
from indexation.stitch_index import StitchIndex


class StitchWrapper(BaseWrapper):
    """Wrapper pour STITCH : résolution du nom lisible des médicaments."""

    def __init__(self, stitch_index: StitchIndex):
        self.stitch_index = stitch_index

    def map_raw_to_drug(self, raw_data: object) -> Optional[Drug]:
        return None

    def map_raw_to_disease(self, raw_data: object) -> Optional[Disease]:
        return None

    def map_raw_to_symptom(self, raw_data: object) -> Optional[Symptom]:
        return None

    def map_symptom_to_disease(self, raw_data: object) -> Optional[Disease]:
        return None

    def map_disease_to_drug(self, raw_data: object) -> Optional[Drug]:
        return None

    def resolve_drug_name(self, stitch_id: str) -> str:
        return self.stitch_index.resolve_drug_name(stitch_id)
