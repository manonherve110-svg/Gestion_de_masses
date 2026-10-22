from typing import Any, List, Optional
from models.schema_global import Disease, Drug, Symptom
from wrappers.base_wrapper import BaseWrapper
import re

class OmimWrapper(BaseWrapper):
    """Transforme les résultats bruts OMIM en entités du schéma global."""

    def _extract_symptom_names(self, clinical_synopsis: str) -> List[Symptom]:
        if not clinical_synopsis:
            return []

        lines = [line.strip() for line in clinical_synopsis.splitlines() if line.strip()]
        return [Symptom(id=f"omim-symptom:{idx}", name=" ".join(line.split()))
                for idx, line in enumerate(lines, start=1)]

    def map_raw_to_drug(self, raw_data: Any) -> Optional[Drug]:
        return None

    def map_raw_to_disease(self, raw_data: Any) -> Optional[Disease]:
        if not isinstance(raw_data, tuple) or len(raw_data) < 2:
            return None

        omim_id = raw_data[0]
        title = raw_data[1] if len(raw_data) > 1 else "OMIM Disease"
        clinical_synopsis = ""
        rank = None
        
        if len(raw_data) >= 4:
            clinical_synopsis = raw_data[2] or ""
            rank = raw_data[3]
        elif len(raw_data) == 3:
            rank = raw_data[2]

        # --- NETTOYAGE DU FORMAT OMIM (ex: "#277590 WEAVER SYNDROME; WVS") ---
        if title and title != "OMIM Disease":
            # Capture l'ID optionnel (avec #) et sépare le nom avant le point-virgule
            match = re.match(r"^#?(\d+)\s+([^;]+)", title.strip())
            if match:
                omim_id = match.group(1)  # On extrait l'ID propre (ex: "277590")
                # On nettoie le nom en enlevant les majuscules agressives (ex: "Weaver Syndrome")
                title = match.group(2).strip().title()
            else:
                # Si pas de pattern global, on enlève juste le '#' résiduel au cas où
                title = title.replace("#", "").strip()

        # --- CALCUL DE LA PERTINENCE ---
        pertinence = 0.0
        if rank is not None:
            try:
                pertinence = max(1.0, min(10.0, 10.0 - abs(float(rank))))
            except (TypeError, ValueError):
                pass

        return Disease(
            id=str(omim_id),
            name=title or "OMIM Disease",
            symptoms=self._extract_symptom_names(clinical_synopsis),
            treatments=[],
            pertinence_score=pertinence
        )

    def map_raw_to_symptom(self, raw_data: Any) -> Optional[Symptom]:
        if isinstance(raw_data, str) and raw_data.strip():
            value = raw_data.strip()
            return Symptom(id=f"omim-search:{value.lower()}", name=value)
        return None

    def map_symptom_to_disease(self, raw_data: Any) -> Optional[Disease]:
        return self.map_raw_to_disease(raw_data)

    def map_disease_to_drug(self, raw_data: Any) -> Optional[Drug]:
        return None
