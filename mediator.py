import os
import re
import sys
from dataclasses import asdict
from typing import List, Set

from wrappers import DrugBankWrapper, HPOWrapper, OmimWrapper, SiderWrapper, StitchWrapper
from indexation.drugbank_index import DrugBankIndex
from indexation.hpo_index import HPOIndex
from indexation.omim_index import OmimIndex
from indexation.sider_index import SiderIndex
from indexation.stitch_index import StitchIndex

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Mediator:
    """Médiateur central qui orchestre les requêtes et fusionne les résultats."""

    def __init__(self):
        print("Initialisation des index et wrappers...", file=sys.stderr)

        self.hpo = HPOIndex(
            os.path.join(BASE_DIR, "sources/HPO/hpo.obo"),
            os.path.join(BASE_DIR, "sources/HPO/hpo_annotations.sqlite"),
        )
        self.sider = SiderIndex(
            os.path.join(BASE_DIR, "sources/SIDER"),
            os.path.join(BASE_DIR, "index/sider.db"),
        )
        self.drugbank = DrugBankIndex(
            os.path.join(BASE_DIR, "sources/DRUGBANK/drugbank.xml"),
            os.path.join(BASE_DIR, "index/drugbank_fts.db"),
        )
        self.omim = OmimIndex(
            os.path.join(BASE_DIR, "sources/OMIM/omim.txt"),
            os.path.join(BASE_DIR, "index/omim_fts.db"),
            onto_csv_path=os.path.join(BASE_DIR, "sources/OMIM/omim_onto.csv"),
        )
        self.stitch = StitchIndex(
            os.path.join(BASE_DIR, "sources/STITCH - ATC/br08303.keg"),
            os.path.join(BASE_DIR, "index/stitch.db"),
            drugbank_xml_path=os.path.join(BASE_DIR, "sources/DRUGBANK/drugbank.xml"),
        )

        self.drugbank_wrapper = DrugBankWrapper()
        self.sider_wrapper = SiderWrapper()
        self.omim_wrapper = OmimWrapper()
        self.hpo_wrapper = HPOWrapper()
        self.stitch_wrapper = StitchWrapper(self.stitch)

        self._ensure_indexes()

    def _ensure_indexes(self):
        try:
            self.setup_databases()
        except Exception as exc:
            print(f"Erreur lors de l'initialisation des index locaux : {exc}", file=sys.stderr)

    def setup_databases(self):
        
        # On passe le chemin à la fonction
        self.hpo.index_data()
        self.sider.index_data()
        self.omim.index_data()
        self.drugbank.index_data()
        self.stitch.index_data()

    def _tokenize(self, query: str) -> List[str]:
        return [token for token in re.findall(r"[\w*?]+", query.lower()) if token]

    def _expand_search_terms(self, token: str) -> List[str]:
        token = token.lower().strip()
        if "*" in token or "?" in token:
            matches = self.hpo.match_terms_wildcard(token)
            if matches:
                return matches
        return [token]

    def _collect_synonyms_and_cuis(self, token: str) -> tuple:
        synonyms: Set[str] = set()
        cuis: Set[str] = set()
        for term in self._expand_search_terms(token):
            synonyms.update(self.hpo.get_synonyms(term))
            cuis.update(self.hpo.translate_symptom_to_cui(term))
            cuis.update(self.omim.get_cuis_for_term(term))
        return list(synonyms), list(cuis)

    def suggest_symptoms(self, prefix: str, limit: int = 10) -> List[str]:
        return self.hpo.suggest_symptoms(prefix, limit)

    def get_source_statistics(self) -> dict:
        hpo_terms = self.hpo.count_terms()
        hpo_cuis = self.hpo.count_distinct_cuis()
        hpo_synonyms = self.hpo.count_synonyms()  # <--- AJOUTER CECI

        return {
            "sources": {
                "HPO": {
                    "symptom_terms": hpo_terms,
                    "annotated_cuis": hpo_cuis,
                    "synonyms": hpo_synonyms,    # <--- AJOUTER CECI
                },
                "OMIM": {
                    "indexed_diseases": self.omim.count_indexed_diseases(),
                    "onto_label_cui_pairs": self.omim.count_onto_mappings(),
                },
                "DrugBank": {
                    "indexed_drugs": self.drugbank.count_indexed_drugs(),
                    "indexed_drugs_with_indications": self.drugbank.connector.count_drugs_with_indications(),
                },
                "SIDER": {
                    "side_effect_rows": self.sider.count_side_effects(),
                    "indication_rows": self.sider.count_indications(),
                    "distinct_cuis": len(self.sider.get_distinct_cuis()),
                },
                "STITCH": {
                    "compound_aliases": self.stitch.count_compounds(),
                    "compound_ids": self.stitch.connector.count_distinct_compound_ids(),
                },
            },
            # ... (la suite reste identique)
        }

    def get_mapping_statistics(self) -> dict:
        """
        Quantification dynamique et complète des correspondances entre sources.
        Compte les CUI (Concept Unique Identifiers) intersections et fournit
        des métriques de qualité de mappings sans hardcoding.
        """
        # Collecte dynamique des CUI de chaque source
        hpo_cuis = self.hpo.get_all_annotation_cuis()
        sider_cuis = self.sider.get_distinct_cuis()
        omim_cuis = set(self.omim.connector.cui_to_labels.keys())

        # Calcul dynamique de toutes les intersections pairwise
        hpo_sider_overlap = hpo_cuis & sider_cuis
        hpo_omim_overlap = hpo_cuis & omim_cuis
        sider_omim_overlap = sider_cuis & omim_cuis
        triple_overlap = hpo_cuis & sider_cuis & omim_cuis

        # Union pour les métriques de couverture
        all_cuis_union = hpo_cuis | sider_cuis | omim_cuis

        # Calcul des CUI uniques à chaque source (déjà mappés dans d'autres)
        hpo_only = hpo_cuis - sider_cuis - omim_cuis
        sider_only = sider_cuis - hpo_cuis - omim_cuis
        omim_only = omim_cuis - hpo_cuis - sider_cuis

        # Paires double-overlap (dans 2 sources exactement)
        hpo_sider_only = (hpo_sider_overlap - omim_cuis)
        hpo_omim_only = (hpo_omim_overlap - sider_cuis)
        sider_omim_only = (sider_omim_overlap - hpo_cuis)

        return {
            "timestamp": "2026-05-21",  # Date de calcul
            "counts": {
                "hpo_annotation_cuis": len(hpo_cuis),
                "sider_distinct_cuis": len(sider_cuis),
                "omim_onto_cuis": len(omim_cuis),
                "omim_onto_labels": self.omim.count_onto_mappings(),
                "total_unique_cuis_across_sources": len(all_cuis_union),
            },
            "cross_source_links": {
                "hpo_sider_intersection": len(hpo_sider_overlap),
                "hpo_omim_intersection": len(hpo_omim_overlap),
                "sider_omim_intersection": len(sider_omim_overlap),
                "triple_intersection": len(triple_overlap),
            },
            "source_specificity": {
                "hpo_only_cuis": len(hpo_only),
                "sider_only_cuis": len(sider_only),
                "omim_only_cuis": len(omim_only),
                "hpo_sider_double": len(hpo_sider_only),
                "hpo_omim_double": len(hpo_omim_only),
                "sider_omim_double": len(sider_omim_only),
            },
            "coverage_rates": {
                "hpo_cuis_also_in_sider_pct": round(100 * len(hpo_sider_overlap) / len(hpo_cuis), 2) if hpo_cuis else 0,
                "hpo_cuis_also_in_omim_pct": round(100 * len(hpo_omim_overlap) / len(hpo_cuis), 2) if hpo_cuis else 0,
                "sider_cuis_also_in_hpo_pct": round(100 * len(hpo_sider_overlap) / len(sider_cuis), 2) if sider_cuis else 0,
                "sider_cuis_also_in_omim_pct": round(100 * len(sider_omim_overlap) / len(sider_cuis), 2) if sider_cuis else 0,
                "omim_cuis_also_in_hpo_pct": round(100 * len(hpo_omim_overlap) / len(omim_cuis), 2) if omim_cuis else 0,
                "omim_cuis_also_in_sider_pct": round(100 * len(sider_omim_overlap) / len(omim_cuis), 2) if omim_cuis else 0,
            },
            "mapping_quality_metrics": {
                "total_pairwise_correspondences": len(hpo_sider_overlap) + len(hpo_omim_overlap) + len(sider_omim_overlap),
                "triangle_alignment_score": len(triple_overlap),
                "unique_cuis_ratio": round(100 * len(all_cuis_union) / (len(hpo_cuis) + len(sider_cuis) + len(omim_cuis)), 2) if (len(hpo_cuis) + len(sider_cuis) + len(omim_cuis)) > 0 else 0,
                "average_coverage": round((
                    (100 * len(hpo_sider_overlap) / len(hpo_cuis) if hpo_cuis else 0) +
                    (100 * len(hpo_omim_overlap) / len(hpo_cuis) if hpo_cuis else 0) +
                    (100 * len(hpo_sider_overlap) / len(sider_cuis) if sider_cuis else 0) +
                    (100 * len(sider_omim_overlap) / len(sider_cuis) if sider_cuis else 0) +
                    (100 * len(hpo_omim_overlap) / len(omim_cuis) if omim_cuis else 0) +
                    (100 * len(sider_omim_overlap) / len(omim_cuis) if omim_cuis else 0)
                ) / 6, 2),
            },
            "notes": {
                "calculation_method": "Dynamic counting of UMLS Concept Unique Identifiers (CUI) intersections across HPO, SIDER, and OMIM ontologies",
                "hpo_role": "Phenotype/symptom ontology providing CUI annotations",
                "sider_role": "Side effects and indications database with CUI references",
                "omim_role": "Disease ontology with label-to-CUI mappings",
            },
        }

    def resolve_query(self, query: str, operator: str = "AND") -> dict:
        query = query.strip()
        tokens = self._tokenize(query)

        if not tokens:
            return {
                "query": query,
                "diseases_causing_symptom": [],
                "drugs_causing_symptom_as_side_effect": [],
                "drugs_treating_symptom_or_disease": [],
                "diseases": [],
                "drugs": [],
                "symptoms": [],
                "result_summary": {"diseases": 0, "side_effect_drugs": 0, "treatments": 0},
            }

        all_token_results = []

        for token in tokens:
            token_res = {
                "diseases_causing_symptom": [],
                "drugs_causing_symptom_as_side_effect": [],
                "drugs_treating_symptom_or_disease": [],
                "diseases": [],
                "drugs": [],
                "symptoms": [],
            }

            for term in self._expand_search_terms(token):
                symptom_entity = self.hpo_wrapper.map_raw_to_symptom(term)
                if symptom_entity:
                    token_res["symptoms"].append(asdict(symptom_entity))

            synonyms, cuis = self._collect_synonyms_and_cuis(token)

            for syn in synonyms:
                for row in self.omim.search_diseases_by_symptom(syn):
                    disease = self.omim_wrapper.map_raw_to_disease(row)
                    if disease:
                        token_res["diseases"].append(asdict(disease))
                        token_res["diseases_causing_symptom"].append({
                            "disease": disease.name,
                            "source": "OMIM",
                            "id": disease.id,
                            "pertinence_score": disease.pertinence_score,
                            "clinical_score": disease.clinical_score,
                        })

            for cui in cuis:
                for raw in self.sider.get_side_effects_by_cui(cui):
                    drug = self.sider_wrapper.map_raw_to_drug({"data": raw, "relation": "side_effect"})
                    if drug:
                        drug_name = self.stitch_wrapper.resolve_drug_name(drug.id)
                        token_res["drugs"].append(asdict(drug))
                        token_res["drugs_causing_symptom_as_side_effect"].append({
                            "drug_name": drug_name,
                            "source": "SIDER",
                            "side_effect": raw[1] if len(raw) > 1 else "",
                            "pertinence_score": drug.pertinence_score,
                            "clinical_score": drug.clinical_score,
                        })

                for raw in self.sider.get_indications_by_cui(cui):
                    drug = self.sider_wrapper.map_raw_to_drug({"data": raw, "relation": "indication"})
                    if drug:
                        drug_name = self.stitch_wrapper.resolve_drug_name(drug.id)
                        token_res["drugs"].append(asdict(drug))
                        token_res["drugs_treating_symptom_or_disease"].append({
                            "drug_name": drug_name,
                            "source": "SIDER",
                            "indication": raw[1] if len(raw) > 1 else "",
                            "pertinence_score": drug.pertinence_score,
                            "clinical_score": drug.clinical_score,
                        })

            if not cuis or not token_res["drugs_causing_symptom_as_side_effect"] or not token_res["drugs_treating_symptom_or_disease"]:
                for syn in synonyms:
                    for raw in self.sider.search_side_effects_by_name(syn):
                        drug = self.sider_wrapper.map_raw_to_drug({"data": raw, "relation": "side_effect"})
                        if drug:
                            drug_name = self.stitch_wrapper.resolve_drug_name(drug.id)
                            token_res["drugs"].append(asdict(drug))
                            token_res["drugs_causing_symptom_as_side_effect"].append({
                                "drug_name": drug_name,
                                "source": "SIDER",
                                "side_effect": raw[2] if len(raw) > 2 else "",
                                "pertinence_score": drug.pertinence_score,
                                "clinical_score": drug.clinical_score,
                            })

                    for raw in self.sider.search_indications_by_name(syn):
                        drug = self.sider_wrapper.map_raw_to_drug({"data": raw, "relation": "indication"})
                        if drug:
                            drug_name = self.stitch_wrapper.resolve_drug_name(drug.id)
                            token_res["drugs"].append(asdict(drug))
                            token_res["drugs_treating_symptom_or_disease"].append({
                                "drug_name": drug_name,
                                "source": "SIDER",
                                "indication": raw[2] if len(raw) > 2 else "",
                                "pertinence_score": drug.pertinence_score,
                                "clinical_score": drug.clinical_score,
                            })

            for syn in synonyms:
                for raw in self.drugbank.search_toxicity_by_symptom(syn):
                    drug = self.drugbank_wrapper.map_raw_to_drug(raw)
                    if drug:
                        token_res["drugs"].append(asdict(drug))
                        token_res["drugs_causing_symptom_as_side_effect"].append({
                            "drug_name": drug.name,
                            "source": "DrugBank",
                            "side_effects": drug.side_effects,
                            "pertinence_score": drug.pertinence_score,
                            "clinical_score": drug.clinical_score,
                        })

                for raw in self.drugbank.search_indications_by_symptom(syn):
                    drug = self.drugbank_wrapper.map_raw_to_drug(raw)
                    if drug:
                        token_res["drugs"].append(asdict(drug))
                        token_res["drugs_treating_symptom_or_disease"].append({
                            "drug_name": drug.name,
                            "source": "DrugBank",
                            "indications": drug.indications,
                            "pertinence_score": drug.pertinence_score,
                            "clinical_score": drug.clinical_score,
                        })
                        disease = self.drugbank_wrapper.map_symptom_to_disease(raw)
                        if disease:
                            token_res["diseases"].append(asdict(disease))

            all_token_results.append(token_res)

        def merge_results(key, identity_keys):
            item_stats = {}
            item_objects = {}

            all_items = []
            for res in all_token_results:
                seen_in_res = set()
                for item in res[key]:
                    item_key = tuple(item.get(k) for k in identity_keys)
                    if item_key not in seen_in_res:
                        seen_in_res.add(item_key)
                        all_items.append((item_key, item, True))
                    else:
                        all_items.append((item_key, item, False))

            for item_key, item, is_new_token_match in all_items:
                if item_key not in item_stats:
                    item_stats[item_key] = {
                        "sources": set(),
                        "pertinence": 0.0,
                        "clinique": 0.0,
                        "tokens_matched": 0,
                    }
                    item_objects[item_key] = dict(item)

                if "source" in item:
                    item_stats[item_key]["sources"].add(item["source"])

                if item.get("pertinence_score", 0) > item_stats[item_key]["pertinence"]:
                    item_stats[item_key]["pertinence"] = item.get("pertinence_score", 0)
                if item.get("clinical_score", 0) > item_stats[item_key]["clinique"]:
                    item_stats[item_key]["clinique"] = item.get("clinical_score", 0)

                if is_new_token_match:
                    item_stats[item_key]["tokens_matched"] += 1

            result_list = []
            for item_key, stats in item_stats.items():
                if operator.upper() == "AND" and stats["tokens_matched"] < len(all_token_results):
                    continue

                consensus = len(stats["sources"]) * 10
                symptom_coverage = stats["tokens_matched"] * 10
                total_score = consensus + symptom_coverage + stats["pertinence"] + stats["clinique"]

                obj = item_objects[item_key]
                obj["score"] = round(total_score, 2)
                obj["source"] = ", ".join(sorted(list(stats["sources"])))
                result_list.append(obj)

            return sorted(result_list, key=lambda x: x.get("score", 0), reverse=True)

        diseases = merge_results("diseases_causing_symptom", ["disease"])
        side_drugs = merge_results("drugs_causing_symptom_as_side_effect", ["drug_name"])
        treatments = merge_results("drugs_treating_symptom_or_disease", ["drug_name"])

        return {
            "query": query,
            "operator": operator.upper(),
            "diseases_causing_symptom": diseases,
            "drugs_causing_symptom_as_side_effect": side_drugs,
            "drugs_treating_symptom_or_disease": treatments,
            "diseases": merge_results("diseases", ["name"]),
            "drugs": merge_results("drugs", ["name"]),
            "symptoms": merge_results("symptoms", ["name"]),
            "result_summary": {
                "diseases": len(diseases),
                "side_effect_drugs": len(side_drugs),
                "treatments": len(treatments),
            },
        }


if __name__ == "__main__":
    import json

    mediator = Mediator()
    if len(sys.argv) > 1 and sys.argv[1] == "--setup":
        mediator.setup_databases()
        sys.exit(0)

    query = "fever"
    if len(sys.argv) > 1:
        query = sys.argv[1]

    print(json.dumps(mediator.resolve_query(query), indent=2, ensure_ascii=False))
