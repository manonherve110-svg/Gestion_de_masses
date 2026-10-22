from indexation.connectors import DrugBankConnector


class DrugBankIndex:
    """Indexation et recherche brute pour DrugBank."""

    def __init__(self, xml_path: str, db_path: str):
        self.connector = DrugBankConnector(xml_path, db_path)

    def index_data(self):
        self.connector.index_data()

    def search_toxicity_by_symptom(self, symptom_query: str):
        return self.connector.search_toxicity_by_symptom(symptom_query)

    def search_indications_by_symptom(self, symptom_query: str):
        return self.connector.search_indications_by_symptom(symptom_query)

    def count_indexed_drugs(self):
        return self.connector.count_indexed_drugs()
