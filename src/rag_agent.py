"""Agent de recherche cadré (RAG lexical, pas d'embeddings) sur la BDPM.

Principe : retrouver d'abord les lignes réellement pertinentes dans la base
structurée (recherche par mot-clé sur le nom du médicament et les substances
actives), puis ne laisser l'IA que reformuler/synthétiser strictement à
partir de ces lignes, jamais inventer un médicament ou un dosage. Chaque
réponse cite les codes CIS utilisés, pour rester vérifiable en un clic sur
la BDPM officielle.

Choix assumé : pas de recherche vectorielle/embeddings ici, une recherche
lexicale suffit sur un référentiel à vocabulaire fixe et exact (noms de
médicaments et de substances, pas du texte libre ambigu) — et reste
transposable à un vrai moteur vectoriel si le volume de requêtes en langage
très libre l'exigeait un jour.
"""


def rechercher_medicaments(query, dim_medicaments, fact_compositions, top_k=5):
    """Retourne jusqu'à top_k codes CIS pertinents pour la requête, avec un score
    simple (nombre de correspondances mot-clé sur le nom du médicament et les
    substances actives associées)."""
    termes = [t.strip().lower() for t in query.split() if len(t.strip()) >= 3]
    if not termes:
        return []

    med = dim_medicaments.copy()
    med["_nom_lower"] = med["denomination"].str.lower()

    substances_par_cis = (
        fact_compositions.groupby("cis_code")["denomination_substance"]
        .apply(lambda s: " | ".join(sorted(set(s.dropna()))))
        .rename("_substances")
    )
    med = med.merge(substances_par_cis, on="cis_code", how="left")
    med["_substances"] = med["_substances"].fillna("")
    med["_substances_lower"] = med["_substances"].str.lower()

    def _score(row):
        texte = row["_nom_lower"] + " " + row["_substances_lower"]
        score = sum(1 for t in termes if t in texte)
        if score and row["etat_commercialisation"] == "Commercialisée":
            score += 0.5  # priorise les médicaments réellement disponibles sur les archivés
        return score

    med["_score"] = med.apply(_score, axis=1)
    resultats = med[med["_score"] > 0].sort_values("_score", ascending=False).head(top_k)
    return resultats["cis_code"].tolist()


def construire_contexte(cis_codes, dim_medicaments, fact_compositions, fact_presentations):
    """Construit un bloc de texte structuré, une fiche par médicament trouvé,
    strictement à partir des données réelles de la base — rien n'est inventé
    ni complété ici."""
    blocs = []
    for cis in cis_codes:
        med = dim_medicaments[dim_medicaments["cis_code"] == cis]
        if med.empty:
            continue
        med = med.iloc[0]

        compo = fact_compositions[fact_compositions["cis_code"] == cis]
        substances = "; ".join(
            f"{r.denomination_substance} ({r.dosage_substance or 'dosage non renseigné'})"
            for r in compo.itertuples()
        ) or "non renseignée"

        pres = fact_presentations[fact_presentations["cis_code"] == cis]
        prix_info = "non renseigné"
        if not pres.empty and pres["prix_eur"].notna().any():
            ligne = pres[pres["prix_eur"].notna()].iloc[0]
            prix_info = f"{ligne.prix_eur:.2f} EUR, remboursement {ligne.taux_remboursement or 'non renseigné'}"

        blocs.append(
            f"[CIS {cis}] {med.denomination}\n"
            f"  Forme : {med.forme_pharmaceutique} | Voie(s) : {med.voies_administration}\n"
            f"  Substance(s) active(s) : {substances}\n"
            f"  Statut : {med.statut_amm}, {med.etat_commercialisation}\n"
            f"  Titulaire AMM : {med.titulaire}\n"
            f"  Prix/remboursement (1re présentation trouvée) : {prix_info}"
        )
    return "\n\n".join(blocs) if blocs else "Aucun médicament trouvé dans la base pour cette recherche."


def repondre_avec_claude(question, contexte, api_key):
    """Synthèse strictement groundée sur le contexte fourni. Retourne None si
    l'appel échoue (l'app affiche alors le contexte brut, jamais une erreur
    silencieuse remplacée par une réponse inventée)."""
    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=api_key)
        prompt = (
            "Tu es un assistant de consultation de la Base de Données Publique des "
            "Médicaments (BDPM, ANSM). Réponds à la question UNIQUEMENT à partir des "
            "fiches ci-dessous, jamais avec une connaissance médicale externe. Si "
            "l'information demandée n'est pas dans les fiches, dis-le explicitement "
            "plutôt que de la déduire ou de l'inventer. Cite systématiquement le code "
            "CIS de chaque médicament mentionné dans ta réponse.\n\n"
            f"Fiches disponibles :\n{contexte}\n\n"
            f"Question : {question}"
        )
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001", max_tokens=500, temperature=0,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text.strip()
    except Exception:
        return None
