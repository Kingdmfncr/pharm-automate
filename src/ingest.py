"""Ingestion de la Base de Données Publique des Médicaments (BDPM, ANSM).

Source réelle, licence ouverte (Etalab) : base-donnees-publique.medicaments.gouv.fr
Mise à jour mensuelle par l'ANSM. Aucune donnée patient, aucune donnée confidentielle :
uniquement le référentiel public des médicaments commercialisés ou l'ayant été en France.

Obligation de la licence : mentionner la source et la date de mise à jour à chaque
usage (voir README.md et l'app), ne jamais altérer le sens des données.
"""
from datetime import date
from pathlib import Path

import pandas as pd
import requests

BASE_URL = "https://base-donnees-publique.medicaments.gouv.fr/download/file"
RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"

FICHIERS = {
    "CIS_bdpm.txt": "medicaments",
    "CIS_COMPO_bdpm.txt": "compositions",
    "CIS_CIP_bdpm.txt": "presentations",
}

# Colonnes déduites de la structure réelle des fichiers (positions observées,
# pas de documentation officielle machine-readable trouvée). À corriger si
# l'ANSM publie un schéma qui contredirait une de ces colonnes.
COLONNES_MEDICAMENTS = [
    "cis_code", "denomination", "forme_pharmaceutique", "voies_administration",
    "statut_amm", "type_procedure_amm", "etat_commercialisation", "date_amm",
    "statut_bdm", "numero_autorisation_europeenne", "titulaire", "surveillance_renforcee",
]
COLONNES_COMPOSITIONS = [
    "cis_code", "forme_pharmaceutique", "code_substance", "denomination_substance",
    "dosage_substance", "reference_dosage", "nature_composant", "numero_liaison",
]
COLONNES_PRESENTATIONS = [
    "cis_code", "code_cip7", "libelle_presentation", "statut_administratif_presentation",
    "etat_commercialisation_presentation", "date_declaration_commercialisation",
    "code_cip13", "agrement_collectivites", "taux_remboursement",
    "prix_1", "prix_2", "honoraire_dispensation", "indications_remboursement",
]


def telecharger_fichiers_bdpm(force=False):
    """Télécharge les 3 fichiers BDPM si absents localement (cache simple sur disque,
    pas de re-téléchargement à chaque run)."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    chemins = {}
    for nom_fichier in FICHIERS:
        chemin = RAW_DIR / nom_fichier
        if force or not chemin.exists():
            reponse = requests.get(f"{BASE_URL}/{nom_fichier}", timeout=30)
            reponse.raise_for_status()
            chemin.write_bytes(reponse.content)
        chemins[nom_fichier] = chemin
    (RAW_DIR / "date_telechargement.txt").write_text(date.today().isoformat(), encoding="utf-8")
    return chemins


def _lire_tsv_latin1(chemin, colonnes):
    return pd.read_csv(
        chemin, sep="\t", header=None, names=colonnes, encoding="latin-1",
        dtype=str, keep_default_na=False, na_values=[""], engine="python",
    )


def charger_medicaments(chemin=None):
    chemin = chemin or (RAW_DIR / "CIS_bdpm.txt")
    return _lire_tsv_latin1(chemin, COLONNES_MEDICAMENTS)


def charger_compositions(chemin=None):
    chemin = chemin or (RAW_DIR / "CIS_COMPO_bdpm.txt")
    return _lire_tsv_latin1(chemin, COLONNES_COMPOSITIONS)


def charger_presentations(chemin=None):
    chemin = chemin or (RAW_DIR / "CIS_CIP_bdpm.txt")
    return _lire_tsv_latin1(chemin, COLONNES_PRESENTATIONS)


def date_derniere_maj():
    fichier = RAW_DIR / "date_telechargement.txt"
    return fichier.read_text(encoding="utf-8").strip() if fichier.exists() else "inconnue"


def main():
    print("Téléchargement des fichiers BDPM (base-donnees-publique.medicaments.gouv.fr)...")
    chemins = telecharger_fichiers_bdpm()
    for nom, chemin in chemins.items():
        taille_ko = chemin.stat().st_size // 1024
        print(f"  {nom} -> {chemin} ({taille_ko} Ko)")

    df_med = charger_medicaments()
    df_compo = charger_compositions()
    df_pres = charger_presentations()
    print(f"\n{len(df_med)} médicaments, {len(df_compo)} lignes de composition, {len(df_pres)} présentations.")
    print(f"Exemple médicament : {df_med.iloc[0]['denomination']}")


if __name__ == "__main__":
    main()
