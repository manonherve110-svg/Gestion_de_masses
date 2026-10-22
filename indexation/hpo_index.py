from indexation.connectors import HPOConnector

class HPOIndex:
    """Indexation et recherche brute pour HPO."""

    def __init__(self, hpo_obo_path: str, hpo_annotations_path: str):
        self.connector = HPOConnector(hpo_obo_path, hpo_annotations_path)

    def index_data(self):
        return self.connector.index_data()

    def translate_symptom_to_cui(self, symptom_term: str):
        return self.connector.translate_symptom_to_cui(symptom_term)

    def get_synonyms(self, symptom_term: str):
        return self.connector.get_synonyms(symptom_term)

    def suggest_symptoms(self, prefix: str, limit: int = 10):
        return self.connector.suggest_symptoms(prefix, limit)

    def match_terms_wildcard(self, pattern: str, limit: int = 25):
        return self.connector.match_terms_wildcard(pattern, limit)

    def count_terms(self):
        return self.connector.count_terms()

    def count_distinct_cuis(self):
        return self.connector.count_distinct_cuis()

    def get_all_annotation_cuis(self):
        return self.connector.get_all_annotation_cuis()
    
    def count_synonyms(self):
        return self.connector.count_synonyms()