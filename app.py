import streamlit as st
from pathlib import Path

from sections.intro import render as render_intro
from sections.overview import render as render_overview
from sections.debug import render as render_debug

from utils.io import load_data
from utils.prep import make_df_clean

# Chargement des données (df_raw + df_clean)
df_raw = load_data("data")
df_clean = make_df_clean(df_raw)

st.set_page_config(
    page_title="Paris, un marché en mutation (2020–2024)",
    page_icon="📊",
    layout="wide",
)

st.title("Paris, un marché en mutation (2020–2024)")
st.caption("DVF géolocalisées (data.gouv.fr) — Département 75 — chargement brut puis préparation légère.")

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

tab_intro, tab_overview, tab_debug = st.tabs(["Intro", "Overview", "Debug"])

with tab_intro:
    render_intro()

with tab_overview:
    render_overview()

with tab_debug:
    render_debug(df_clean)

