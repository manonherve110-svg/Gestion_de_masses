#!/usr/bin/env python3
"""
Analyse comparative des sources biomédicales - AlloDoctor
Génère un tableau, des histogrammes et une analyse scale-free network.
"""

import os
import sys
import sqlite3
import gzip
import xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
from collections import defaultdict, Counter
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.backends.backend_pdf import PdfPages
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

# Configuration des chemins
SOURCES_DIR = Path(__file__).parent
PROJECT_ROOT = SOURCES_DIR.parent
INDEXATION_DIR = PROJECT_ROOT / "indexation"

sys.path.insert(0, str(INDEXATION_DIR.parent))

from indexation.connectors import (
    DrugBankConnector, SiderConnector, OmimConnector, 
    HPOConnector, StitchConnector
)


class SourceAnalyzer:
    def __init__(self):
        self.stats = {}
        self.distributions = {}
        
    def analyze_drugbank(self):
        """Analyse DrugBank XML"""
        print("📊 Analyse DrugBank...")
        drugbank_path = SOURCES_DIR / "DRUGBANK" / "drugbank.xml"
        
        if not drugbank_path.exists():
            print(f"  ⚠️  Fichier non trouvé: {drugbank_path}")
            return
        
        drug_count = 0
        has_indication = 0
        has_toxicity = 0
        indication_length = []
        
        ns = {'db': 'http://www.drugbank.ca'}
        context = ET.iterparse(str(drugbank_path), events=('end',))
        
        for event, elem in context:
            if elem.tag.endswith('drug'):
                drug_id = elem.find('.//db:drugbank-id[@primary="true"]', ns)
                indication = elem.find('.//db:indication', ns)
                toxicity = elem.find('.//db:toxicity', ns)
                
                if drug_id is not None:
                    drug_count += 1
                    
                    if indication is not None and indication.text:
                        has_indication += 1
                        indication_length.append(len(indication.text))
                    
                    if toxicity is not None and toxicity.text:
                        has_toxicity += 1
                
                elem.clear()
        
        self.stats['DrugBank'] = {
            'Total médicaments': drug_count,
            'Avec indications': has_indication,
            'Avec toxicité': has_toxicity,
            'Type': 'Base de données de médicaments',
            'Couverture': f"{(has_indication + has_toxicity) / max(drug_count, 1) * 100:.1f}%",
        }
        print(f"  ✓ {drug_count} médicaments analysés")

    def analyze_sider(self):
        """Analyse SIDER et distribution des effets secondaires"""
        print("📊 Analyse SIDER...")
        sider_dir = SOURCES_DIR / "SIDER"
        
        side_effects_counts = Counter()
        indications_counts = Counter()
        total_se = 0
        total_ind = 0
        
        # Analyse des effets secondaires
        se_path = sider_dir / "meddra_all_se.tsv.gz"
        if se_path.exists():
            with gzip.open(se_path, 'rt', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    parts = line.strip().split('\t')
                    if len(parts) >= 6:
                        stitch_id = parts[0]
                        side_effects_counts[stitch_id] += 1
                        total_se += 1
        
        # Analyse des indications
        ind_path = sider_dir / "meddra_all_indications.tsv.gz"
        if ind_path.exists():
            with gzip.open(ind_path, 'rt', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    parts = line.strip().split('\t')
                    if len(parts) >= 7:
                        stitch_id = parts[0]
                        indications_counts[stitch_id] += 1
                        total_ind += 1
        
        distinct_molecules = len(side_effects_counts)
        self.stats['SIDER'] = {
            'Total molécules': distinct_molecules,
            'Total effets secondaires': total_se,
            'Total indications': total_ind,
            'Type': 'Effets secondaires et indications',
            'Relations': f"{total_se + total_ind}",
        }
        
        # Sauvegarde distribution pour histogramme
        if side_effects_counts:
            self.distributions['SIDER'] = list(side_effects_counts.values())
        
        print(f"  ✓ {distinct_molecules} molécules, {total_se} effets secondaires")

    def analyze_omim(self):
        """Analyse OMIM"""
        print("📊 Analyse OMIM...")
        omim_path = SOURCES_DIR / "OMIM" / "omim.txt"
        
        if not omim_path.exists():
            print(f"  ⚠️  Fichier non trouvé: {omim_path}")
            return
        
        disease_count = 0
        with_cs = 0
        cs_lengths = []
        
        with open(omim_path, 'r', encoding='latin1') as f:
            in_cs = False
            cs_text = []
            
            for line in f:
                if line.startswith('*FIELD* NO'):
                    disease_count += 1
                elif line.startswith('*FIELD* CS'):
                    in_cs = True
                    cs_text = []
                elif line.startswith('*FIELD*') and in_cs:
                    in_cs = False
                    if cs_text:
                        with_cs += 1
                        cs_lengths.append(len(" ".join(cs_text)))
                elif in_cs:
                    cs_text.append(line.strip())
        
        self.stats['OMIM'] = {
            'Total maladies': disease_count,
            'Avec description': with_cs,
            'Type': 'Base de maladies génétiques',
            'Couverture': f"{with_cs / max(disease_count, 1) * 100:.1f}%",
        }
        print(f"  ✓ {disease_count} maladies analysées")

    def analyze_hpo(self):
        """Analyse HPO"""
        print("Analyse HPO...")
        hpo_path = SOURCES_DIR / "HPO" / "hpo.obo"
        
        if not hpo_path.exists():
            print(f"    Fichier non trouvé: {hpo_path}")
            return
        
        terms = set()
        synonyms = 0
        
        with open(hpo_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith('id: HP:'):
                    terms.add(line.strip())
                elif line.startswith('synonym:'):
                    synonyms += 1
        
        self.stats['HPO'] = {
            'Termes d\'ontologie': len(terms),
            'Synonymes': synonyms,
            'Type': 'Ontologie des phénotypes humains',
            'Total annotations': len(terms) + synonyms,
        }
        print(f"  ✓ {len(terms)} termes, {synonyms} synonymes")

    def analyze_stitch(self):
        """Analyse STITCH"""
        print("📊 Analyse STITCH...")
        stitch_path = SOURCES_DIR / "STITCH - ATC" / "br08303.keg"
        
        if not stitch_path.exists():
            print(f"  ⚠️  Fichier non trouvé: {stitch_path}")
            return
        
        total_compounds = 0
        with open(stitch_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if line.startswith('F '):
                    total_compounds += 1
        
        self.stats['STITCH'] = {
            'Composés chimiques': total_compounds,
            'Type': 'Base d\'interactions chimiques',
            'Couverture': 'Interactions protéine-chimique',
        }
        print(f"  ✓ {total_compounds} composés analysés")

    def run_all_analyses(self):
        """Lance toutes les analyses"""
        self.analyze_drugbank()
        self.analyze_sider()
        self.analyze_omim()
        self.analyze_hpo()
        self.analyze_stitch()

    def detect_scale_free(self):
        """
        Détecte si une distribution suit une loi de puissance (scale-free network).
        Retourne conclusions et métriques.
        """
        conclusions = []
        
        if 'SIDER' in self.distributions and self.distributions['SIDER']:
            degrees = np.array(self.distributions['SIDER'])
            
            # Calcul du log-log
            x = np.log10(np.arange(1, len(degrees) + 1))
            y = np.log10(np.sort(degrees)[::-1])
            
            # Régression linéaire
            slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
            
            # Alpha (exposant de la loi de puissance)
            alpha = -slope
            
            # Sauvegarder pour le graphique
            self.scale_free_metrics = {
                'alpha': alpha,
                'r_value': r_value,
                'slope': slope,
                'is_scale_free': abs(r_value) > 0.8
            }
            
            # Génération de la conclusion
            if abs(r_value) > 0.8:
                conclusions.append(
                    f"Le réseau SIDER suit une **loi de puissance** (α={alpha:.2f}, R²={r_value**2:.3f}), "
                    f"caractéristique des réseaux scale-free biologiques où peu de molécules ont beaucoup d'effets secondaires."
                )
            else:
                conclusions.append(
                    f"Le réseau SIDER ne suit pas strictement une loi de puissance pure (α={alpha:.2f}, R²={r_value**2:.3f}), "
                    f"mais montre une distribution hétérogène typique des réseaux biologiques réels."
                )
        
        return conclusions

    def save_PDF(self, output_path):
        """Génère le PDF avec tableau, histogrammes et conclusion"""
        print(f"📄 Génération du PDF: {output_path}")
        
        with PdfPages(output_path) as pdf:
            # Page 1: Tableau comparatif
            self._create_table_page(pdf)
            
            # Page 2: Histogrammes
            self._create_histogram_page(pdf)
            
            # Page 3: Analyse scale-free
            self._create_analysis_page(pdf)

    def _create_table_page(self, pdf):
        """Crée la page du tableau"""
        fig, ax = plt.subplots(figsize=(11, 8.5))
        ax.axis('off')
        
        # Titre
        fig.text(0.5, 0.97, 'Tableau Comparatif des Sources Biomédicales', 
                ha='center', fontsize=16, fontweight='bold')
        fig.text(0.5, 0.93, 'AlloDoctor Project - Analyse des Données', 
                ha='center', fontsize=10, style='italic', color='gray')
        
        # Préparation des données
        headers = ['Source', 'Nature', 'Entités', 'Détails', 'Couverture/Relations']
        rows = []
        
        for source in ['DrugBank', 'OMIM', 'HPO', 'SIDER', 'STITCH']:
            if source in self.stats:
                s = self.stats[source]
                
                # Composition de la ligne
                if source == 'DrugBank':
                    rows.append([
                        source,
                        s['Type'],
                        f"{s['Total médicaments']:,}",
                        f"Indic.: {s['Avec indications']}, Tox.: {s['Avec toxicité']}",
                        s['Couverture']
                    ])
                elif source == 'OMIM':
                    rows.append([
                        source,
                        s['Type'],
                        f"{s['Total maladies']:,}",
                        f"Desc.: {s['Avec description']}",
                        s['Couverture']
                    ])
                elif source == 'HPO':
                    rows.append([
                        source,
                        s['Type'],
                        f"{s['Termes d\'ontologie']:,}",
                        f"Syn.: {s['Synonymes']:,}",
                        f"{s['Total annotations']:,}"
                    ])
                elif source == 'SIDER':
                    rows.append([
                        source,
                        s['Type'],
                        f"{s['Total molécules']:,}",
                        f"ES: {s['Total effets secondaires']:,}, Ind.: {s['Total indications']:,}",
                        s['Relations']
                    ])
                elif source == 'STITCH':
                    rows.append([
                        source,
                        s['Type'],
                        f"{s['Composés chimiques']:,}",
                        'Interactions protéine-chimique',
                        s['Couverture']
                    ])
        
        # Création du tableau
        table = ax.table(cellText=rows, colLabels=headers, cellLoc='left', 
                        loc='center', colWidths=[0.12, 0.25, 0.15, 0.25, 0.23])
        
        table.auto_set_font_size(False)
        table.set_fontsize(9)
        table.scale(1, 2.8)
        
        # Style des entêtes
        for i in range(len(headers)):
            cell = table[(0, i)]
            cell.set_facecolor('#4CAF50')
            cell.set_text_props(weight='bold', color='white')
        
        # Alternance de couleurs
        for i in range(1, len(rows) + 1):
            for j in range(len(headers)):
                cell = table[(i, j)]
                if i % 2 == 0:
                    cell.set_facecolor('#f0f0f0')
                else:
                    cell.set_facecolor('#ffffff')
                cell.set_edgecolor('#cccccc')
        
        plt.tight_layout(rect=[0, 0.02, 1, 0.95])
        pdf.savefig(fig, bbox_inches='tight')
        plt.close(fig)

    def _create_histogram_page(self, pdf):
        """Crée la page avec histogrammes"""
        fig, axes = plt.subplots(1, 2, figsize=(11, 8.5))
        
        fig.suptitle('Analyse des Distributions - Sources Biomédicales', 
                    fontsize=14, fontweight='bold', y=0.98)
        
        # Histogramme 1: Distribution des effets secondaires par molécule (SIDER)
        if 'SIDER' in self.distributions:
            degrees = np.array(self.distributions['SIDER'])
            
            ax = axes[0]
            ax.hist(degrees, bins=30, color='#FF6B6B', alpha=0.7, edgecolor='black')
            ax.set_xlabel('Nombre d\'effets secondaires par molécule', fontweight='bold')
            ax.set_ylabel('Nombre de molécules', fontweight='bold')
            ax.set_title('SIDER: Distribution des Effets Secondaires', fontweight='bold')
            ax.grid(axis='y', alpha=0.3)
            
            # Statistiques
            stats_text = (
                f"n = {len(degrees):,}\n"
                f"μ = {np.mean(degrees):.1f}\n"
                f"σ = {np.std(degrees):.1f}\n"
                f"max = {np.max(degrees)}"
            )
            ax.text(0.98, 0.97, stats_text, transform=ax.transAxes, 
                   fontsize=9, verticalalignment='top', horizontalalignment='right',
                   bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        # Histogramme 2: Distribution log-log (scale-free test)
        if 'SIDER' in self.distributions and hasattr(self, 'scale_free_metrics'):
            degrees = np.array(self.distributions['SIDER'])
            
            ax = axes[1]
            sorted_degrees = np.sort(degrees)[::-1]
            ranks = np.arange(1, len(sorted_degrees) + 1)
            
            # Scatter plot log-log
            ax.loglog(ranks, sorted_degrees, 'o', color='#4CAF50', alpha=0.6, markersize=4)
            
            # Ligne de tendance
            x = np.log10(ranks)
            y = np.log10(sorted_degrees)
            z = np.polyfit(x, y, 1)
            p = np.poly1d(z)
            ax.loglog(ranks, 10**p(x), "r-", linewidth=2, label=f'Tendance (α={-z[0]:.2f})')
            
            ax.set_xlabel('Rang (log)', fontweight='bold')
            ax.set_ylabel('Nombre d\'effets secondaires (log)', fontweight='bold')
            ax.set_title('SIDER: Analyse Log-Log (Scale-free test)', fontweight='bold')
            ax.legend(loc='upper right')
            ax.grid(True, alpha=0.3, which='both')
            
            # Métriques
            metrics = self.scale_free_metrics
            metrics_text = (
                f"α = {metrics['alpha']:.2f}\n"
                f"R² = {metrics['r_value']**2:.3f}\n"
                f"Scale-free: {'✓' if metrics['is_scale_free'] else '✗'}"
            )
            ax.text(0.98, 0.03, metrics_text, transform=ax.transAxes, 
                   fontsize=9, verticalalignment='bottom', horizontalalignment='right',
                   bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.7))
        
        plt.tight_layout()
        pdf.savefig(fig, bbox_inches='tight')
        plt.close(fig)

    def _create_analysis_page(self, pdf):
        """Crée la page d'analyse mathématique"""
        fig = plt.figure(figsize=(11, 8.5))
        ax = fig.add_subplot(111)
        ax.axis('off')
        
        # Titre
        fig.text(0.5, 0.95, 'Conclusion Mathématique', 
                ha='center', fontsize=16, fontweight='bold')
        fig.text(0.5, 0.91, 'Analyse de la Nature Scale-Free des Réseaux Biomédicaux', 
                ha='center', fontsize=11, style='italic', color='gray')
        
        # Contenu
        conclusions = self.detect_scale_free()
        
        y_pos = 0.83
        for i, conclusion in enumerate(conclusions, 1):
            # Convertir les **textes** en italiques pour l'affichage
            text = conclusion.replace('**', '')
            wrapped_text = self._wrap_text(text, 100)
            
            fig.text(0.08, y_pos, f"{i}.", fontsize=11, fontweight='bold')
            fig.text(0.12, y_pos, wrapped_text, fontsize=11, wrap=True, 
                    verticalalignment='top', fontfamily='sans-serif')
            
            y_pos -= 0.15 * (len(wrapped_text.split('\n')))
        
        # Signature
        fig.text(0.5, 0.05, f'Analyse générée: AlloDoctor Analysis Suite', 
                ha='center', fontsize=9, style='italic', color='gray')
        
        pdf.savefig(fig, bbox_inches='tight')
        plt.close(fig)

    @staticmethod
    def _wrap_text(text, width):
        """Enveloppe le texte"""
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            current_line.append(word)
            if len(' '.join(current_line)) > width:
                lines.append(' '.join(current_line[:-1]))
                current_line = [word]
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return '\n'.join(lines)


def main():
    # Initialisation
    analyzer = SourceAnalyzer()
    
    print("=" * 60)
    print("AlloDoctor - Analyse Comparative des Sources")
    print("=" * 60)
    print()
    
    # Analyses
    analyzer.run_all_analyses()
    
    print()
    print("=" * 60)
    print("Génération du rapport PDF...")
    print("=" * 60)
    
    # Génération du PDF
    output_pdf = SOURCES_DIR / "SOURCES_ANALYSIS.pdf"
    analyzer.save_PDF(str(output_pdf))
    
    print(f"✅ PDF généré : {output_pdf}")
    print()
    
    # Affichage des conclusions
    print("📋 Conclusions Mathématiques:")
    print("-" * 60)
    for conclusion in analyzer.detect_scale_free():
        print(conclusion)
    print("-" * 60)


if __name__ == '__main__':
    main()
