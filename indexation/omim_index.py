from indexation.connectors import OmimConnector


class OmimIndex:
    """Indexation et recherche brute pour OMIM."""

    def __init__(self, txt_path: str, db_path: str, onto_csv_path: str = None):
        self.connector = OmimConnector(txt_path, db_path, onto_csv_path)

    def index_data(self):
        self.connector.index_data()

    def search_diseases_by_symptom(self, symptom_query: str):
        return self.connector.search_diseases_by_symptom(symptom_query)

    def count_indexed_diseases(self):
        return self.connector.count_indexed_diseases()

    def count_onto_mappings(self):
        return self.connector.count_onto_mappings()

    def get_cuis_for_term(self, term: str):
        return self.connector.get_cuis_for_term(term)
