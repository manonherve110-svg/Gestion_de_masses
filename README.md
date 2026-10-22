# AlloDoctor - Symptom and Medication Search


## How to Open

### Simple Open
1. Navigate to the folder **`python3 scripts/api.py`**



## Description

**AlloDoctor** is an interactive web interface for searching diseases and medications based on symptoms. The application facilitates consulting medical data from reliable sources such as:

- **HPO** (Human Phenotype Ontology) - Human phenotype ontology
- **OMIM** (Online Mendelian Inheritance in Man) - Genetic database
- **DrugBank** - Medication database
- **SIDER** (Side Effect Resource) - Side effect database
- **STITCH** (Search Tool for Interactions of Chemicals) - Chemical interactions database

## Features

**Symptom search** - Real-time autocomplete and suggestions
**Multiple selection** - Easily add and remove symptoms
**Search modes** - AND/OR operators to refine results
**Organized results** - Displayed in cards and tables
**Associated medications** - See treatments for each disease
**Cited sources** - Data traceability

## Project Structure

```
gestion_de_masses/
├── frontend/           # Web interface (HTML, CSS, JS)
├── scripts/            # Python logic (connectors, mediator, API)
├── index/              # Local SQLite caches used by connectors
├── docs/               # Documentation
├── README.md           
├── sources/            # Raw data files (HPO, OMIM, SIDER, STITCH, DrugBank)
└── mediator.py         # Main mediator logic
```


## Usage

1. **Enter a symptom** in the search bar
   - Autocomplete will provide suggestions
   
2. **Click on a suggestion** or press Enter
   - The symptom appears as a blue tag
   
3. **Select the search mode**
   - **AND**: Find diseases with ALL selected symptoms
   - **OR**: Find diseases with AT LEAST ONE selected symptom

4. **Click on "Search Diseases & Medications"**
   - Results are displayed in real-time

5. **Review the results**
   - Disease cards with associated symptoms
   - Medication cards causing the symptoms
   - Complete table with treatment medications

## Examples of Symptoms

- Headache
- Migraine
- Fever
- Nausea
- Fatigue
- Dizziness
- Cough
- Vomiting

## Technologies Used

- **HTML5** - Semantic structure
- **CSS3** - Modern and responsive design
- **JavaScript (Vanilla)** - Interactivity without external dependencies
- **Font Awesome** - Icons
- **Google Fonts (Poppins)** - Typography

### Data Sources

The project uses a mediator pattern: raw data files are stored in `sources/`, and each source is accessed via a dedicated connector.

| Source | Format | Role |
| :--- | :--- | :--- |
| HPO | .obo | Synonym ontology and CUI mapping |
| OMIM | .txt, .csv | Disease and symptom text search |
| DrugBank | .xml | Indications and toxicity retrieval |
| SIDER | .txt, .TSV | Side effect and indication relational search |
| STITCH | .keg, .TSV | Medication ID resolution |

Note: The index/ directory contains local SQLite caches, not the raw data itself.

 Model 17:03
Installation & Development

The frontend connects to a Flask API that utilizes the Python mediator.

    

1. Prepare the local indexes:
```bash
cd /home/manon/2A/semestre_2/masses_données/gestion_de_masses
python3 scripts/mediator.py --setup
```
2. Launch the API:
```bash
python3 scripts/api.py
```
3. Open the frontend in your browser, or navigate to `http://127.0.0.1:5000`.      
To modify the code:

To modify the code:

1. Edit `frontend/index.html` for the interface.
2. Modify `frontend/styles.css` for styling.
3. Update `frontend/script.js` for client-side logic.
4. Edit  `scripts/mediator.py`  and the connectors in`scripts/` for integration logic.

## Future Improvements

- Direct database integration
- Charts and visualizations
- Save searches
- Export results (PDF, CSV)
- Full multilingual support
- Customizable themes

## Author

ambre 
manon
lukasz
