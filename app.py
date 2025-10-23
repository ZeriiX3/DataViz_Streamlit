import streamlit as st
from pathlib import Path
import pandas as pd

from sections.intro import render as render_intro
from sections.overview import render as render_overview
from sections.debug import render as render_debug

from utils.io import load_data_cached, dir_signature
from utils.prep import make_df_clean_cached

st.set_page_config(
    page_title="Paris, un marché en mutation (2020–2024)",
    page_icon="📊",
    layout="wide",
)

st.title("Paris, un marché en mutation (2020–2024)")
st.caption("DVF géolocalisées (data.gouv.fr) — Département 75")

# ---------- Chargement (avec cache) ----------
sig = dir_signature("data")
df_raw = load_data_cached(sig, "data")
df_clean = make_df_clean_cached(df_raw)

# ---------- Sidebar ----------
with st.sidebar:
    st.header("Projet & Données")
    data_dir = Path("data")
    files = sorted(data_dir.glob("75_*.csv")) if data_dir.exists() else []
    if files:
        st.success(f"{len(files)} fichier(s) détecté(s)")
        for f in files:
            st.write("•", f.name)
    else:
        st.info("Aucun fichier `75_*.csv` trouvé.")

    st.divider()
    st.subheader("Filtres (globaux)")
    years_avail = df_clean["annee"].dropna().astype(int)
    ymin, ymax = int(years_avail.min()), int(years_avail.max())

    if "surface_reelle_bati" in df_clean.columns:
        s_min = int(max(0, float(df_clean["surface_reelle_bati"].min() or 0)))
        s_max = int(float(df_clean["surface_reelle_bati"].quantile(0.99)))
    else:
        s_min, s_max = 0, 200

    types = sorted(df_clean["type_local"].dropna().astype(str).unique()) if "type_local" in df_clean.columns else []
    arr_all = sorted([int(a) for a in df_clean["arrondissement"].dropna().unique()]) if "arrondissement" in df_clean.columns else []

    if st.button("↺ Réinitialiser les filtres"):
        for k in ("flt_years", "flt_types", "flt_arr", "flt_surface", "show_map", "map_sample"):
            if k in st.session_state:
                del st.session_state[k]

    year_range = st.slider(
        "Période (années)", ymin, ymax, value=(ymin, ymax), step=1, key="flt_years",
        help="Années inclusives de la sélection."
    )
    type_sel = st.multiselect(
        "Type de bien", options=types, default=types, key="flt_types",
        help="Appartement et/ou Maison."
    )
    arr_sel = st.multiselect(
        "Arrondissements (01–20)", options=arr_all, default=arr_all, key="flt_arr",
        help="Filtre géographique intra-muros."
    )
    surface_range = st.slider(
        "Surface bâtie (m²)", s_min, s_max, value=(max(9, s_min), s_max), step=1, key="flt_surface",
        help="Exclut les biens hors plage sélectionnée."
    )

    st.divider()
    st.subheader("Carte (optionnel)")
    st.checkbox("Afficher la carte (échantillon)", value=False, key="show_map")
    st.slider("Taille échantillon carte", 2000, 20000, 5000, 1000, key="map_sample")

# ---------- Application des filtres globaux ----------
df_sel = df_clean.copy()
df_sel = df_sel[(df_sel["annee"] >= year_range[0]) & (df_sel["annee"] <= year_range[1])]

if type_sel and "type_local" in df_sel.columns:
    df_sel = df_sel[df_sel["type_local"].isin(type_sel)]

if "arrondissement" in df_sel.columns and arr_sel:
    df_sel = df_sel[df_sel["arrondissement"].isin(arr_sel)]

if "surface_reelle_bati" in df_sel.columns:
    df_sel = df_sel[
        (df_sel["surface_reelle_bati"] >= float(surface_range[0])) &
        (df_sel["surface_reelle_bati"] <= float(surface_range[1]))
    ]

# ---------- Tabs ----------
tab_intro, tab_overview, tab_debug = st.tabs(["Intro", "Overview", "Debug"])

with tab_intro:
    render_intro()

with tab_overview:
    if df_sel.empty:
        st.warning("Aucune donnée pour ces filtres. Élargis la période, les types ou les arrondissements.")
    else:
        # on lit directement les paramètres de la sidebar dans overview via st.session_state
        render_overview(df_sel)

with tab_debug:
    render_debug(df_clean)

# ---------- Footer : Source & Licence ----------
st.markdown("---")
st.markdown(
    """
    <div style="font-size:0.9rem; opacity:0.9; line-height:1.5;">
      <b>Source & licence.</b>
      Données <i>Demandes de valeurs foncières (DVF) géolocalisées – Paris (75)</i> :
      <a href="https://www.data.gouv.fr/datasets/demandes-de-valeurs-foncieres-geolocalisees/" target="_blank">page dataset sur data.gouv.fr</a>.<br/>
      Réutilisation conforme à la <i>Licence Ouverte / Etalab</i> — mention de paternité&nbsp;: DGFiP, Etalab.
    </div>
    """,
    unsafe_allow_html=True,
)
