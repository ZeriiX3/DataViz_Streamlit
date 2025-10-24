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
    # 0) KPIs — photo de la sélection
    # -----------------------
    st.subheader("KPIs")

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
        _kpi(vol, "Transactions")
    with c3:
        _kpi(part_small, "Part ≤ 40 m²", fmt="{:.1f} %")
    with c4:
        _kpi(surf_med, "Surface médiane (m²)", fmt="{:.0f}")
    with c5:
        _kpi(pieces_med, "Pièces médianes", fmt="{:.0f}")

    st.markdown(
        """
**Comment lire ces KPIs ?**  
Ils donnent la **photo instantanée de ta sélection** (filtres à gauche) : niveau de **prix**, **activité**, **mix** (part des petites surfaces),
**taille** et **pièces**.

**À observer**
- Si le prix médian **2024 < 2020**, le **cycle baissier** est installé.
- Si la part ≤ 40 m² **monte**, on voit des **contraintes de budget**.
- Compare **Appartements / Maisons** ou **arrondissements** pour repérer les écarts.

> Ces indicateurs réagissent à chaque filtre et posent le **contexte** pour les graphes ci-dessous.
"""
    )

    # -----------------------
    # 1) Trajectoire du prix médian (trimestriel)
    # -----------------------
    st.subheader("1) Trajectoire du prix médian (trimestriel)")
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
            alt.Chart(g_prix, title="Prix médian au m² — trimestriel")
            .mark_line(point=True)
            .encode(
                x=alt.X("tri_date:T", title="Trimestre"),
                y=alt.Y("prix_m2_median:Q", title="Prix médian (€/m²)"),
                tooltip=["trimestre", alt.Tooltip("prix_m2_median:Q", format=",.0f", title="€/m²")],
            )
        )
        st.altair_chart(chart, theme="streamlit", use_container_width=True)
        st.markdown(
            """
Chaque point correspond à la **médiane €/m² par trimestre**.

**À observer**
- **Avant / après 2021** : le **palier** puis la **bascule** éventuelle.
- **2023-2024** : confirme-t-on un **refroidissement** ?
- Filtre par **type** ou **arrondissement** pour voir **qui résiste** (courbe plus plate) et **qui décroche**.

> Ce graphe raconte le **cycle des prix** : s'il baisse alors que la part ≤ 40 m² monte, on a un **recentrage** du marché.
"""
        )
    else:
        st.info("Colonnes nécessaires absentes pour la trajectoire (prix_m2, trimestre).")

    # -----------------------
    # 2) Volumes de transactions (trimestriel)
    # -----------------------
    st.subheader("2) Volumes de transactions (trimestriel)")
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
        st.markdown(
            """
Chaque barre = **nombre de ventes** au trimestre.

**À observer**
- **Creux 2023–2024** → marché **moins liquide** (taux, financement, attentisme).
- **Rebond** dans certains filtres (ex. **petites surfaces**) = poches de **demande**.
- Croise avec le **prix** : volumes qui repartent pendant que les prix reculent → **ré-ajustement** en cours.

> Les volumes mesurent la **liquidité** : un marché actif mais moins cher ≠ un marché bloqué.
"""
        )
    else:
        st.info("Colonne 'trimestre' absente pour le volume trimestriel.")

    # -----------------------
    # 3) Part des petites surfaces (≤ 40 m²)
    # -----------------------
    st.subheader("3) Part des petites surfaces (≤ 40 m²)")
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
        st.markdown(
            """
La courbe montre la **proportion** de ventes ≤ **40 m²**.

**À observer**
- **Hausse** après 2021 → **arbitrage d’espace** (budgets contraints, primo-accédants).
- **Baisse** dans certains arrondissements → retour de biens plus grands / segment haut.
- Compare **Appartements/Maisons** pour séparer **effet mix** et **prix**.

> Avec la trajectoire des prix, ça permet de dire si le marché **se recentre** ou **se polarise**.
"""
        )
    else:
        st.info("Colonnes nécessaires absentes pour la part des petites surfaces.")

    # -----------------------
    # 4) Classement des arrondissements (médiane €/m²)
    # -----------------------
    st.subheader("4) Classement des arrondissements (médiane €/m²)")
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
        st.markdown(
            """
Classement par **médiane €/m²** sur la sélection.

**À observer**
- Le **gradient intra-Paris** (ouest/centre vs nord/est).
- Filtres par **période** : certains arrondissements **décrochent** plus que d’autres.
- Regarde aussi le **# ventes** (tooltip) : un rang élevé mais peu de ventes = **niche**.

> Ce classement localise où le **niveau** est le plus tendu, à confronter avec la **carte**.
"""
        )
    else:
        st.info("Colonnes nécessaires absentes pour le classement par arrondissement.")

    # -----------------------
    # 5) Carte des transactions (couleur = quantile de prix/m²)
    # -----------------------
    st.subheader("5) Carte des transactions (couleur = quantile de prix/m²)")
    if pdk is not None and {"latitude", "longitude", "prix_m2"}.issubset(df.columns):
        df_geo = df.dropna(subset=["latitude", "longitude", "prix_m2"]).copy()
        df_geo["lat"] = pd.to_numeric(df_geo["latitude"], errors="coerce")
        df_geo["lon"] = pd.to_numeric(df_geo["longitude"], errors="coerce")
        df_geo["prix_m2"] = pd.to_numeric(df_geo["prix_m2"], errors="coerce")
        df_geo = df_geo.dropna(subset=["lat", "lon", "prix_m2"])

        if df_geo.empty:
            st.info("Aucun point géolocalisé dans la sélection actuelle (ou colonnes lat/lon/prix manquantes).")
        else:
            # échantillon pour perfs
            sample_size = 6000
            if len(df_geo) > sample_size:
                df_geo = df_geo.sample(sample_size, random_state=42)

            # binning prix -> quantiles
            if len(df_geo) >= 5:
                qs = df_geo["prix_m2"].quantile([0.2, 0.4, 0.6, 0.8]).values
                bins = [-np.inf, qs[0], qs[1], qs[2], qs[3], np.inf]
                labels = [
                    f"≤ {qs[0]/1000:.1f}k €/m²",
                    f"{qs[0]/1000:.1f}–{qs[1]/1000:.1f}k",
                    f"{qs[1]/1000:.1f}–{qs[2]/1000:.1f}k",
                    f"{qs[2]/1000:.1f}–{qs[3]/1000:.1f}k",
                    f"> {qs[3]/1000:.1f}k €/m²",
                ]
            else:
                mn, mx = float(df_geo["prix_m2"].min()), float(df_geo["prix_m2"].max())
                step = (mx - mn) / 5 if mx > mn else 1
                bins = [mn-1, mn+step, mn+2*step, mn+3*step, mn+4*step, mx+1]
                labels = [
                    f"≤ {bins[1]/1000:.1f}k €/m²",
                    f"{bins[1]/1000:.1f}–{bins[2]/1000:.1f}k",
                    f"{bins[2]/1000:.1f}–{bins[3]/1000:.1f}k",
                    f"{bins[3]/1000:.1f}–{bins[4]/1000:.1f}k",
                    f"> {bins[4]/1000:.1f}k €/m²",
                ]

            df_geo["prix_m2_bin"] = pd.cut(df_geo["prix_m2"], bins=bins, labels=labels, include_lowest=True)

            palette = {
                labels[0]: (33, 158, 188),
                labels[1]: (67, 170, 139),
                labels[2]: (253, 210, 97),
                labels[3]: (244, 96, 54),
                labels[4]: (157, 0, 57),
            }
            cols = df_geo["prix_m2_bin"].astype("string").map(palette)
            df_geo["r"] = cols.apply(lambda c: c[0] if isinstance(c, tuple) else 200)
            df_geo["g"] = cols.apply(lambda c: c[1] if isinstance(c, tuple) else 200)
            df_geo["b"] = cols.apply(lambda c: c[2] if isinstance(c, tuple) else 200)

            midpoint = [df_geo["lat"].median(), df_geo["lon"].median()] if len(df_geo) else [48.8566, 2.3522]

            layer = pdk.Layer(
                "ScatterplotLayer",
                data=df_geo,
                get_position="[lon, lat]",
                get_fill_color="[r, g, b, 170]",
                get_radius=8,                 # pixels 
                radius_units="pixels",
                radius_min_pixels=3,
                radius_max_pixels=28,
                pickable=True,
                auto_highlight=True,
                stroked=False,
            )
            view_state = pdk.ViewState(latitude=midpoint[0], longitude=midpoint[1], zoom=10.5, bearing=0, pitch=0)
            st.pydeck_chart(
                pdk.Deck(
                    layers=[layer],
                    initial_view_state=view_state,
                    tooltip={"text": "€/m²: {prix_m2}\nClasse: {prix_m2_bin}"},
                )
            )

            legend_items = "".join(
                f'<div style="display:flex;align-items:center;margin-right:10px;">'
                f'<span style="display:inline-block;width:12px;height:12px;border-radius:50%;'
                f'background:rgb{palette.get(lbl, (200,200,200))};margin-right:6px;"></span>'
                f'<span>{lbl}</span></div>'
                for lbl in labels
            )
            st.markdown(
                f"""
                <div style="display:flex;flex-wrap:wrap;gap:6px;align-items:center;
                            background:rgba(255,255,255,0.05);padding:6px 8px;border-radius:8px;">
                    {legend_items}
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.markdown(
                """
Chaque point est une transaction DVF sur **2020–2024** (selon ta sélection).  
La couleur va du **bleu** (les moins chers de la sélection) au **bordeaux** (les plus chers).

**À observer**
- La **couronne périphérique** concentre davantage de bleus/verts (prix plus bas).
- Le **centre et l’ouest** (6e, 7e, 8e, 16e) tirent vers l’orange/bordeaux (prix élevés).
- En changeant la **période**, vois si la dispersion se **renforce** ou se **resserre** après 2021.

> La carte sert de **contexte géographique** au reste du tableau : zones de **cherté** et **répartition** des ventes.
"""
            )
    elif pdk is None:
        st.info("pydeck non disponible. Installe `pydeck` pour activer la carte.")

    # -----------------------
    # 6) Échantillon de la sélection
    # -----------------------
    st.subheader("6) Échantillon de la sélection")
    with st.expander("Voir un échantillon (50 premières lignes)"):
        st.dataframe(df.head(50), width="stretch")
