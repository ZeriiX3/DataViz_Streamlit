# sections/deep_dives.py
# Deep dives P1 vs P2 + analyses par arrondissement

import streamlit as st
import pandas as pd
import numpy as np
import altair as alt


# --- compat Altair: width="stretch" vs use_container_width=True
def _altair(chart, title: str | None = None):
    if title:
        chart = chart.properties(title=title)
    try:
        st.altair_chart(chart, width="stretch")
    except TypeError:
        st.altair_chart(chart, use_container_width=True)


# ---------- helpers ----------
def _period_flag(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    if "annee" not in d.columns:
        d["annee"] = pd.to_datetime(d["date_mutation"], errors="coerce").dt.year

    # pd.cut produit un dtype 'category' 
    d["periode2"] = pd.cut(
        d["annee"],
        bins=[2019, 2021, 2024],                  
        labels=["P1: 2020-2021", "P2: 2022-2024"],
        right=True,
        include_lowest=False,
    )

    d = d.dropna(subset=["periode2"]).copy()
    d["periode2"] = d["periode2"].astype(str)
    return d


def _small_mask(df: pd.DataFrame) -> pd.Series:
    if "classe_surface_m2" in df.columns:
        return df["classe_surface_m2"].astype(str).isin(["<25", "25-40"])
    if "surface_reelle_bati" in df.columns:
        return pd.to_numeric(df["surface_reelle_bati"], errors="coerce") <= 40
    return pd.Series(False, index=df.index)


def _hist_overlay(df1, df2, col="prix_m2", bins=40):
    """Histogrammes pré-calculés pour P1 vs P2)."""
    s1 = pd.to_numeric(df1[col], errors="coerce")
    s2 = pd.to_numeric(df2[col], errors="coerce")
    both = pd.concat([s1, s2], ignore_index=True)
    lo = np.nanquantile(both, 0.01)
    hi = np.nanquantile(both, 0.99)
    edges = np.linspace(lo, hi, bins + 1)

    def _mk(s, label):
        cts, ed = np.histogram(s.dropna().clip(lo, hi), bins=edges)
        mid = (ed[:-1] + ed[1:]) / 2
        return pd.DataFrame({"bin_mid": mid, "count": cts, "periode2": label})

    return pd.concat([_mk(s1, "P1: 2020-2021"), _mk(s2, "P2: 2022-2024")], ignore_index=True)


# ---------- main ----------
def render(df: pd.DataFrame):
    st.header("Deep dives")

    # Chapô 
    st.markdown(
        """
Le Deep Dives met en évidence les écarts qui apparaissent depuis le Covid : **où** les prix reculent le plus,
**comment** le mix de biens évolue et **quelles zones** combinent niveau de prix et activité. La comparaison entre
**P1 (2020-2021)** et **P2 (2022-2024)** permet d'isoler le changement de régime. Les visuels s'adaptent aux filtres
de la barre latérale.
        """
    )

    # Préparation commune
    d = _period_flag(df)
    has_arr = "arrondissement" in d.columns and not d["arrondissement"].isna().all()

    tabs = st.tabs([
        "Variation des prix (P1 vs P2)",
        "Volume vs niveau",
        "Distribution des prix",
        "Tableau détaillé",
    ])

    # ------------------------------------------------------------------
    # 1) Variation P1 vs P2 par arrondissement
    # ------------------------------------------------------------------
    with tabs[0]:
        st.subheader("Où les prix ont-ils le plus reculé depuis 2021 ?")
        if not has_arr:
            st.info("Pas de colonne `arrondissement` exploitable dans la sélection.")
        else:
            g = (
                d.dropna(subset=["arrondissement", "prix_m2"])
                 .groupby(["arrondissement", "periode2"], observed=True)
                 .agg(prix_m2_median=("prix_m2", "median"),
                      ventes=("prix_m2", "size"))
                 .reset_index()
            )
            p1 = g[g["periode2"].str.startswith("P1")][["arrondissement", "prix_m2_median"]].rename(columns={"prix_m2_median": "p1"})
            p2 = g[g["periode2"].str.startswith("P2")][["arrondissement", "prix_m2_median"]].rename(columns={"prix_m2_median": "p2"})
            delta = p1.merge(p2, on="arrondissement", how="inner")
            delta["variation_%"] = (delta["p2"] - delta["p1"]) / delta["p1"] * 100
            delta = delta.sort_values("variation_%")  # baisses en haut

            topn = st.slider("Top N baisses", 5, 20, 10, step=1, key="dd_topn_baisses")
            show = delta.head(topn).sort_values("variation_%")

            chart = (
                alt.Chart(show)
                .mark_bar(color="#d94e4e")
                .encode(
                    x=alt.X("variation_%:Q", title="Variation (%)"),
                    y=alt.Y("arrondissement:O", sort=None, title="Arr."),
                    tooltip=[
                        alt.Tooltip("arrondissement:O", title="Arr."),
                        alt.Tooltip("p1:Q", format=",.0f", title="Médiane P1 (€/m²)"),
                        alt.Tooltip("p2:Q", format=",.0f", title="Médiane P2 (€/m²)"),
                        alt.Tooltip("variation_%:Q", format=".1f", title="Δ %"),
                    ],
                )
            )
            _altair(chart, "Variation du prix médian €/m² - P2 vs P1")

            st.markdown(
                """
Le classement met en avant les arrondissements où la baisse relative entre P1 et P2 est la plus nette.
Les infobulles donnent les médianes P1 et P2 pour situer l'ampleur du recul par rapport au niveau de départ.
La variation (%) négatif = baisse
                """
            )

    # ------------------------------------------------------------------
    # 2) Volume vs niveau - P1 vs P2
    # ------------------------------------------------------------------
    with tabs[1]:
        st.subheader("Quelles zones combinent niveau de prix élevé et activité ? (P1 vs P2)")

        if not has_arr:
            st.info("Pas de colonne `arrondissement` exploitable.")
        else:
            base = (
                d.dropna(subset=["arrondissement", "prix_m2"])
                .groupby(["arrondissement", "periode2"], observed=True)
                .agg(
                    prix_m2_median=("prix_m2", "median"),
                    ventes=("prix_m2", "size"),
                ).reset_index()
            )

            # On ne garde que P1 et P2 si elles existent (évite d'autres labels)
            base = base[base["periode2"].isin(["P1: 2020-2021", "P2: 2022-2024"])]
            if base.empty or base["periode2"].nunique() < 2:
                st.info("Il faut des données pour P1 et P2 pour comparer.")
            else:
                # Lignes reliant P1 -> P2 pour chaque arrondissement
                lines = (
                    alt.Chart(base)
                    .mark_line(opacity=0.35, color="#9aa0a6")  # trait neutre
                    .encode(
                        x=alt.X("ventes:Q", title="Transactions (#)"),
                        y=alt.Y("prix_m2_median:Q", title="Prix médian (€/m²)"),
                        detail="arrondissement:N"
                    )
                )

                # Points P1 vs P2
                points = (
                    alt.Chart(base)
                    .mark_circle()
                    .encode(
                        x=alt.X("ventes:Q", title="Transactions (#)"),
                        y=alt.Y("prix_m2_median:Q", title="Prix médian (€/m²)"),
                        size=alt.Size("ventes:Q", legend=None),
                        color=alt.Color("periode2:N", title="Période", scale=alt.Scale(scheme="set2")),
                        shape=alt.Shape("periode2:N", title="Période"),
                        tooltip=[
                            alt.Tooltip("arrondissement:O", title="Arr."),
                            alt.Tooltip("periode2:N", title="Période"),
                            alt.Tooltip("ventes:Q", title="# ventes"),
                            alt.Tooltip("prix_m2_median:Q", format=",.0f", title="€/m² médian"),
                        ],
                    )
                )

                chart3 = (lines + points).properties(
                    title="Transactions vs prix médian — P1 (2020-2021) et P2 (2022-2024)"
                )

                _altair(chart3)

                st.markdown(
                    """
    Les traits relient l'évolution **P1 -> P2** pour chaque arrondissement.  
    En haut à droite : zones **chères** et **actives** ; un déplacement vers la gauche/bas signale **moins d'activité** et/ou **prix plus bas**.
                    """
                )





    # ------------------------------------------------------------------
    # 4) Distribution des prix (overlay d’histogrammes)
    # ------------------------------------------------------------------
    with tabs[2]:
        st.subheader("La distribution des prix s'est-elle déplacée entre P1 et P2 ?")
        p1_df = d[d["periode2"].str.startswith("P1")]
        p2_df = d[d["periode2"].str.startswith("P2")]

        if p1_df.empty or p2_df.empty:
            st.info("Données insuffisantes dans l'une des périodes pour tracer la distribution.")
        else:
            hist = _hist_overlay(p1_df, p2_df, col="prix_m2", bins=40)
            chart = (
                alt.Chart(hist)
                .mark_area(opacity=0.45)
                .encode(
                    x=alt.X("bin_mid:Q", title="€/m²"),
                    y=alt.Y("count:Q", title="Transactions (#)"),
                    color=alt.Color("periode2:N", title="Période", scale=alt.Scale(scheme="set2")),
                    tooltip=[
                        alt.Tooltip("periode2:N", title="Période"),
                        alt.Tooltip("bin_mid:Q", format=",.0f", title="€/m²"),
                        alt.Tooltip("count:Q", title="#"),
                    ],
                )
            )
            _altair(chart, "Histogrammes superposés")

            st.markdown(
                """
Un décalage de l'aire P2 vers la gauche traduit un niveau de prix plus bas qu'en P1 ; une aire plus comprimée
indique une dispersion moindre. L'inverse signale une hausse ou une polarisation. La comparaison porte à la fois
sur la position (niveau) et la largeur (dispersion) des deux distributions.
                """
            )

    # ------------------------------------------------------------------
    # 5) Tableau complet
    # ------------------------------------------------------------------
    with tabs[3]:
        st.subheader("Tableau détaillé - P1 vs P2 par arrondissement")
        if not has_arr:
            st.info("Pas de colonne `arrondissement` exploitable.")
        else:
            agg = (
                d.dropna(subset=["arrondissement", "prix_m2"])
                 .assign(is_small=_small_mask)
                 .groupby(["arrondissement", "periode2"], observed=True)
                 .agg(
                    ventes=("prix_m2", "size"),
                    prix_m2_med=("prix_m2", "median"),
                    prix_m2_p10=("prix_m2", lambda s: np.nanpercentile(s, 10)),
                    prix_m2_p90=("prix_m2", lambda s: np.nanpercentile(s, 90)),
                    part_small=("is_small", "mean"),
                    surf_med=("surface_reelle_bati", "median"),
                 )
                 .reset_index()
            )
            agg["part_small"] = (agg["part_small"] * 100).round(1)
            agg = agg.sort_values(["periode2", "arrondissement"])

            st.dataframe(
                agg.rename(columns={
                    "periode2": "Période", "arrondissement": "Arr.",
                    "ventes": "Ventes (#)", "prix_m2_med": "€/m² médian",
                    "prix_m2_p10": "p10", "prix_m2_p90": "p90",
                    "part_small": "% ≤ 40 m²", "surf_med": "Surface médiane"
                }),
                width="stretch"
            )

            st.markdown(
                """
Ce tableau permet de naviguer rapidement entre le niveau (€/m²), la dispersion, le mix (% ≤ 40 m²)
et la liquidité (ventes) pour chaque arrondissement et chaque période.

                """
            )
