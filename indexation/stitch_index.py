from indexation.connectors import StitchConnector


class StitchIndex:
    """Indexation et résolution des identifiants STITCH."""

    def __init__(self, stitch_tsv_path: str, db_path: str, drugbank_xml_path: str = None):
        self.connector = StitchConnector(stitch_tsv_path, db_path, drugbank_xml_path=drugbank_xml_path)

    def index_data(self):
        self.connector.index_data()

    def resolve_drug_name(self, stitch_id: str):
        return self.connector.resolve_drug_name(stitch_id)

    def count_compounds(self):
        return self.connector.count_compounds()
