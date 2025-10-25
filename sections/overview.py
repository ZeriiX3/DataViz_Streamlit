# sections/overview.py
import streamlit as st
import pandas as pd
import numpy as np
import altair as alt


def _altair(chart, title: str | None = None):
    if title:
        chart = chart.properties(title=title)
    try:
        st.altair_chart(chart, width="stretch")
    except TypeError:
        st.altair_chart(chart, use_container_width=True)

def _ensure_period_index(df: pd.DataFrame) -> pd.DataFrame:
    """Ajoute une colonne datetime trimestrielle tri_date à partir de 'trimestre'."""
    if "trimestre" not in df.columns:
        return df.assign(tri_date=pd.NaT)
    tri = pd.PeriodIndex(df["trimestre"].astype(str), freq="Q")
    return df.assign(tri_date=tri.asfreq("Q").to_timestamp())

def _fmt_nb(x, unit=""):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "—"
    if unit == "€":
        return f"{x:,.0f} €".replace(",", " ")
    if unit == "%":
        return f"{x:.1f} %"
    return f"{x:,.0f}".replace(",", " ")

def _kpi(value, label, fmt=None, help_text=None):
    """Affiche un KPI robuste aux NaN avec un format optionnel."""
    if fmt is not None and value is not None and not (isinstance(value, float) and np.isnan(value)):
        try:
            value = fmt.format(value)
        except Exception:
            pass
    st.metric(label, value if value is not None else "—", help=help_text)

def render(df: pd.DataFrame):
    st.header("Overview")

    # =======================
    # 0) KPIs
    # =======================
    st.subheader("Que dit la photo de la sélection ?")

    small_mask = (
        df["classe_surface_m2"].astype(str).isin(["<25", "25-40"])
        if "classe_surface_m2" in df.columns
        else pd.Series(False, index=df.index)
    )
    prix_m2_med = float(np.nanmedian(df["prix_m2"])) if "prix_m2" in df.columns else np.nan
    vol = int(len(df))
    part_small = float(100 * small_mask.mean()) if len(df) else np.nan
    surf_med = float(np.nanmedian(df["surface_reelle_bati"])) if "surface_reelle_bati" in df.columns else np.nan
    pieces_med = float(np.nanmedian(df["nombre_pieces_principales"])) if "nombre_pieces_principales" in df.columns else np.nan

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        _kpi(prix_m2_med, "Prix médian (€/m²)", fmt="{:,.0f} €".replace(",", " "))
    with c2:
        _kpi(vol, "Transactions (#)")
    with c3:
        _kpi(part_small, "Part ≤ 40 m²", fmt="{:.1f} %")
    with c4:
        _kpi(surf_med, "Surface médiane (m²)", fmt="{:.0f}")
    with c5:
        _kpi(pieces_med, "Pièces médianes", fmt="{:.0f}")

    # =======================
    # 1) Trajectoire du prix médian (trimestriel)
    # =======================
    st.subheader("1) Les prix ont-ils changé de régime depuis 2021 ?")

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
            alt.Chart(g_prix)
            .mark_line(point=True)
            .encode(
                x=alt.X("tri_date:T", title="Trimestre"),
                y=alt.Y("prix_m2_median:Q", title="Prix médian (€/m²)"),
                tooltip=["trimestre", alt.Tooltip("prix_m2_median:Q", format=",.0f", title="€/m²")],
            )
        )
        _altair(chart, "Prix médian au m² — trajectoire trimestrielle")

        # constats chiffrés
        def _period_median(d: pd.DataFrame, years: tuple[int, int]):
            a, b = years
            sub = d[(d["tri_date"].dt.year >= a) & (d["tri_date"].dt.year <= b)]
            return float(sub["prix_m2_median"].median()) if len(sub) else np.nan

        p1 = _period_median(g_prix, (2020, 2021))
        p2 = _period_median(g_prix, (2023, 2024))
        delta_pct = (p2 - p1) / p1 * 100 if (p1 and not np.isnan(p1) and p1 != 0 and not np.isnan(p2)) else np.nan

        if len(g_prix):
            idx_max = int(g_prix["prix_m2_median"].idxmax())
            peak_val = float(g_prix.loc[idx_max, "prix_m2_median"])
            peak_q = g_prix.loc[idx_max, "trimestre"]
            last_val = float(g_prix["prix_m2_median"].iloc[-1])
            drawdown = (last_val - peak_val) / peak_val * 100 if peak_val else np.nan
        else:
            peak_q = "—"; peak_val = np.nan; last_val = np.nan; drawdown = np.nan

        st.markdown(
            f"""
De **{_fmt_nb(p1, unit='€')}** en **2020-2021** à **{_fmt_nb(p2, unit='€')}** en **2023-2024**
(**{_fmt_nb(delta_pct, unit='%')}**). Le **pic** apparaît vers **{peak_q}** (≈ {_fmt_nb(peak_val, unit='€')})
et le niveau récent est {_fmt_nb(last_val, unit='€')} (**{_fmt_nb(drawdown, unit='%')}** depuis le pic)."""
        )
    else:
        st.info("Colonnes nécessaires absentes pour la trajectoire (prix_m2, trimestre).")

    # =======================
    # 2) Volumes de transactions (trimestriel)
    # =======================
    st.subheader("2) La liquidité s'est-elle normalisée ?")

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
            alt.Chart(g_vol)
            .mark_bar()
            .encode(
                x=alt.X("tri_date:T", title="Trimestre"),
                y=alt.Y("volume:Q", title="Transactions (#)"),
                tooltip=["trimestre", "volume"],
            )
        )
        _altair(chart, "Transactions par trimestre (liquidité de marché)")

        def _period_avg(d: pd.DataFrame, years: tuple[int, int]):
            a, b = years
            sub = d[(d["tri_date"].dt.year >= a) & (d["tri_date"].dt.year <= b)]
            return float(sub["volume"].mean()) if len(sub) else np.nan

        v1 = _period_avg(g_vol, (2020, 2021))
        v2 = _period_avg(g_vol, (2023, 2024))
        v_delta = (v2 - v1) / v1 * 100 if (v1 and not np.isnan(v1) and v1 != 0 and not np.isnan(v2)) else np.nan

        if len(g_vol) >= 4:
            recent = g_vol["volume"].iloc[-2:].mean()
            prev = g_vol["volume"].iloc[-4:-2].mean()
            mom = (recent - prev) / prev * 100 if prev else np.nan
        else:
            mom = np.nan

        st.markdown(
            f"""
La moyenne trimestrielle passe de **{_fmt_nb(v1)}** (2020–2021) à **{_fmt_nb(v2)}** (2023–2024)
(**{_fmt_nb(v_delta, unit='%')}**). Sur les deux derniers trimestres, la variation par rapport aux deux précédents
est de **{_fmt_nb(mom, unit='%')}**."""
        )
    else:
        st.info("Colonne 'trimestre' absente pour le volume trimestriel.")

    # =======================
    # 3) Part des petites surfaces
    # =======================
    st.subheader("3) La part des petites surfaces (<= 40 m²) progresse-t-elle ?")

    if {"classe_surface_m2", "trimestre"}.issubset(df.columns):
        df_part = _ensure_period_index(df).dropna(subset=["tri_date"]).copy()
        df_part["is_small"] = df_part["classe_surface_m2"].astype(str).isin(["<25", "25-40"])
        g_part = (
            df_part.groupby("trimestre", as_index=False, observed=True)
            .agg(part_small=("is_small", "mean"))
            .assign(tri_date=lambda d: pd.PeriodIndex(d["trimestre"], freq="Q").asfreq("Q").to_timestamp())
            .sort_values("tri_date")
        )
        chart = (
            alt.Chart(g_part)
            .mark_line(point=True)
            .encode(
                x=alt.X("tri_date:T", title="Trimestre"),
                y=alt.Y("part_small:Q", axis=alt.Axis(format="%"), title="Part des petites surfaces"),
                tooltip=["trimestre", alt.Tooltip("part_small:Q", format=".1%")],
            )
        )
        _altair(chart, "Part des petites surfaces (<= 40 m²) — trajectoire trimestrielle")

        def _period_share(d: pd.DataFrame, years: tuple[int, int]):
            a, b = years
            sub = d[(d["tri_date"].dt.year >= a) & (d["tri_date"].dt.year <= b)]
            return float(sub["part_small"].mean()) * 100 if len(sub) else np.nan

        s1 = _period_share(g_part, (2020, 2021))
        s2 = _period_share(g_part, (2023, 2024))
        s_delta = s2 - s1 if (not np.isnan(s1) and not np.isnan(s2)) else np.nan

        st.markdown(
            f"""
La part ≤ 40 m² est **{_fmt_nb(s1, unit='%')}** en **2020–2021** et **{_fmt_nb(s2, unit='%')}** en **2023-2024**
(**{_fmt_nb(s_delta, unit='%')}** d'écart)."""
        )
    else:
        st.info("Colonnes nécessaires absentes pour la part des petites surfaces.")

    # =======================
    # 4) Où sont les zones les plus chères aujourd’hui ?
    # =======================
    st.subheader("4) Où sont les zones les plus chères aujourd'hui ? (médiane €/m²)")

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
            alt.Chart(g_top)
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
        _altair(chart, "Arrondissements les plus chers (médiane sur la sélection)")

        head = g_arr.head(3)
        tail = g_arr.tail(3).sort_values("prix_m2_median")
        spread = (g_arr["prix_m2_median"].max() - g_arr["prix_m2_median"].min()) if len(g_arr) >= 2 else np.nan

        def _triplet(dftrip):
            return ", ".join([f"{int(r.arrondissement)} ({_fmt_nb(float(r.prix_m2_median), unit='€')})" for _, r in dftrip.iterrows()])

        st.markdown(
            f"""
Top actuel : {_triplet(head)}.  
En bas de classement : {_triplet(tail)}.  
Écart observé entre l'arrondissement le plus cher et le moins cher : **{_fmt_nb(float(spread), unit='€')}**."""
        )
    else:
        st.info("Colonnes nécessaires absentes pour le classement par arrondissement.")

    # =======================
    # 5) Tableau d’aperçu (sélection)
    # =======================
    st.subheader("5) Aperçu des données filtrées")
    with st.expander("Afficher 50 lignes"):
        st.dataframe(df.head(50), width="stretch")
