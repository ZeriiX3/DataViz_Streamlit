# app.py
import streamlit as st
from pathlib import Path

from sections.intro import render as render_intro
from sections.overview import render as render_overview
from sections.deep_dives import render as render_deep_dives
from sections.debug import render as render_debug

from utils.io import load_data_cached, dir_signature
from utils.prep import make_df_clean_cached


# ---------------------- Page config ----------------------
st.set_page_config(
    page_title="Paris, un marché en mutation (2020–2024)",
    page_icon="📊",
    layout="wide",
)

st.title("Paris, un marché en mutation (2020–2024)")
st.caption("DVF géolocalisées (data.gouv.fr) — Département 75")

# ---------------------- Chargement données (cache disque + cache mémoire) ----------------------
sig = dir_signature("data")               # signature du dossier ./data -> invalide le cache si les CSV changent
df_raw = load_data_cached(sig, "data")    # lecture CSV -> df_raw (cache)
df_clean = make_df_clean_cached(df_raw)   # préparation -> df_clean (cache)


# ---------------------- Sidebar ----------------------
with st.sidebar:
    st.header("Projet & Données")

    # Présence des fichiers attendus (75_2020..75_2024.csv)
    data_dir = Path("data")
    files = sorted(data_dir.glob("75_*.csv")) if data_dir.exists() else []
    expected_years = {2020, 2021, 2022, 2023, 2024}
    found_years = set()
    for f in files:
        try:
            y = int(f.stem.split("_")[1])
            if y in expected_years:
                found_years.add(y)
        except Exception:
            pass

    n_found = len(found_years)
    n_expected = len(expected_years)
    if n_found == n_expected:
        st.success(f"{n_found}/{n_expected} fichiers détectés")
    else:
        missing = ", ".join(map(str, sorted(expected_years - found_years))) or "—"
        st.warning(f"{n_found}/{n_expected} fichiers détectés — manquants : {missing}")

    st.divider()
    st.subheader("Filtres (globaux)")

    # Bornes calculées sur df_clean (complet)
    years_avail = df_clean["annee"].dropna().astype(int)
    ymin, ymax = int(years_avail.min()), int(years_avail.max())

    if "surface_reelle_bati" in df_clean.columns:
        s_min = int(max(0, float(df_clean["surface_reelle_bati"].min() or 0)))
        s_max = int(float(df_clean["surface_reelle_bati"].quantile(0.99)))  # borne haute robuste
    else:
        s_min, s_max = 0, 200

    types = sorted(df_clean["type_local"].dropna().astype(str).unique()) if "type_local" in df_clean.columns else []
    arr_all = sorted([int(a) for a in df_clean["arrondissement"].dropna().unique()]) if "arrondissement" in df_clean.columns else []

    # Initialisation unique (pas de value=/default= dans les widgets)
    st.session_state.setdefault("flt_years",   (ymin, ymax))
    st.session_state.setdefault("flt_types",   list(types))
    st.session_state.setdefault("flt_arr",     list(arr_all))
    st.session_state.setdefault("flt_surface", (max(9, s_min), s_max))

    # Bouton reset : met à jour l'état puis relance
    if st.button("↺ Réinitialiser les filtres"):
        st.session_state["flt_years"]   = (ymin, ymax)
        st.session_state["flt_types"]   = list(types)     # ["Appartement","Maison"] si présents
        st.session_state["flt_arr"]     = list(arr_all)   # 1..20
        st.session_state["flt_surface"] = (max(9, s_min), s_max)
        st.rerun()

    # Widgets (lisent uniquement via key -> pas d’avertissement)
    year_range = st.slider("Période (années)", ymin, ymax, key="flt_years",
                           help="Années inclusives de la sélection.")
    type_sel = st.multiselect("Type de bien", options=types, key="flt_types",
                              help="Appartement et/ou Maison.")
    arr_sel = st.multiselect("Arrondissements (01–20)", options=arr_all, key="flt_arr",
                             help="Filtre géographique intra-muros.")
    surface_range = st.slider("Surface bâtie (m²)", s_min, s_max, key="flt_surface",
                              help="Exclut les biens hors plage sélectionnée.")

# ---------------------- Application des filtres -> df_sel ----------------------
df_sel = df_clean.copy()

# Années
if "annee" in df_sel.columns:
    df_sel = df_sel[(df_sel["annee"] >= year_range[0]) & (df_sel["annee"] <= year_range[1])]

# Types
if type_sel and "type_local" in df_sel.columns:
    df_sel = df_sel[df_sel["type_local"].isin(type_sel)]

# Arrondissements
if "arrondissement" in df_sel.columns and arr_sel:
    df_sel = df_sel[df_sel["arrondissement"].isin(arr_sel)]

# Surface
if "surface_reelle_bati" in df_sel.columns:
    df_sel = df_sel[
        (df_sel["surface_reelle_bati"] >= float(surface_range[0])) &
        (df_sel["surface_reelle_bati"] <= float(surface_range[1]))
    ]


# ---------------------- Tabs ----------------------
tab_intro, tab_overview, tab_deep, tab_debug = st.tabs(["Intro", "Overview", "Deep Dives", "Debug"])

with tab_intro:
    render_intro(df_sel)

with tab_overview:
    if df_sel.empty:
        st.warning("Aucune donnée pour ces filtres. Élargis la période, les types ou les arrondissements.")
    else:
        render_overview(df_sel)  # KPIs & visuels branchés sur la sélection

with tab_deep:
    if df_sel.empty:
        st.info("Aucune donnée pour ces filtres.")
    else:
        render_deep_dives(df_sel)  # Q&R : comparaisons P1 vs P2


# ---------------------- Footer : Source & licence ----------------------
st.markdown("---")
st.markdown(
    """
    <div style="font-size:0.9rem; opacity:0.9; line-height:1.5;">
      <b>Source & licence.</b>
      Données <i>Demandes de valeurs foncières (DVF) géolocalisées – Paris (75)</i> :
      <a href="https://www.data.gouv.fr/datasets/demandes-de-valeurs-foncieres-geolocalisees/" target="_blank">page dataset sur data.gouv.fr</a>.<br/>
      Réutilisation conforme à la <i>Licence Ouverte 2.0 / Etalab</i>.
    </div>
    """,
    unsafe_allow_html=True,
)
