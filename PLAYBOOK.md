# Playbook : PharmAUtomate

> Guide opératoire structuré en 4 volets (Définitions / Process / Documentation / Templates),
> pour comprendre, réutiliser ou transposer ce projet à un contexte réel.
> Rappel : projet personnel (PoC), données réelles et publiques (BDPM/ANSM, licence Etalab), voir [`README.md`](README.md).

---

## 1. Définitions

**Vocabulaire du domaine**

| Terme | Définition |
|---|---|
| **BDPM** | Base de Données Publique des Médicaments, référentiel officiel ANSM, licence ouverte Etalab, mise à jour mensuelle |
| **CIS** | Code Identifiant de Spécialité, identifiant unique d'un médicament dans la BDPM |
| **RAG lexical** | Retrieval-Augmented Generation par recherche mot-clé (pas d'embeddings) : on retrouve d'abord les lignes pertinentes dans la base, l'IA ne fait que synthétiser strictement à partir de ces lignes |
| **Grounding** | Contraindre une réponse IA à ne s'appuyer que sur un contexte fourni, jamais sur sa connaissance générale, avec citation systématique de la source |

**Modèle de données** : `dim_medicaments` (1 ligne par CIS), `fact_compositions` (1 ligne par substance active par médicament), `fact_presentations` (1 ligne par présentation commerciale, avec prix et taux de remboursement).

---

## 2. Process

```mermaid
flowchart LR
    A[1. Téléchargement BDPM] --> B[2. Structuration DuckDB]
    B --> C[3. Recherche lexicale + synthèse groundée]
    C --> D[4. Dashboard Streamlit]
```

1. **Ingestion** (`src/ingest.py`) : téléchargement direct des 3 fichiers officiels, encodage ISO-8859-1 décodé explicitement, mise en cache locale.
2. **Structuration** (`src/pipeline.py`) : jointures DuckDB, contrôle d'intégrité référentielle (lignes de composition/présentation sans médicament associé, comptées, jamais corrigées en silence).
3. **Recherche** (`src/rag_agent.py`) : scoring lexical sur noms de médicaments et substances, priorité aux médicaments commercialisés, contexte texte structuré, synthèse Claude groundée avec citation des CIS.
4. **Dashboard** (`app.py`) : recherche, exploration des 3 tables, tableau de bord qualité.

**Point de décision réutilisable** : ne jamais laisser l'IA répondre sans contexte récupéré au préalable, même pour une base au vocabulaire aussi précis que la BDPM, le prompt de synthèse interdit explicitement toute connaissance médicale externe et impose la citation du CIS.

---

## 3. Documentation

- [`README.md`](README.md), contexte métier, architecture, stack, chiffres réels du dernier chargement
- [`PROMPT_LOG.md`](PROMPT_LOG.md), méthode de construction avec l'IA, y compris la vérification de la structure réelle des fichiers BDPM avant d'écrire le parsing

---

## 4. Templates réutilisables

- **`src/ingest.py`**, pattern de téléchargement + cache local + décodage explicite d'un encodage hérité (ISO-8859-1), transposable à toute donnée publique française ancienne (Sirene, data.gouv.fr).
- **`src/pipeline.py`**, structuration DuckDB avec contrôle d'intégrité référentielle explicite entre plusieurs fichiers sources, même pattern que les autres pipelines qualité du portfolio.
- **`src/rag_agent.py`**, pattern de RAG lexical + synthèse groundée avec citation systématique de la source, réutilisable pour tout référentiel à vocabulaire exact (technique, réglementaire, juridique) sans avoir besoin d'un moteur d'embeddings.

**Règle de transposition** : pour appliquer à un cas réel (fiches techniques internes, notices produit, documentation normative), remplacer `ingest.py` par une extraction du référentiel du client (PDF, export interne) et adapter le schéma de `pipeline.py`, `rag_agent.py` reste inchangé, c'est le composant le plus directement réutilisable.

---

*Gisèle Metouck, Consultante Data Steward & Gouvernance · [GitHub](https://github.com/Kingdmfncr)*
