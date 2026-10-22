import csv
import fnmatch
import os
import sqlite3
import re
import gzip
import xml.etree.ElementTree as ET

try:
    from drugbank_name_mapper import DrugBankNameMapper
except ImportError:
    from scripts.drugbank_name_mapper import DrugBankNameMapper


class DrugBankConnector:
    """Accès brut au fichier DrugBank et à l'index FTS local."""

    def __init__(self, xml_path: str, db_path: str):
        self.xml_path = xml_path
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._init_db()

    def _init_db(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE VIRTUAL TABLE IF NOT EXISTS drugbank_fts USING fts5(
                drugbank_id, name, indication, toxicity
            )
        ''')
        self.conn.commit()

    def index_data(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM drugbank_fts")
        if cursor.fetchone()[0] > 0:
            return

        if not os.path.exists(self.xml_path):
            return

        ns = {'db': 'http://www.drugbank.ca'}
        records = []
        context = ET.iterparse(self.xml_path, events=('end',))
        for event, elem in context:
            if elem.tag.endswith('drug'):
                drug_id = elem.find('.//db:drugbank-id[@primary="true"]', ns)
                name = elem.find('.//db:name', ns)
                indication = elem.find('.//db:indication', ns)
                toxicity = elem.find('.//db:toxicity', ns)

                if drug_id is not None and name is not None:
                    db_id = drug_id.text
                    db_name = name.text
                    db_ind = indication.text if indication is not None and indication.text else ""
                    db_tox = toxicity.text if toxicity is not None and toxicity.text else ""

                    if db_ind or db_tox:
                        records.append((db_id, db_name, db_ind, db_tox))

                elem.clear()

        if records:
            cursor.executemany("INSERT INTO drugbank_fts VALUES (?, ?, ?, ?)", records)
            self.conn.commit()

    def search_toxicity_by_symptom(self, symptom_query: str):
        cursor = self.conn.cursor()
        
        # Si la requête contient un joker, on la passe telle quelle à FTS5
        if "*" in symptom_query:
            match_query = symptom_query
        else:
            # Sinon, on cherche l'expression exacte
            query_escaped = symptom_query.replace('"', '""')
            match_query = f'"{query_escaped}"'
            
        try:
            cursor.execute("SELECT drugbank_id, name, indication, toxicity, rank FROM drugbank_fts WHERE toxicity MATCH ?", (match_query,))
            return cursor.fetchall()
        except sqlite3.OperationalError:
            return []

    def search_indications_by_symptom(self, symptom_query: str):
        cursor = self.conn.cursor()
        query = symptom_query.replace('"', '""')
        try:
            cursor.execute("SELECT drugbank_id, name, indication, toxicity, rank FROM drugbank_fts WHERE indication MATCH ?", (f'"{query}"',))
            return cursor.fetchall()
        except sqlite3.OperationalError:
            return []

    def count_indexed_drugs(self):
        cursor = self.conn.cursor()
        try:
            cursor.execute("SELECT COUNT(*) FROM drugbank_fts")
            return cursor.fetchone()[0]
        except sqlite3.OperationalError:
            return 0

    def count_drugs_with_indications(self):
        cursor = self.conn.cursor()
        try:
            cursor.execute("SELECT COUNT(*) FROM drugbank_fts WHERE indication != '' AND indication IS NOT NULL")
            return cursor.fetchone()[0]
        except sqlite3.OperationalError:
            return 0


class SiderConnector:
    """Accès brut aux fichiers SIDER et création de l'index SQLite local."""

    def __init__(self, sider_dir: str, db_path: str):
        self.sider_dir = sider_dir
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._init_db()

    def _init_db(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS side_effects (
                stitch_id TEXT,
                cui TEXT,
                meddra_type TEXT,
                term TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS indications (
                stitch_id TEXT,
                cui TEXT,
                meddra_type TEXT,
                term TEXT
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_se_cui ON side_effects(cui)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_ind_cui ON indications(cui)')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS meddra_freq (
                stitch_id TEXT,
                cui TEXT,
                frequency TEXT
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_freq_cui ON meddra_freq(cui)')
        self.conn.commit()

    def index_data(self):
        cursor = self.conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM side_effects")
        if cursor.fetchone()[0] == 0:
            se_path = os.path.join(self.sider_dir, "meddra_all_se.tsv.gz")
            if os.path.exists(se_path):
                with gzip.open(se_path, 'rt', encoding='utf-8') as f:
                    records = []
                    for line in f:
                        parts = line.strip().split('\t')
                        if len(parts) >= 6:
                            records.append((parts[0], parts[4], parts[3], parts[5]))
                    cursor.executemany("INSERT INTO side_effects VALUES (?, ?, ?, ?)", records)

        cursor.execute("SELECT COUNT(*) FROM indications")
        if cursor.fetchone()[0] == 0:
            ind_path = os.path.join(self.sider_dir, "meddra_all_indications.tsv.gz")
            if os.path.exists(ind_path):
                with gzip.open(ind_path, 'rt', encoding='utf-8') as f:
                    records = []
                    for line in f:
                        parts = line.strip().split('\t')
                        if len(parts) >= 7:
                            records.append((parts[0], parts[5], parts[4], parts[6]))
                    cursor.executemany("INSERT INTO indications VALUES (?, ?, ?, ?)", records)

        cursor.execute("SELECT COUNT(*) FROM meddra_freq")
        if cursor.fetchone()[0] == 0:
            freq_path = os.path.join(self.sider_dir, "meddra_freq.tsv.gz")
            if os.path.exists(freq_path):
                with gzip.open(freq_path, 'rt', encoding='utf-8') as f:
                    records = []
                    for line in f:
                        parts = line.strip().split('\t')
                        if len(parts) >= 5:
                            records.append((parts[0], parts[2], parts[4]))
                    cursor.executemany("INSERT INTO meddra_freq VALUES (?, ?, ?)", records)

        self.conn.commit()

    def get_side_effects_by_cui(self, cui: str):
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT s.stitch_id, s.term, f.frequency 
            FROM side_effects s
            LEFT JOIN meddra_freq f ON s.stitch_id = f.stitch_id AND s.cui = f.cui
            WHERE s.cui = ? AND s.meddra_type = 'PT'
        """, (cui,))
        return cursor.fetchall()

    def get_indications_by_cui(self, cui: str):
        cursor = self.conn.cursor()
        cursor.execute("SELECT stitch_id, term FROM indications WHERE cui = ? AND meddra_type = 'PT'", (cui,))
        return cursor.fetchall()

    def search_side_effects_by_name(self, term: str):
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT s.stitch_id, s.cui, s.term, f.frequency 
            FROM side_effects s
            LEFT JOIN meddra_freq f ON s.stitch_id = f.stitch_id AND s.cui = f.cui
            WHERE s.term LIKE ? AND s.meddra_type = 'PT'
        """, ('%' + term + '%',))
        return cursor.fetchall()

    def search_indications_by_name(self, term: str):
        cursor = self.conn.cursor()
        cursor.execute("SELECT stitch_id, cui, term FROM indications WHERE term LIKE ? AND meddra_type = 'PT'", ('%' + term + '%',))
        return cursor.fetchall()

    def count_side_effects(self):
        cursor = self.conn.cursor()
        try:
            cursor.execute("SELECT COUNT(*) FROM side_effects")
            return cursor.fetchone()[0]
        except sqlite3.OperationalError:
            return 0

    def count_indications(self):
        cursor = self.conn.cursor()
        try:
            cursor.execute("SELECT COUNT(*) FROM indications")
            return cursor.fetchone()[0]
        except sqlite3.OperationalError:
            return 0

    def get_distinct_cuis(self):
        cursor = self.conn.cursor()
        try:
            cursor.execute("SELECT DISTINCT cui FROM side_effects UNION SELECT DISTINCT cui FROM indications")
            return {row[0] for row in cursor.fetchall() if row[0]}
        except sqlite3.OperationalError:
            return set()


class OmimConnector:
    """Accès brut au fichier OMIM et construction d'un index FTS local."""

    def __init__(self, txt_path: str, db_path: str, onto_csv_path: str = None):
        self.txt_path = txt_path
        self.db_path = db_path
        self.onto_csv_path = onto_csv_path
        self.label_to_cui = {}
        self.cui_to_labels = {}
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._init_db()
        self._load_omim_onto()

    def _load_omim_onto(self):
        if not self.onto_csv_path or not os.path.exists(self.onto_csv_path):
            return
        with open(self.onto_csv_path, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                label = (row.get("Preferred Label") or "").strip().lower()
                cui = (row.get("CUI") or "").strip()
                if not label or not cui or row.get("Obsolete", "").lower() == "true":
                    continue
                self.label_to_cui[label] = cui
                self.cui_to_labels.setdefault(cui, []).append(label)

    def get_labels_for_term(self, term: str, limit: int = 15):
        term = term.lower().strip()
        if not term:
            return []
        if "*" in term or "?" in term:
            pattern = term
            matches = [label for label in self.label_to_cui if fnmatch.fnmatch(label, pattern)]
            return matches[:limit]
        exact = self.label_to_cui.get(term)
        if exact:
            return [term]
        return [label for label in self.label_to_cui if term in label][:limit]

    def get_cuis_for_term(self, term: str):
        return list({self.label_to_cui[label] for label in self.get_labels_for_term(term) if label in self.label_to_cui})

    def _init_db(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE VIRTUAL TABLE IF NOT EXISTS omim_fts USING fts5(
                omim_id, title, clinical_synopsis
            )
        ''')
        self.conn.commit()

    def index_data(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM omim_fts")
        if cursor.fetchone()[0] > 0:
            return

        if not os.path.exists(self.txt_path):
            return

        records = []
        with open(self.txt_path, 'r', encoding='latin1') as f:
            current_id = None
            current_title = None
            in_cs = False
            cs_text = []

            for line in f:
                if line.startswith('*FIELD* NO'):
                    current_id = next(f, '').strip()
                elif line.startswith('*FIELD* TI'):
                    current_title = next(f, '').strip()
                elif line.startswith('*FIELD* CS'):
                    in_cs = True
                    cs_text = []
                elif line.startswith('*FIELD*') and in_cs:
                    in_cs = False
                    if current_id and current_title and cs_text:
                        records.append((current_id, current_title, " ".join(cs_text)))
                elif in_cs:
                    cs_text.append(line.strip())

        if records:
            cursor.executemany("INSERT INTO omim_fts VALUES (?, ?, ?)", records)
            self.conn.commit()

    def search_diseases_by_symptom(self, symptom_query: str):
        cursor = self.conn.cursor()
        query = symptom_query.replace('"', '""')
        results = []
        seen = set()
        try:
            cursor.execute(
                "SELECT omim_id, title, clinical_synopsis, rank FROM omim_fts WHERE clinical_synopsis MATCH ?",
                (f'"{query}"',),
            )
            for row in cursor.fetchall():
                key = row[0]
                if key not in seen:
                    seen.add(key)
                    results.append(row)
        except sqlite3.OperationalError:
            pass

        for label in self.get_labels_for_term(symptom_query):
            escaped = label.replace('"', '""')
            try:
                cursor.execute(
                    "SELECT omim_id, title, clinical_synopsis, rank FROM omim_fts WHERE clinical_synopsis MATCH ?",
                    (f'"{escaped}"',),
                )
                for row in cursor.fetchall():
                    key = row[0]
                    if key not in seen:
                        seen.add(key)
                        results.append(row)
            except sqlite3.OperationalError:
                continue
        return results

    def count_indexed_diseases(self):
        cursor = self.conn.cursor()
        try:
            cursor.execute("SELECT COUNT(*) FROM omim_fts")
            return cursor.fetchone()[0]
        except sqlite3.OperationalError:
            return 0

    def count_onto_mappings(self):
        return len(self.label_to_cui)




class HPOConnector:
    """Accès à l'ontologie HPO (via un index SQLite qu'on crée) et aux annotations du prof."""

    def __init__(self, hpo_obo_path: str, hpo_annotations_db_path: str):
        self.hpo_obo_path = hpo_obo_path
        self.hpo_annotations_path = hpo_annotations_db_path
        
        # On détermine dynamiquement le chemin vers le dossier "index"
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        index_dir = os.path.join(project_root, "index")
        os.makedirs(index_dir, exist_ok=True)
        
        # NOUVEAU : Chemin vers notre propre base de données d'indexation OBO
        self.hpo_index_path = os.path.join(index_dir, "hpo_obo_index.db")
        
        # Connexion 1 : Base de données du prof (en lecture)
        if not os.path.exists(self.hpo_annotations_path):
            print(f"ATTENTION: La base SQLite du prof est introuvable ici : {self.hpo_annotations_path}")
        self.annot_conn = sqlite3.connect(self.hpo_annotations_path, check_same_thread=False)
        
        # Connexion 2 : Notre propre base d'indexation (en écriture/lecture)
        self.index_conn = sqlite3.connect(self.hpo_index_path, check_same_thread=False)

    def index_data(self):
        """Lit le fichier hpo.obo et crée un index SQL des symptômes et synonymes."""
        if not os.path.exists(self.hpo_obo_path):
            print(f"Fichier OBO introuvable : {self.hpo_obo_path}")
            return "Erreur: Fichier OBO introuvable."

        cursor = self.index_conn.cursor()
        
        # Création de notre table d'indexation
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS hpo_terms (
                hp_id TEXT,
                term_name TEXT,
                is_synonym INTEGER
            )
        ''')
        
        # On vide la table pour éviter les doublons si on relance --setup
        cursor.execute("DELETE FROM hpo_terms")

        print("Création de la base de données hpo_obo_index.db à partir de hpo.obo...")
        batch = []
        current_id = None
        
        with open(self.hpo_obo_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith('id: HP:'):
                    current_id = line[4:].strip()
                elif line.startswith('name: '):
                    name = line[6:].strip().lower()
                    if current_id:
                        batch.append((current_id, name, 0)) # 0 = Nom principal
                elif line.startswith('synonym: '):
                    match = re.search(r'"([^"]*)"', line)
                    if match and current_id:
                        syn = match.group(1).lower()
                        batch.append((current_id, syn, 1)) # 1 = Synonyme
                
                # Insertion par lots pour ne pas saturer la RAM
                if len(batch) >= 10000:
                    cursor.executemany("INSERT INTO hpo_terms (hp_id, term_name, is_synonym) VALUES (?, ?, ?)", batch)
                    batch = []
                    
        if batch:
            cursor.executemany("INSERT INTO hpo_terms (hp_id, term_name, is_synonym) VALUES (?, ?, ?)", batch)

        # Création des index SQL (TRÈS IMPORTANT pour le projet et la rapidité)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_term_name ON hpo_terms(term_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_hp_id ON hpo_terms(hp_id)")

        self.index_conn.commit()
        return f"Indexation HPO.obo terminée avec succès dans {self.hpo_index_path}"

    def translate_symptom_to_cui(self, symptom_term: str):
        """Traduit un symptôme en identifiants de maladie (CUI/OMIM) via les bases de données."""
        symptom_term = symptom_term.lower().strip()
        
        # 1. Chercher le HP_ID dans notre nouvel index
        index_cursor = self.index_conn.cursor()
        index_cursor.execute("SELECT hp_id FROM hpo_terms WHERE term_name LIKE ?", (f"%{symptom_term}%",))
        row = index_cursor.fetchone()
        
        cuis = set()
        if row:
            hp_id = row[0]
            # 2. Chercher les maladies dans la base du prof
            annot_cursor = self.annot_conn.cursor()
            try:
                annot_cursor.execute("SELECT disease_id FROM phenotype_annotation WHERE sign_id = ? AND disease_db = 'UMLS'", (hp_id,))
                for r in annot_cursor.fetchall():
                    cuis.add(r[0])
            except sqlite3.OperationalError:
                pass # Si la table du prof est mal nommée
                
        return list(cuis)

    def get_synonyms(self, symptom_term: str):
        """Récupère tous les synonymes d'un symptôme (bonus du projet)."""
        symptom_term = symptom_term.lower().strip()
        cursor = self.index_conn.cursor()
        
        # Trouver l'ID du terme
        cursor.execute("SELECT hp_id FROM hpo_terms WHERE term_name LIKE ?", (f"%{symptom_term}%",))
        row = cursor.fetchone()
        
        if row:
            hp_id = row[0]
            # Récupérer tous les noms (principaux et synonymes) liés à cet ID
            cursor.execute("SELECT term_name FROM hpo_terms WHERE hp_id = ?", (hp_id,))
            return list(set(r[0] for r in cursor.fetchall()))
            
        return [symptom_term]

    def match_terms_wildcard(self, pattern: str, limit: int = 25):
        """Gère les jokers * et ? dans la requête (bonus +2 points)."""
        pattern = pattern.lower().strip()
        if not pattern:
            return []
            
        # Conversion des jokers en syntaxe SQL : '*' devient '%' et '?' devient '_'
        sql_pattern = pattern.replace('*', '%').replace('?', '_')
        
        cursor = self.index_conn.cursor()
        cursor.execute("SELECT DISTINCT term_name FROM hpo_terms WHERE term_name LIKE ? LIMIT ?", (sql_pattern, limit))
        return [r[0] for r in cursor.fetchall()]

    def suggest_symptoms(self, prefix: str, limit: int = 10):
        prefix = prefix.lower().strip()
        if not prefix:
            return []
            
        if "*" in prefix or "?" in prefix:
            return self.match_terms_wildcard(prefix, limit)
            
        cursor = self.index_conn.cursor()
        # Chercher d'abord ceux qui commencent par le préfixe
        cursor.execute("SELECT DISTINCT term_name FROM hpo_terms WHERE term_name LIKE ? LIMIT ?", (f"{prefix}%", limit))
        suggestions = [r[0] for r in cursor.fetchall()]
        
        # Compléter avec ceux qui contiennent le préfixe si on n'a pas atteint la limite
        if len(suggestions) < limit:
            diff = limit - len(suggestions)
            cursor.execute("SELECT DISTINCT term_name FROM hpo_terms WHERE term_name LIKE ? AND term_name NOT LIKE ? LIMIT ?", 
                           (f"%{prefix}%", f"{prefix}%", diff))
            suggestions.extend([r[0] for r in cursor.fetchall()])
            
        return suggestions

    def count_terms(self):
        try:
            cursor = self.index_conn.cursor()
            cursor.execute("SELECT COUNT(DISTINCT hp_id) FROM hpo_terms")
            return cursor.fetchone()[0]
        except sqlite3.OperationalError:
            return 0

    def count_synonyms(self):
        try:
            cursor = self.index_conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM hpo_terms WHERE is_synonym = 1")
            return cursor.fetchone()[0]
        except sqlite3.OperationalError:
            return 0

    def count_distinct_cuis(self):
        try:
            cursor = self.annot_conn.cursor()
            cursor.execute("SELECT COUNT(DISTINCT disease_id) FROM phenotype_annotation WHERE disease_db = 'UMLS'")
            return cursor.fetchone()[0]
        except sqlite3.OperationalError:
            return 0

    def get_all_annotation_cuis(self):
        try:
            cursor = self.annot_conn.cursor()
            cursor.execute("SELECT DISTINCT disease_id FROM phenotype_annotation WHERE disease_db = 'UMLS'")
            return {row[0] for row in cursor.fetchall()}
        except sqlite3.OperationalError:
            return set()


class StitchConnector:
    """Accès brut aux alias STITCH et résolution des noms de composés."""

    def __init__(self, stitch_tsv_path: str, db_path: str, drugbank_xml_path: str = None):
        self.stitch_tsv_path = stitch_tsv_path
        self.db_path = db_path
        self.drugbank_xml_path = drugbank_xml_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._init_db()
        self.mapper = None
        if self.drugbank_xml_path and os.path.exists(self.drugbank_xml_path):
            try:
                self.mapper = DrugBankNameMapper(self.drugbank_xml_path)
                self.mapper.load()
            except Exception:
                self.mapper = None

    def _init_db(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE VIRTUAL TABLE IF NOT EXISTS stitch_names USING fts5(
                stitch_id UNINDEXED, 
                name
            )
        ''')
        self.conn.commit()

    def index_data(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM stitch_names")
        if cursor.fetchone()[0] > 0:
            return

        if os.path.exists(self.stitch_tsv_path):
            # Gestion auto du gzip ou du texte brut
            open_func = gzip.open(self.stitch_tsv_path, 'rt', encoding='utf-8') if self.stitch_tsv_path.endswith('.gz') else open(self.stitch_tsv_path, 'r', encoding='utf-8')
            
            with open_func as f:
                records = []
                for line in f:
                    # Dans un fichier .keg, les entrées de médicaments commencent par 'F'
                    if line.startswith('F '):
                        # On retire le 'F' et les espaces superflus au début et à la fin
                        content = line[1:].strip()
                        
                        # Séparation par le premier espace pour isoler l'ID (ex: D00943) du reste du nom
                        parts = content.split(maxsplit=1)
                        
                        if len(parts) == 2:
                            drug_id = parts[0]   # ex: "D00943"
                            drug_name = parts[1] # ex: "Sodium fluoride (JAN/USP)"
                            
                            records.append((drug_id, drug_name))
                
                if records:
                    cursor.executemany("INSERT OR IGNORE INTO stitch_names VALUES (?, ?)", records)
                    self.conn.commit()

    def resolve_drug_name(self, stitch_id: str):
        cursor = self.conn.cursor()
        cursor.execute("SELECT name FROM stitch_names WHERE stitch_id = ?", (stitch_id,))
        res = cursor.fetchone()

        if res and res[0]:
            return res[0]

        if self.mapper:
            mapped_name = self.mapper.get_name_for_stitch_id(stitch_id)
            if mapped_name:
                return mapped_name

        return stitch_id

    def count_compounds(self):
        cursor = self.conn.cursor()
        try:
            cursor.execute("SELECT COUNT(*) FROM stitch_names")
            return cursor.fetchone()[0]
        except sqlite3.OperationalError:
            return 0

    def count_distinct_compound_ids(self):
        cursor = self.conn.cursor()
        try:
            cursor.execute("SELECT COUNT(DISTINCT stitch_id) FROM stitch_names")
            return cursor.fetchone()[0]
        except sqlite3.OperationalError:
            return 0
        
    def count_synonyms(self):
        # self.hp_to_synonyms contient des listes sous la forme : [nom_principal, synonyme1, synonyme2...]
        # On additionne la taille de toutes les listes
        total_mots = sum(len(liste) for liste in self.hp_to_synonyms.values())
        # On soustrait le nombre de termes pour ne garder que le compte strict des synonymes
        total_termes = len(self.hp_to_synonyms)
        return total_mots - total_termes
