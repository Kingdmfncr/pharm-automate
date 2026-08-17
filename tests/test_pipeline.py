"""Tests unitaires, structuration DuckDB et agent de recherche.
DataFrames construits à la main (pas de téléchargement réseau dans les tests,
pour rester rapides et déterministes) plutôt que le vrai jeu BDPM.
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import pipeline as data_pipeline
import rag_agent


def _dim_test():
    return pd.DataFrame({
        "cis_code": ["111", "222"],
        "denomination": ["PARACETAMOL TEST 500 mg", "IBUPROFENE TEST 400 mg"],
        "forme_pharmaceutique": ["comprimé", "comprimé"],
        "voies_administration": ["orale", "orale"],
        "statut_amm": ["Autorisation active", "Autorisation active"],
        "etat_commercialisation": ["Commercialisée", "Non commercialisée"],
        "titulaire": ["LABO A", "LABO B"],
        "surveillance_renforcee": ["Non", "Non"],
    })


def _compo_test():
    return pd.DataFrame({
        "cis_code": ["111", "222", "999"],
        "code_substance": ["01", "02", "03"],
        "denomination_substance": ["PARACETAMOL", "IBUPROFENE", "SUBSTANCE ORPHELINE"],
        "dosage_substance": ["500 mg", "400 mg", "10 mg"],
        "nature_composant": ["SA", "SA", "SA"],
    })


def _pres_test():
    return pd.DataFrame({
        "cis_code": ["111", "999"],
        "code_cip13": ["3400900000001", "3400900000002"],
        "libelle_presentation": ["plaquette de 8", "boîte de 10"],
        "etat_commercialisation_presentation": ["Présentation active", "Présentation active"],
        "taux_remboursement": ["65%", "65%"],
        "prix_eur": [2.5, 3.0],
    })


def test_run_pipeline_structure_correctement():
    dim_source = pd.DataFrame({
        "cis_code": ["111", "222"], "denomination": ["PARACETAMOL TEST 500 mg", "IBUPROFENE TEST 400 mg"],
        "forme_pharmaceutique": ["comprimé", "comprimé"], "voies_administration": ["orale", "orale"],
        "statut_amm": ["Autorisation active", "Autorisation active"], "type_procedure_amm": ["", ""],
        "etat_commercialisation": ["Commercialisée", "Non commercialisée"], "date_amm": ["01/01/2020", "01/01/2020"],
        "statut_bdm": ["", ""], "numero_autorisation_europeenne": ["", ""],
        "titulaire": ["LABO A", "LABO B"], "surveillance_renforcee": ["Non", "Non"],
    })
    compo_source = pd.DataFrame({
        "cis_code": ["111", "999"], "forme_pharmaceutique": ["comprimé", "comprimé"],
        "code_substance": ["01", "03"], "denomination_substance": ["PARACETAMOL", "SUBSTANCE ORPHELINE"],
        "dosage_substance": ["500 mg", "10 mg"], "reference_dosage": ["un comprimé", "un comprimé"],
        "nature_composant": ["SA", "SA"], "numero_liaison": ["1", "1"],
    })
    pres_source = pd.DataFrame({
        "cis_code": ["111", "999"], "code_cip7": ["1234567", "7654321"],
        "libelle_presentation": ["plaquette de 8", "boite de 10"],
        "statut_administratif_presentation": ["Présentation active", "Présentation active"],
        "etat_commercialisation_presentation": ["Présentation active", "Présentation active"],
        "date_declaration_commercialisation": ["01/01/2020", "01/01/2020"],
        "code_cip13": ["3400900000001", "3400900000002"],
        "agrement_collectivites": ["oui", "oui"], "taux_remboursement": ["65%", "65%"],
        "prix_1": ["2,50", "3,00"], "prix_2": ["2,60", "3,10"],
        "honoraire_dispensation": ["1,02", "1,02"], "indications_remboursement": ["", ""],
    })

    tables, qualite, con = data_pipeline.run_pipeline(dim_source, compo_source, pres_source)
    con.close()

    assert qualite["nb_medicaments"] == 2
    assert qualite["nb_compositions"] == 2
    assert qualite["nb_presentations"] == 2
    # cis_code 999 existe dans compositions/presentations mais pas dans dim_medicaments -> 1 orphelin chacun
    assert qualite["compositions_orphelines"] == 1
    assert qualite["presentations_orphelines"] == 1
    assert round(tables["fact_presentations"]["prix_eur"].iloc[0], 2) == 2.60


def test_recherche_priorise_les_medicaments_commercialises():
    dim = _dim_test()
    compo = _compo_test()
    resultats = rag_agent.rechercher_medicaments("test", dim, compo, top_k=2)
    assert resultats[0] == "111"  # commercialisé, doit passer devant le 222 (non commercialisé)


def test_recherche_matche_sur_le_nom_de_substance():
    dim = _dim_test()
    compo = _compo_test()
    resultats = rag_agent.rechercher_medicaments("ibuprofene", dim, compo, top_k=5)
    assert "222" in resultats


def test_recherche_sans_terme_pertinent_renvoie_vide():
    dim = _dim_test()
    compo = _compo_test()
    resultats = rag_agent.rechercher_medicaments("xyznotfound123", dim, compo, top_k=5)
    assert resultats == []


def test_construire_contexte_cite_le_code_cis():
    dim = _dim_test()
    compo = _compo_test()
    pres = _pres_test()
    contexte = rag_agent.construire_contexte(["111"], dim, compo, pres)
    assert "[CIS 111]" in contexte
    assert "PARACETAMOL" in contexte
    assert "2.50 EUR" in contexte or "2.5" in contexte


def test_construire_contexte_vide_si_aucun_cis():
    dim = _dim_test()
    compo = _compo_test()
    pres = _pres_test()
    contexte = rag_agent.construire_contexte([], dim, compo, pres)
    assert "Aucun médicament trouvé" in contexte


def test_repondre_avec_claude_sans_cle_valide_renvoie_none():
    reponse = rag_agent.repondre_avec_claude("question", "contexte", api_key="cle-invalide-de-test")
    assert reponse is None
