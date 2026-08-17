"""PharmAUtomate — Pipeline de structuration de données réglementaires (Santé/Pharma).
Ingestion de la BDPM (ANSM, licence ouverte Etalab), structuration relationnelle
DuckDB, et recherche cadrée (RAG lexical) avec réponses sourcées et citées.
"""
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

SRC_DIR = Path(__file__).resolve().parent / "src"
sys.path.insert(0, str(SRC_DIR))

import ingest
import pipeline as data_pipeline
import rag_agent

C_PRIMARY = "#0071E3"
C_GOOD    = "#34C759"
C_WARNING = "#FF9F0A"
C_DANGER  = "#FF3B30"
C_SURF    = "#F5F5F7"
C_TEXT    = "#1D1D1F"
C_MUTED   = "#6E6E73"
C_BORDER  = "#E8E8ED"

CHART_DEFAULTS = dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color=C_TEXT, family="Inter, -apple-system, sans-serif", size=13),
    margin=dict(l=20, r=20, t=40, b=20),
)

st.set_page_config(page_title="PharmAUtomate", page_icon="💊",
                   layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
html, body, [class*="css"] { font-family:'Inter',-apple-system,sans-serif; }
div[data-testid="stMetricValue"] { font-size: 1.6rem; font-weight: 700; }
.stTabs [aria-selected="true"] { font-weight: 700; }
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=86400, show_spinner="Téléchargement et structuration de la BDPM (ANSM)...")
def load_all():
    ingest.telecharger_fichiers_bdpm()
    df_med = ingest.charger_medicaments()
    df_compo = ingest.charger_compositions()
    df_pres = ingest.charger_presentations()
    tables, qualite, con = data_pipeline.run_pipeline(df_med, df_compo, df_pres)
    con.close()
    date_maj = ingest.date_derniere_maj()
    return tables, qualite, date_maj


tables, qualite, date_maj = load_all()
dim_medicaments = tables["dim_medicaments"]
fact_compositions = tables["fact_compositions"]
fact_presentations = tables["fact_presentations"]

with st.sidebar:
    st.markdown(
        "<div style='text-align:center;padding:12px 0;'>"
        "<div style='font-size:1.8rem;'>💊</div>"
        f"<div style='color:{C_PRIMARY};font-size:1.0rem;font-weight:700;'>PharmAUtomate</div>"
        f"<div style='color:{C_MUTED};font-size:0.72rem;'>Structuration & recherche BDPM</div>"
        "</div>", unsafe_allow_html=True)
    st.markdown(f"<hr style='border-color:{C_BORDER};'>", unsafe_allow_html=True)

    api_key = st.text_input("Clé API Anthropic (optionnel)", type="password",
                             help="BYOK — utilisée uniquement pour synthétiser la réponse, jamais stockée.")
    st.caption("🔒 Sans clé : les fiches sources trouvées s'affichent directement, sans synthèse IA.")

    st.markdown(f"<hr style='border-color:{C_BORDER};'>", unsafe_allow_html=True)
    st.markdown(
        f"<div style='background:{C_SURF};border-radius:8px;padding:10px;font-size:0.75rem;color:{C_MUTED};'>"
        "📖 <strong>Données réelles, licence ouverte</strong><br>"
        "Base de Données Publique des Médicaments (ANSM), diffusée sous licence ouverte "
        "Etalab. Aucune donnée patient, aucune donnée confidentielle : uniquement le "
        f"référentiel public des médicaments. Dernière synchronisation locale : {date_maj}. "
        "Source : base-donnees-publique.medicaments.gouv.fr"
        "</div>", unsafe_allow_html=True)
    st.caption("Construit avec l'IA — Gisèle Metouck")
    st.caption("[GitHub](https://github.com/Kingdmfncr)")

st.title("PharmAUtomate")
st.caption("Recherche cadrée sur la Base de Données Publique des Médicaments : réponses sourcées, jamais inventées, chaque médicament cité par son code CIS vérifiable.")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Médicaments référencés", f"{qualite['nb_medicaments']:,}".replace(",", " "))
c2.metric("Lignes de composition", f"{qualite['nb_compositions']:,}".replace(",", " "))
c3.metric("Présentations commerciales", f"{qualite['nb_presentations']:,}".replace(",", " "))
taux_integrite = round(100 * (1 - (qualite["compositions_orphelines"] + qualite["presentations_orphelines"])
                               / (qualite["nb_compositions"] + qualite["nb_presentations"])), 2)
c4.metric("Intégrité référentielle", f"{taux_integrite}%")

tabs = st.tabs(["Recherche IA (RAG)", "Explorer la base", "Qualité & intégrité"])

with tabs[0]:
    st.caption("Exemples : \"paracetamol\", \"ibuprofene douleur\", \"atorvastatine cholesterol\"")
    question = st.text_input("Posez une question sur un médicament ou une substance")

    if question:
        cis_trouves = rag_agent.rechercher_medicaments(question, dim_medicaments, fact_compositions, top_k=5)
        contexte = rag_agent.construire_contexte(cis_trouves, dim_medicaments, fact_compositions, fact_presentations)

        if not cis_trouves:
            st.warning("Aucun médicament trouvé dans la base pour cette recherche.")
        else:
            reponse = rag_agent.repondre_avec_claude(question, contexte, api_key) if api_key else None
            if reponse:
                st.markdown(f"""<div style="background:{C_SURF};border-radius:10px;padding:20px;border-left:4px solid {C_PRIMARY};">
                  {reponse}
                </div>""", unsafe_allow_html=True)
                st.caption("Réponse générée par IA, strictement à partir des fiches BDPM ci-dessous.")
            elif api_key:
                st.info("Synthèse IA indisponible pour cette requête. Fiches sources trouvées ci-dessous.")
            st.markdown("**Fiches sources (BDPM), vérifiables sur base-donnees-publique.medicaments.gouv.fr :**")
            st.text(contexte)

with tabs[1]:
    sous_tab_med, sous_tab_compo, sous_tab_pres = st.tabs(["dim_medicaments", "fact_compositions", "fact_presentations"])
    with sous_tab_med:
        recherche = st.text_input("Filtrer par nom de médicament", key="filtre_med")
        df_affiche = dim_medicaments
        if recherche:
            df_affiche = df_affiche[df_affiche["denomination"].str.contains(recherche, case=False, na=False)]
        st.dataframe(df_affiche.head(500), use_container_width=True, hide_index=True)
        st.caption(f"{len(df_affiche)} résultat(s) — affichage limité aux 500 premiers.")
    with sous_tab_compo:
        st.dataframe(fact_compositions.head(500), use_container_width=True, hide_index=True)
    with sous_tab_pres:
        st.dataframe(fact_presentations.head(500), use_container_width=True, hide_index=True)

with tabs[2]:
    st.markdown("**Intégrité référentielle** — compositions et présentations dont le code CIS n'existe pas dans le référentiel médicaments (signalé, jamais corrigé en silence) :")
    d1, d2 = st.columns(2)
    d1.metric("Compositions orphelines", qualite["compositions_orphelines"])
    d2.metric("Présentations orphelines", qualite["presentations_orphelines"])

    rep_statut = dim_medicaments["etat_commercialisation"].value_counts()
    fig = go.Figure(go.Pie(labels=rep_statut.index, values=rep_statut.values, hole=0.55,
                            marker=dict(colors=[C_GOOD, C_MUTED, C_WARNING, C_DANGER])))
    fig.update_layout(title="Répartition des médicaments par état de commercialisation", height=340, **CHART_DEFAULTS)
    st.plotly_chart(fig, use_container_width=True, key="chart_etat_commercialisation")

    top_substances = (
        fact_compositions["denomination_substance"].value_counts().head(15).sort_values()
    )
    fig2 = go.Figure(go.Bar(x=top_substances.values, y=top_substances.index, orientation="h", marker_color=C_PRIMARY))
    fig2.update_layout(title="15 substances actives les plus fréquentes dans la base", height=420, **CHART_DEFAULTS)
    st.plotly_chart(fig2, use_container_width=True, key="chart_top_substances")
