import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

try:
    import pydeck as pdk
except Exception:
    pdk = None


def _ensure_period_index(df: pd.DataFrame) -> pd.DataFrame:
    if "trimestre" not in df.columns:
        return df.assign(tri_date=pd.NaT)
    tri = pd.PeriodIndex(df["trimestre"].astype(str), freq="Q")
    return df.assign(tri_date=tri.asfreq("Q").to_timestamp())


def _kpi(value, label, fmt=None, help_text=None):
    if fmt is not None and value is not None and not (isinstance(value, float) and np.isnan(value)):
        try:
            value = fmt.format(value)
        except Exception:
            pass
    st.metric(label, value if value is not None else "—", help=help_text)


def render(df: pd.DataFrame):
    st.header("🔎 Overview")

    # -----------------------
    # KPIs (ligne du haut)
    # -----------------------
    small_mask = df["classe_surface_m2"].astype(str).isin(["<25", "25–40"]) if "classe_surface_m2" in df.columns else pd.Series(False, index=df.index)
    prix_m2_med = float(np.nanmedian(df["prix_m2"])) if "prix_m2" in df.columns else np.nan
    vol = int(len(df))
    part_small = float(100 * small_mask.mean()) if len(df) else np.nan
    surf_med = float(np.nanmedian(df["surface_reelle_bati"])) if "surface_reelle_bati" in df.columns else np.nan
    pieces_med = float(np.nanmedian(df["nombre_pieces_principales"])) if "nombre_pieces_principales" in df.columns else np.nan

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        _kpi(prix_m2_med, "Prix médian (€/m²)", fmt="{:,.0f} €".replace(",", " "))
    with c2:
        _kpi(vol, "Transactions (sélection)")
    with c3:
        _kpi(part_small, "Part ≤ 40 m²", fmt="{:.1f} %")
    with c4:
        _kpi(surf_med, "Surface médiane (m²)", fmt="{:.0f}")
    with c5:
        _kpi(pieces_med, "Pièces médianes", fmt="{:.0f}")

    st.caption("KPIs calculés sur la **sélection courante** (sidebar).")

    # -----------------------
    # VISUEL 1 — Prix médian au m² (trimestriel)
    # -----------------------
    if {"prix_m2", "trimestre"}.issubset(df.columns):
        g_prix = (
            _ensure_period_index(df)
            .dropna(subset=["tri_date"])
            .groupby("trimestre", as_index=False, observed=True)
            .agg(prix_m2_median=("prix_m2", "median"))
            .assign(tri_date=lambda d: pd.PeriodIndex(d["trimestre"], freq="Q").asfreq("Q").to_timestamp())
            .sort_values("tri_date")
        )
        chart = (
            alt.Chart(g_prix, title="Prix médian au m² — trajectoire trimestrielle")
            .mark_line(point=True)
            .encode(
                x=alt.X("tri_date:T", title="Trimestre"),
                y=alt.Y("prix_m2_median:Q", title="Prix médian (€/m²)"),
                tooltip=["trimestre", alt.Tooltip("prix_m2_median:Q", format=",.0f", title="€/m²")],
            )
        )
        st.altair_chart(chart, theme="streamlit", use_container_width=True)
        st.caption("Alt text: courbe trimestrielle du prix médian au m².")
    else:
        st.info("Colonnes nécessaires absentes pour la trajectoire trimestrielle (prix_m2, trimestre).")

    # -----------------------
    # VISUEL 2 — Transactions par trimestre
    # -----------------------
    if "trimestre" in df.columns:
        base_group_col = "id_mutation" if "id_mutation" in df.columns else "date_mutation"
        g_vol = (
            _ensure_period_index(df)
            .dropna(subset=["tri_date"])
            .groupby("trimestre", as_index=False, observed=True)
            .agg(volume=(base_group_col, "count"))
            .assign(tri_date=lambda d: pd.PeriodIndex(d["trimestre"], freq="Q").asfreq("Q").to_timestamp())
            .sort_values("tri_date")
        )
        chart = (
            alt.Chart(g_vol, title="Transactions par trimestre")
            .mark_bar()
            .encode(
                x=alt.X("tri_date:T", title="Trimestre"),
                y=alt.Y("volume:Q", title="Transactions (#)"),
                tooltip=["trimestre", "volume"],
            )
        )
        st.altair_chart(chart, theme="streamlit", use_container_width=True)
        st.caption("Alt text: histogramme trimestriel des transactions.")
    else:
        st.info("Colonne 'trimestre' absente pour le volume trimestriel.")

    # -----------------------
    # VISUEL 3 — Part des petites surfaces (≤ 40 m²)
    # -----------------------
    if {"classe_surface_m2", "trimestre"}.issubset(df.columns):
        df_part = _ensure_period_index(df).dropna(subset=["tri_date"]).copy()
        df_part["is_small"] = df_part["classe_surface_m2"].astype(str).isin(["<25", "25–40"])
        g_part = (
            df_part.groupby("trimestre", as_index=False, observed=True)
            .agg(part_small=("is_small", "mean"))
            .assign(tri_date=lambda d: pd.PeriodIndex(d["trimestre"], freq="Q").asfreq("Q").to_timestamp())
            .sort_values("tri_date")
        )
        chart = (
            alt.Chart(g_part, title="Part des petites surfaces (≤ 40 m²) — trimestriel")
            .mark_line(point=True)
            .encode(
                x=alt.X("tri_date:T", title="Trimestre"),
                y=alt.Y("part_small:Q", axis=alt.Axis(format="%"), title="Part des petites surfaces"),
                tooltip=["trimestre", alt.Tooltip("part_small:Q", format=".1%")],
            )
        )
        st.altair_chart(chart, theme="streamlit", use_container_width=True)
        st.caption("Alt text: courbe de la part des petites surfaces par trimestre.")
    else:
        st.info("Colonnes nécessaires absentes pour la part des petites surfaces.")

    # -----------------------
    # VISUEL 4 — Classement arrondissements (prix médian)
    # -----------------------
    if {"arrondissement", "prix_m2"}.issubset(df.columns) and not df["arrondissement"].isna().all():
        g_arr = (
            df.dropna(subset=["arrondissement"])
              .groupby("arrondissement", as_index=False, observed=True)
              .agg(prix_m2_median=("prix_m2", "median"), n=("prix_m2", "size"))
              .sort_values("prix_m2_median", ascending=False)
        )
        topn = st.slider("Top N arrondissements par prix médian", 5, 20, 10, step=1)
        g_top = g_arr.head(topn).sort_values("prix_m2_median")
        chart = (
            alt.Chart(g_top, title="Arrondissements les plus chers (médiane sur la sélection)")
            .mark_bar()
            .encode(
                x=alt.X("prix_m2_median:Q", title="Prix médian (€/m²)"),
                y=alt.Y("arrondissement:O", sort=None, title="Arrondissement"),
                tooltip=[
                    alt.Tooltip("arrondissement:O", title="Arr."),
                    alt.Tooltip("prix_m2_median:Q", format=",.0f", title="€/m²"),
                    alt.Tooltip("n:Q", title="# ventes"),
                ],
            )
        )
        st.altair_chart(chart, theme="streamlit", use_container_width=True)
        st.caption("Alt text: barres horizontales du top N des arrondissements.")
    else:
        st.info("Colonnes nécessaires absentes pour le classement par arrondissement.")

    # -----------------------
    # CARTE (optionnelle)
    # -----------------------
    show_map = st.session_state.get("show_map", False)
    sample_size = int(st.session_state.get("map_sample", 5000))

    if show_map and pdk is not None and {"latitude", "longitude"}.issubset(df.columns):
        df_geo = df.dropna(subset=["latitude", "longitude"]).copy()
        df_geo["lat"] = pd.to_numeric(df_geo["latitude"], errors="coerce")
        df_geo["lon"] = pd.to_numeric(df_geo["longitude"], errors="coerce")
        df_geo = df_geo.dropna(subset=["lat", "lon"])
        if len(df_geo) > sample_size:
            df_geo = df_geo.sample(sample_size, random_state=42)

        midpoint = [df_geo["lat"].median(), df_geo["lon"].median()] if len(df_geo) else [48.8566, 2.3522]

        layer = pdk.Layer(
            "ScatterplotLayer",
            data=df_geo,
            get_position="[lon, lat]",
            get_radius=10,
            pickable=True,
            auto_highlight=True,
        )
        view_state = pdk.ViewState(latitude=midpoint[0], longitude=midpoint[1], zoom=10.5, bearing=0, pitch=0)
        st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view_state, tooltip={"text": "€/m²: {prix_m2}"}))
        st.caption("Alt text: carte des transactions (échantillon) positionnées par latitude/longitude.")
    elif show_map and pdk is None:
        st.info("pydeck non disponible. Ajoute `pydeck` à requirements.txt pour activer la carte.")

    # -----------------------
    # Échantillon de la sélection
    # -----------------------
    with st.expander("Voir un échantillon de la sélection"):
        st.dataframe(df.head(50), width="stretch")
