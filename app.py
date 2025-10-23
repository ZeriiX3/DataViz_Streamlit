import streamlit as st
from pathlib import Path

from sections.intro import render as render_intro
from sections.overview import render as render_overview
from sections.debug import render as render_debug

from utils.io import load_data_cached, dir_signature
from utils.prep import make_df_clean_cached

# Chargement des données (df_raw + df_clean)
sig = dir_signature("data")
df_raw = load_data_cached(sig, "data")
df_clean = make_df_clean_cached(df_raw)

st.set_page_config(
    page_title="Paris, un marché en mutation (2020–2024)",
    page_icon="📊",
    layout="wide",
)

st.title("Paris, un marché en mutation (2020–2024)")
st.caption("DVF géolocalisées (data.gouv.fr) — Département 75")

# Bandeau court (visible sur tous les onglets)
st.markdown(
    """
**Paris, un marché en mutation (2020–2024).**  
À partir des **DVF géolocalisées (75)**, ce tableau de bord raconte le basculement post-Covid : **prix au m², volumes, mix** par période, arrondissement et typologie.

**🎯 Objectifs.** Comprendre le cycle (pic 2021–2022 → refroidissement 2023–2024) · Comparer par arrondissement & type de bien · Aider à décider (timing, budget, surface).  
**🧾 Périmètre.** Ventes de logements (appartements/maisons), 2020–2024 · Nettoyage : normalisation, **prix/m²**, filtres cohérence (surfaces < 9 m², coupe douce des extrêmes).  
**🔎 Lecture.** D’abord **Overview** (3 KPIs) → **Deep Dives** (Temps, Géographie, Mix, Distribution, Qualité) → **Conclusion**. 
"""
)

# --- Sidebar : état des fichiers ---
with st.sidebar:
    st.header("Projet")
    st.write("**Dossier données (./data)** : `75_2020.csv` … `75_2024.csv`")
    data_dir = Path("data")
    if data_dir.exists():
        files = sorted(data_dir.glob("75_*.csv"))
        if files:
            st.success("Fichiers détectés :")
            for f in files:
                st.write("•", f.name)
        else:
            st.info("Aucun fichier `75_*.csv` trouvé.")
    else:
        st.info("Le dossier `./data` n’existe pas encore.")

# --- TAB ----
tab_intro, tab_overview, tab_debug = st.tabs(["Intro", "Overview", "Debug"])

with tab_intro:
    render_intro()

with tab_overview:
    render_overview()

with tab_debug:
    render_debug(df_clean)


# Footer

st.markdown("---")
st.markdown(
    """
    <div style="font-size:0.9rem; opacity:0.9; line-height:1.5;">
      <b>Source & licence.</b>
      Données <i>Demandes de valeurs foncières (DVF) géolocalisées – Paris (75)</i> :
      <a href="https://www.data.gouv.fr/datasets/demandes-de-valeurs-foncieres-geolocalisees/" target="_blank">page dataset sur data.gouv.fr</a>.<br/>
      Réutilisation conforme à la <i>Licence Ouverte 2.0 / Etalab</i>
    </div>
    """,
    unsafe_allow_html=True,
)