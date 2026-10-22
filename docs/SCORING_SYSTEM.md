# Système de Scoring — AlloDoctor

## Vue d'ensemble

Les résultats de recherche dans AlloDoctor sont triés par **score de pertinence**. Ce document explique comment ce score est calculé dynamiquement en fonction de :

1. **Consensus inter-sources** (convergence des données)
2. **Couverture symptomatique** (nombre de termes correspondants)
3. **Pertinence source** (fiabilité du lien trouvé)
4. **Contexte clinique** (disponibilité de données cliniques)

---

## Formule du Score Global

```
Score Total = (Consensus × 10) + (Coverage × 10) + Pertinence + Clinique
```

### Composantes

| Composante | Calcul | Explication |
|-----------|--------|------------|
| **Consensus** | `nombre_sources × 10` | Si un résultat apparaît dans 2 sources, +20 points. Dans 3 sources, +30 points. Plus de sources = plus de fiabilité |
| **Coverage** | `tokens_correspondants × 10` | Si 2 termes de la requête correspondent au résultat, +20 points. Mesure la complétude de correspondance |
| **Pertinence** | Voir tableau ci-dessous | Score attribué par la source (1–10) basé sur la qualité du lien |
| **Clinique** | Score clinique | Points bonus si données cliniques disponibles (actuellement 0 par défaut) |

---

## Scores de Pertinence par Source

### OMIM (Ontologie des maladies)

**Formule** : `max(1.0, min(10.0, 10.0 - |rank|))`

| Rang | Pertinence | Contexte |
|------|-----------|---------|
| 0 | 10.0 | Correspondance la plus proche |
| 1 | 9.0 | Très bonne correspondance |
| 2 | 8.0 | Bonne correspondance |
| 3 | 7.0 | Correspondance acceptable |
| 4+ | ≤ 6.0 | Correspondance faible |
| -1, -2... | 10.0, 9.0... | Rang négatif inversé |

**Exemple** : Si une maladie OMIM a rang 2, score = 10 - 2 = **8.0**

### DrugBank (Médicaments et toxicité)

**Formule** : `max(1, min(10, 10 - abs(rank)))`

| Rang | Pertinence | Contexte |
|------|-----------|---------|
| 0 | 10 | Correspondance excellente (indication ou toxicité primaire) |
| 1 | 9 | Très bonne correspondance |
| 2 | 8 | Bonne correspondance |
| 5 | 5 | Correspondance moyenne |
| 10+ | 1 (minimum) | Correspondance très faible |

**Exemple** : Un médicament DrugBank au rang 3 obtient = 10 - 3 = **7**

### SIDER (Effets secondaires et indications)

**Formule** : `10.0` (fixe)

- Tous les résultats SIDER reçoivent le score maximum **10.0**
- Raison : SIDER contient des données structurées et validées via CUI UMLS

### HPO (Human Phenotype Ontology)

**Formule** : `0.0` (fixe)

- Les termes HPO sont utilisés pour **initier** les recherches, pas pour le classement
- Pertinence supplémentaire via fusion avec SIDER/OMIM/DrugBank

### STITCH (Search Tool for Interactions of Chemicals)

**Formule** : `max(1.0, min(10.0, 10.0 - |rank|))`

| Rang | Pertinence | Contexte |
|------|-----------|---------|
| 0 | 10.0 | Correspondance la plus proche |
| 1 | 9.0 | Très bonne correspondance |
| 2 | 8.0 | Bonne correspondance |
| 3 | 7.0 | Correspondance acceptable |
| 5 | 5.0 | Correspondance moyenne |
| 10+ | ≤ 1.0 | Correspondance très faible |

**Exemple** : Une interaction STITCH au rang 2 obtient = 10 - 2 = **8.0**

- STITCH résout les noms de médicaments/composés vers identifiants lisibles
- Formule identique à OMIM via FTS5 (rank vient de la pertinence de recherche textuelle)

---

## Exemple Complet

### Requête : "fatigue AND dépression"

**Résultat 1** : Hypothyroïdie (OMIM)
- **Consensus** : Trouvé dans HPO + OMIM = 2 sources → `2 × 10 = 20`
- **Coverage** : 1 token sur 2 correspond ("fatigue") → `1 × 10 = 10`
- **Pertinence OMIM** : Rang 1 → `10 - 1 = 9`
- **Clinique** : `0`
- **Score total** = 20 + 10 + 9 + 0 = **39 points**

**Résultat 2** : Atorvastatine / interaction (DrugBank)
- **Consensus** : Trouvé dans DrugBank seul = 1 source → `1 × 10 = 10`
- **Coverage** : 2 tokens correspondent ("fatigue", "dépression") → `2 × 10 = 20`
- **Pertinence DrugBank** : Rang 4 → `10 - 4 = 6`
- **Clinique** : `0`
- **Score total** = 10 + 20 + 6 + 0 = **36 points**

**Résultat 3** : Dépression majeure (SIDER + OMIM)
- **Consensus** : Trouvé dans SIDER + OMIM + HPO = 3 sources → `3 × 10 = 30`
- **Coverage** : 1 token ("dépression"), 0 pour "fatigue" → `1 × 10 = 10`
- **Pertinence** : SIDER (10.0) + OMIM (rang 0 = 10.0) → `(10 + 10) / 2 ≈ 10`
- **Clinique** : `0`
- **Score total** = 30 + 10 + 10 + 0 = **50 points**  **En tête du classement**

---

## Facteurs de Classement (ordre d'importance)

```
Rang 1 : Consensus (0–30 points max)
Rang 2 : Pertinence source (0–10 points max)
Rang 3 : Coverage symptomatique (0–20 points max)
Rang 4 : Clinique (0–X points, actuellement 0)
```

**Insight** : Un résultat dans **3 sources** bat presque tout résultat dans **1 seule source**, même si la pertinence est moyenne.

---

## Cas Particuliers

### Fusion de résultats identiques

Si un même résultat apparaît dans plusieurs chemins (ex: "Hypothyroïdie" trouvée via HPO à travers SIDER + via OMIM directement) :

1. Les scores de pertinence sont **moyennés**
2. Le consensus compte **tous les chemins uniques**
3. La coverage accumule **tous les tokens correspondants trouvés par n'importe quel chemin**

### Tri final

```python
results = sorted(results, key=lambda x: x["score"], reverse=True)
```

Les résultats sont triés **décroissants** (score le plus haut en premier).

---
