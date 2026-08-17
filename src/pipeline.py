"""Structuration relationnelle de la BDPM dans DuckDB (moteur SQL embarqué,
zéro serveur à connecter, même logique que les autres pipelines du portfolio).

Modèle : dim_medicaments (1 ligne par CIS) + fact_compositions (1 ligne par
substance active par médicament) + fact_presentations (1 ligne par
présentation commerciale, avec prix et taux de remboursement).
"""
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA_PROCESSED = ROOT / "data" / "processed"
ENTREPOT_PATH = DATA_PROCESSED / "bdpm.duckdb"


def _nettoyer_prix(serie):
    """'24,34' (format FR, virgule décimale) -> 24.34 (float). Chaîne vide -> NaN."""
    return pd.to_numeric(serie.str.replace(",", ".", regex=False), errors="coerce")


def construire_dim_medicaments(df_med):
    df = df_med.copy()
    df["date_amm"] = pd.to_datetime(df["date_amm"], format="%d/%m/%Y", errors="coerce")
    return df[[
        "cis_code", "denomination", "forme_pharmaceutique", "voies_administration",
        "statut_amm", "etat_commercialisation", "date_amm", "titulaire", "surveillance_renforcee",
    ]]


def construire_fact_compositions(df_compo):
    df = df_compo.copy()
    return df[[
        "cis_code", "code_substance", "denomination_substance", "dosage_substance", "nature_composant",
    ]]


def construire_fact_presentations(df_pres):
    df = df_pres.copy()
    df["taux_remboursement"] = df["taux_remboursement"]
    df["prix_eur"] = _nettoyer_prix(df["prix_2"].fillna(df["prix_1"]))
    return df[[
        "cis_code", "code_cip13", "libelle_presentation", "etat_commercialisation_presentation",
        "taux_remboursement", "prix_eur",
    ]]


def run_pipeline(df_med, df_compo, df_pres, con=None):
    """Retourne (tables: dict[str, DataFrame], con: connexion DuckDB ouverte)."""
    con = con or duckdb.connect(database=":memory:")

    dim_medicaments = construire_dim_medicaments(df_med)
    fact_compositions = construire_fact_compositions(df_compo)
    fact_presentations = construire_fact_presentations(df_pres)

    con.register("dim_medicaments_df", dim_medicaments)
    con.register("fact_compositions_df", fact_compositions)
    con.register("fact_presentations_df", fact_presentations)

    con.execute("CREATE OR REPLACE TABLE dim_medicaments AS SELECT * FROM dim_medicaments_df")
    con.execute("""
        CREATE OR REPLACE TABLE fact_compositions AS
        SELECT c.*, m.denomination
        FROM fact_compositions_df c
        LEFT JOIN dim_medicaments_df m USING (cis_code)
    """)
    con.execute("""
        CREATE OR REPLACE TABLE fact_presentations AS
        SELECT p.*, m.denomination
        FROM fact_presentations_df p
        LEFT JOIN dim_medicaments_df m USING (cis_code)
    """)

    # Signal de qualité simple et honnête : combien de compositions/présentations
    # référencent un CIS absent du référentiel médicaments (intégrité référentielle),
    # sans corriger silencieusement, juste compté et exposé.
    orphelins_compo = con.execute(
        "SELECT count(*) FROM fact_compositions WHERE denomination IS NULL"
    ).fetchone()[0]
    orphelins_pres = con.execute(
        "SELECT count(*) FROM fact_presentations WHERE denomination IS NULL"
    ).fetchone()[0]

    tables = {
        "dim_medicaments": con.execute("SELECT * FROM dim_medicaments").fetchdf(),
        "fact_compositions": con.execute("SELECT * FROM fact_compositions").fetchdf(),
        "fact_presentations": con.execute("SELECT * FROM fact_presentations").fetchdf(),
    }
    qualite = {
        "nb_medicaments": len(tables["dim_medicaments"]),
        "nb_compositions": len(tables["fact_compositions"]),
        "nb_presentations": len(tables["fact_presentations"]),
        "compositions_orphelines": int(orphelins_compo),
        "presentations_orphelines": int(orphelins_pres),
    }
    return tables, qualite, con


def main():
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import ingest

    df_med = ingest.charger_medicaments()
    df_compo = ingest.charger_compositions()
    df_pres = ingest.charger_presentations()

    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    if ENTREPOT_PATH.exists():
        ENTREPOT_PATH.unlink()

    con = duckdb.connect(database=str(ENTREPOT_PATH))
    tables, qualite, con = run_pipeline(df_med, df_compo, df_pres, con=con)
    con.close()

    print("Qualité du modèle relationnel :")
    for cle, valeur in qualite.items():
        print(f"  {cle} : {valeur}")
    print(f"\nEntrepôt persisté -> {ENTREPOT_PATH}")


if __name__ == "__main__":
    main()
