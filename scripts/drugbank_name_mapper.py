import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Optional, Set


class DrugBankNameMapper:
    """
    Maps STITCH/SIDER compound identifiers to readable DrugBank drug names.

    SIDER uses STITCH compound IDs such as:
        CID100000085
        CID000010917

    DrugBank contains external identifiers such as:
        PubChem Compound
        PubChem Substance

    This mapper tries to convert STITCH/SIDER IDs into PubChem-like numeric IDs
    and then searches for matching DrugBank names.
    """

    def __init__(self, drugbank_xml_path: str):
        self.drugbank_xml_path = Path(drugbank_xml_path)
        self.pubchem_to_name: Dict[str, str] = {}
        self.external_id_to_name: Dict[str, str] = {}

    def load(self) -> None:
        if not self.drugbank_xml_path.exists():
            raise FileNotFoundError(f"DrugBank XML file not found: {self.drugbank_xml_path}")

        tree = ET.parse(self.drugbank_xml_path)
        root = tree.getroot()

        namespace = ""
        if root.tag.startswith("{"):
            namespace = root.tag.split("}")[0] + "}"

        for drug_node in root.findall(f"{namespace}drug"):
            name_node = drug_node.find(f"{namespace}name")

            if name_node is None or not name_node.text:
                continue

            drug_name = name_node.text.strip()

            external_identifiers_node = drug_node.find(f"{namespace}external-identifiers")

            if external_identifiers_node is None:
                continue

            for external_id_node in external_identifiers_node.findall(f"{namespace}external-identifier"):
                resource_node = external_id_node.find(f"{namespace}resource")
                identifier_node = external_id_node.find(f"{namespace}identifier")

                if resource_node is None or identifier_node is None:
                    continue

                if not resource_node.text or not identifier_node.text:
                    continue

                resource = resource_node.text.strip()
                identifier = identifier_node.text.strip()
                normalized_identifier = self._normalize_numeric_identifier(identifier)

                if normalized_identifier:
                    if normalized_identifier not in self.external_id_to_name:
                        self.external_id_to_name[normalized_identifier] = drug_name

                    if resource in {"PubChem Compound", "PubChem Substance"}:
                        self.pubchem_to_name[normalized_identifier] = drug_name

    @staticmethod
    def _normalize_numeric_identifier(identifier: str) -> Optional[str]:
        """
        Keep only numeric identifiers and remove leading zeros.
        """
        identifier = identifier.strip()

        if not identifier.isdigit():
            return None

        normalized = str(int(identifier))

        return normalized

    @staticmethod
    def _numeric_substrings(value: str) -> Set[str]:
        candidates = set()
        for match in re.finditer(r"\d+", value):
            digits = match.group(0)
            if digits:
                try:
                    candidates.add(str(int(digits)))
                except ValueError:
                    continue
        return candidates

    @staticmethod
    def stitch_id_to_pubchem_candidates(stitch_id: str) -> Set[str]:
        """
        Convert STITCH/SIDER ID into possible numeric lookup candidates.

        Examples:
            CID100000085 -> candidates: 100000085, 85
            CID000010917 -> candidates: 10917
        """
        candidates = set()

        if not stitch_id:
            return candidates

        digits_match = re.search(r"CID(\d+)", stitch_id)
        if digits_match:
            digits = digits_match.group(1)
            candidates.update(DrugBankNameMapper._numeric_substrings(digits))

            # STITCH flat IDs often have an additional leading '1'
            # followed by an 8-digit padded PubChem CID.
            # Example: CID100000085 -> PubChem CID 85
            if len(digits) == 9 and digits.startswith("1"):
                stripped = digits[1:]
                candidates.update(DrugBankNameMapper._numeric_substrings(stripped))

        # fallback: any numeric substring inside the full STITCH id
        candidates.update(DrugBankNameMapper._numeric_substrings(stitch_id))

        return candidates

    def get_name_for_stitch_id(self, stitch_id: str) -> Optional[str]:
        candidates = self.stitch_id_to_pubchem_candidates(stitch_id)

        for candidate in candidates:
            if candidate in self.pubchem_to_name:
                return self.pubchem_to_name[candidate]

        for candidate in candidates:
            if candidate in self.external_id_to_name:
                return self.external_id_to_name[candidate]

        # if no numeric lookup succeeded, try raw stitch_id string as an exact key
        if stitch_id in self.external_id_to_name:
            return self.external_id_to_name[stitch_id]

        return None

    def statistics(self) -> dict:
        return {
            "pubchem_identifiers_mapped": len(self.pubchem_to_name)
        }


def main() -> None:
    mapper = DrugBankNameMapper("sources/DRUGBANK/drugbank.xml")
    mapper.load()

    print("DrugBank name mapper loaded.")
    print(mapper.statistics())

    examples = [
        "CID100000085",
        "CID000010917",
        "CID100000143",
        "CID100000158"
    ]

    for stitch_id in examples:
        print(stitch_id, "->", mapper.get_name_for_stitch_id(stitch_id))


if __name__ == "__main__":
    main()