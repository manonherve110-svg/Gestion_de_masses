import re
import xml.etree.ElementTree as ET
from typing import Any, List, Optional, Tuple
from models.schema_global import Disease, Drug, Symptom
from wrappers.base_wrapper import BaseWrapper


class DrugBankWrapper(BaseWrapper):
    """Transforme les résultats bruts DrugBank en entités du schéma global."""

    DRUGBANK_NS = "http://www.drugbank.ca"

    def _find_text(self, parent: ET.Element, tag: str) -> str:
        for candidate in [tag, f"{{{self.DRUGBANK_NS}}}{tag}"]:
            child = parent.find(candidate)
            if child is not None and child.text:
                return child.text.strip()
        return ""

    def _split_terms(self, text: str) -> List[str]:
        cleaned = re.sub(r"\s+", " ", text or "").strip()
        terms = [part.strip() for part in re.split(r"[\.;:]+\s*", cleaned) if part.strip()]
        return terms if terms else ([cleaned] if cleaned else [])

    def _xml_to_drug(self, raw_data: str) -> Optional[Drug]:
        try:
            root = ET.fromstring(raw_data)
        except ET.ParseError:
            return None

        drug_id = self._find_text(root, "drugbank-id")
        if not drug_id:
            ids = root.findall(f".//{{{self.DRUGBANK_NS}}}drugbank-id") + root.findall(".//drugbank-id")
            for candidate in ids:
                if candidate.get("primary") == "true" and candidate.text:
                    drug_id = candidate.text.strip()
                    break
            if not drug_id and ids:
                drug_id = ids[0].text.strip() if ids[0].text else ""

        name = self._find_text(root, "name") or "Unknown Drug"
        return Drug(
            id=drug_id or f"drugbank:{name}",
            name=name,
            indications=self._split_terms(self._find_text(root, "indication")),
            side_effects=self._split_terms(self._find_text(root, "toxicity")),
        )

    def _tuple_to_drug(self, raw_data: Tuple) -> Drug:
        drug_id = raw_data[0]
        name = raw_data[1]
        indication = raw_data[2]
        toxicity = raw_data[3]
        
        pertinence = 0.0
        if len(raw_data) > 4:
            rank = raw_data[4]
            try:
                pertinence = max(1, min(10, int(10 - abs(float(rank)))))
            except:
                pass

        return Drug(
            id=drug_id or f"drugbank:{name}",
            name=name or "Unknown Drug",
            indications=self._split_terms(indication),
            side_effects=self._split_terms(toxicity),
            pertinence_score=pertinence
        )

    def map_raw_to_drug(self, raw_data: Any) -> Optional[Drug]:
        if isinstance(raw_data, tuple) and len(raw_data) >= 4:
            return self._tuple_to_drug(raw_data)
        if isinstance(raw_data, str):
            return self._xml_to_drug(raw_data)
        return None

    def map_raw_to_disease(self, raw_data: Any) -> Optional[Disease]:
        drug = self.map_raw_to_drug(raw_data)
        if not drug:
            return None

        disease_name = drug.indications[0] if drug.indications else (drug.side_effects[0] if drug.side_effects else "Unknown condition")
        return Disease(
            id=f"drugbank-disease:{drug.id}",
            name=disease_name,
            symptoms=[],
            treatments=[drug.name],
        )

    def map_raw_to_symptom(self, raw_data: Any) -> Optional[Symptom]:
        drug = self.map_raw_to_drug(raw_data)
        if not drug:
            return None

        symptom_name = drug.side_effects[0] if drug.side_effects else "Unknown symptom"
        return Symptom(id=f"drugbank-symptom:{drug.id}", name=symptom_name)

    def map_symptom_to_disease(self, raw_data: Any) -> Optional[Disease]:
        return self.map_raw_to_disease(raw_data)

    def map_disease_to_drug(self, raw_data: Any) -> Optional[Drug]:
        return self.map_raw_to_drug(raw_data)
