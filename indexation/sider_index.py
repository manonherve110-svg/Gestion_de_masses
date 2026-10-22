from indexation.connectors import SiderConnector


class SiderIndex:
    """Indexation et recherche brute pour SIDER."""

    def __init__(self, sider_dir: str, db_path: str):
        self.connector = SiderConnector(sider_dir, db_path)

    def index_data(self):
        self.connector.index_data()

    def get_side_effects_by_cui(self, cui: str):
        return self.connector.get_side_effects_by_cui(cui)

    def get_indications_by_cui(self, cui: str):
        return self.connector.get_indications_by_cui(cui)

    def search_side_effects_by_name(self, term: str):
        return self.connector.search_side_effects_by_name(term)

    def search_indications_by_name(self, term: str):
        return self.connector.search_indications_by_name(term)

    def count_side_effects(self):
        return self.connector.count_side_effects()

    def count_indications(self):
        return self.connector.count_indications()

    def get_distinct_cuis(self):
        return self.connector.get_distinct_cuis()
