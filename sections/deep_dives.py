# sections/deep_dives.py
# comparisons, distributions, drilldowns — version optimisée (pas de lag)

import streamlit as st
import pandas as pd
import numpy as np
import altair as alt


# ---------- Utils ----------
def _periodize(df: pd.DataFrame, p1: tuple[int, int], p2: tuple[int, int]) -> pd.DataFrame:
    """Ajoute 'periode2' ∈ {'P1','P2', <NA>} selon l'année, sans dtype mixing."""
    d = df.copy()
    d["annee"] = pd.to_numeric(d.get("annee"), errors="coerce").astype("Int64")
    y1a, y1b = p1
    y2a, y2b = p2
    periode = pd.Series(pd.NA, index=d.index, dtype="string")
    periode[(d["annee"] >= y1a) & (d["annee"] <= y1b)] = "P1"
    periode[(d["annee"] >= y2a) & (d["annee"] <= y2b)] = "P2"
    d["periode2"] = periode
    return d


def _needs(cols: set[str], df: pd.DataFrame) -> bool:
    miss = cols - set(df.columns)
    if miss:
        st.info("Colonnes manquantes : " + ", ".join(sorted(miss)))
        return False
    return True


# ---------- Page ----------
def render(df: pd.DataFrame):
    st.header("🧭 Deep Dives")
    st.caption(
        "Comparaisons **P1 vs P2** pour expliquer le basculement post-Covid : variations par arrondissement, "
        "distributions de prix/m² et mix (surfaces, pièces). Version optimisée pour rester fluide."
    )

    # Sélecteurs de périodes
    years = df["annee"].dropna().astype(int)
    if years.empty:
        st.warning("Aucune année disponible dans la sélection.")
        return
    y_min, y_max = int(years.min()), int(years.max())
    c1, c2 = st.columns([1, 1])
    with c1:
        p1 = st.slider("Période 1 (P1)", y_min, y_max, (max(y_min, 2020), min(y_max, 2021)), step=1)
    with c2:
        p2 = st.slider("Période 2 (P2)", y_min, y_max, (max(y_min, 2022), min(y_max, 2024)), step=1)

    d2 = _periodize(df, p1, p2).dropna(subset=["periode2"]).copy()
    if d2.empty:
        st.warning("Aucune donnée dans ces fenêtres P1/P2. Ajuste les curseurs.")
        return

    # Dtypes compacts utiles
    if "arrondissement" in d2.columns:
        d2["arrondissement"] = d2["arrondissement"].astype("Int64")
    if "type_local" in d2.columns:
        d2["type_local"] = d2["type_local"].astype("category")

    # ================= 1) Dumbbell par arrondissement =================
    st.subheader("1) Arrondissements — Médiane €/m² (P1 vs P2)")
    st.caption("Alt text : pour chaque arrondissement, une ligne relie la médiane P1 à la médiane P2 ; sa longueur = variation.")

    if _needs({"arrondissement", "prix_m2"}, d2) and not d2["arrondissement"].isna().all():
        grp = (
            d2.dropna(subset=["arrondissement", "prix_m2"])
              .groupby(["arrondissement", "periode2"], observed=True, as_index=False)
              .agg(med_prix=("prix_m2", "median"))
        )
        piv = grp.pivot(index="arrondissement", columns="periode2", values="med_prix").reset_index()
        piv = piv.loc[piv["P1"].notna() & piv["P2"].notna()].copy()
        if not piv.empty:
            piv["delta"] = piv["P2"] - piv["P1"]
            max_n = min(20, len(piv))
            topn = st.slider("Top N par |variation|", 8, max_n, min(15, max_n), step=1)
            piv_top = piv.reindex(piv["delta"].abs().sort_values(ascending=False).head(topn).index)
            piv_top = piv_top.sort_values("P2")

            base = alt.Chart(piv_top).encode(y=alt.Y("arrondissement:O", title="Arr.", sort=None))
            lines = base.mark_rule().encode(
                x=alt.X("P1:Q", title="€/m² (médiane)"),
                x2="P2:Q",
                color=alt.condition("datum.delta>0", alt.value("#ef4444"), alt.value("#22c55e")),
                tooltip=[
                    alt.Tooltip("arrondissement:O", title="Arr."),
                    alt.Tooltip("P1:Q", format=",.0f", title="P1 €/m²"),
                    alt.Tooltip("P2:Q", format=",.0f", title="P2 €/m²"),
                    alt.Tooltip("delta:Q", format=",.0f", title="Δ (P2-P1)"),
                ],
            )
            p1_pts = base.mark_point(filled=True, size=60, color="#60a5fa").encode(x="P1:Q")
            p2_pts = base.mark_point(filled=True, size=60, color="#fb7185").encode(x="P2:Q")
            st.altair_chart((lines + p1_pts + p2_pts).properties(height=28 * len(piv_top), title="Dumbbell P1 ↔ P2"),
                            use_container_width=True)

            st.markdown(
                f"""
**Lecture / Storytelling.**  
- **Rouge** = P2 > P1 (médiane en hausse), **Vert** = P2 < P1 (repli).  
- La **longueur** de la ligne = **amplitude** de la variation.  
- Compare **P1 {p1[0]}–{p1[1]}** vs **P2 {p2[0]}–{p2[1]}** : tu vois **où** ça descend/monte le plus.  
- À croiser avec les **volumes** (Overview) pour savoir si ces variations se font en **marché liquide** ou **faible**.
"""
            )
    else:
        st.info("Colonnes nécessaires absentes pour ce visuel.")

    st.divider()

    # ================= 2) Distribution prix/m² (pré-agrégée pandas) =================
    st.subheader("2) Distribution du prix au m² — P1 vs P2")
    if _needs({"prix_m2"}, d2):
        d_price = d2.dropna(subset=["prix_m2", "periode2"]).copy()

        # Fenêtre d'affichage robuste
        lo, hi = d_price["prix_m2"].quantile([0.01, 0.99]).tolist()
        d_price = d_price[(d_price["prix_m2"] >= lo) & (d_price["prix_m2"] <= hi)]

        # Binning côté pandas (rapide)
        nbins = 40
        edges = np.linspace(lo, hi, nbins + 1)
        d_price["bin"] = pd.cut(d_price["prix_m2"], bins=edges, include_lowest=True)
        # Comptes & normalisation par période
        g = d_price.groupby(["periode2", "bin"], observed=True, as_index=False).size().rename(columns={"size": "n"})
        g["part"] = g.groupby("periode2")["n"].transform(lambda x: x / x.sum())
        # Ordre lisible des bacs
        bin_order = [str(b) for b in g["bin"].cat.categories]
        g["bin_str"] = g["bin"].astype(str)

        chart = (
            alt.Chart(g.dropna(subset=["bin_str"]))
            .mark_bar(opacity=0.8)
            .encode(
                x=alt.X("bin_str:N", title="€/m² (classes)", sort=bin_order),
                y=alt.Y("part:Q", title="Part (%)", axis=alt.Axis(format="%")),
                color=alt.Color("periode2:N", title="Période"),
                tooltip=[alt.Tooltip("periode2:N"), alt.Tooltip("bin_str:N", title="Classe"), alt.Tooltip("part:Q", format=".1%")],
            )
            .properties(title="Histogramme normalisé du prix/m²")
        )
        st.altair_chart(chart, use_container_width=True)

        # Boxplots légers
        box = (
            alt.Chart(d_price)
            .mark_boxplot()
            .encode(
                x=alt.X("periode2:N", title="Période"),
                y=alt.Y("prix_m2:Q", title="€/m²"),
                color=alt.Color("periode2:N", legend=None),
            )
            .properties(title="Boxplots du prix/m²")
        )
        st.altair_chart(box, use_container_width=True)

        st.markdown(
            """
**Lecture / Storytelling.**  
- Les **barres** comparent la **répartition** des transactions par tranches de prix : si P2 se déplace vers la gauche → **recentrage**.  
- Les **boxplots** comparent **médianes** et **quartiles** : P2 plus bas et plus serré = **refroidissement** du marché.
"""
        )

    st.divider()

    # ================= 3) Mix : surfaces & pièces =================
    st.subheader("3) Mix — Surfaces et pièces (parts par classe)")

    # Surfaces
    if _needs({"surface_reelle_bati"}, d2):
        d_s = d2.dropna(subset=["surface_reelle_bati", "periode2"]).copy()
        d_s["bin"] = pd.cut(
            d_s["surface_reelle_bati"],
            bins=[0, 25, 40, 60, 80, 120, 10000],
            labels=["<25", "25–40", "40–60", "60–80", "80–120", "120+"],
            right=False,
        )
        g_s = d_s.groupby(["periode2", "bin"], observed=True, as_index=False).size().rename(columns={"size": "n"})
        g_s["part"] = g_s.groupby("periode2")["n"].transform(lambda x: x / x.sum())

        chart_s = (
            alt.Chart(g_s.dropna(subset=["bin"]))
            .mark_bar()
            .encode(
                x=alt.X("bin:N", title="Classe surface (m²)"),
                y=alt.Y("part:Q", title="Part (%)", axis=alt.Axis(format="%")),
                color=alt.Color("periode2:N", title="Période"),
                tooltip=["periode2", "bin", alt.Tooltip("part:Q", format=".1%")],
            )
            .properties(title="Répartition des surfaces")
        )
        st.altair_chart(chart_s, use_container_width=True)

    # Pièces
    if _needs({"nombre_pieces_principales"}, d2):
        d_p = d2.dropna(subset=["nombre_pieces_principales", "periode2"]).copy()
        d_p["nbp"] = pd.to_numeric(d_p["nombre_pieces_principales"], errors="coerce").round().astype("Int64")
        d_p["classe"] = pd.cut(d_p["nbp"], bins=[0, 1, 2, 3, 4, 100], labels=["T1", "T2", "T3", "T4", "T5+"], include_lowest=True)
        g_p = d_p.groupby(["periode2", "classe"], observed=True, as_index=False).size().rename(columns={"size": "n"})
        g_p["part"] = g_p.groupby("periode2")["n"].transform(lambda x: x / x.sum())

        chart_p = (
            alt.Chart(g_p.dropna(subset=["classe"]))
            .mark_bar()
            .encode(
                x=alt.X("classe:N", title="Classe pièces"),
                y=alt.Y("part:Q", title="Part (%)", axis=alt.Axis(format="%")),
                color=alt.Color("periode2:N", title="Période"),
                tooltip=["periode2", "classe", alt.Tooltip("part:Q", format=".1%")],
            )
            .properties(title="Répartition du nombre de pièces")
        )
        st.altair_chart(chart_p, use_container_width=True)

    st.markdown(
        """
**Lecture / Storytelling.**  
- Si la part des **<40 m²** ou des **T1–T2** **augmente** en P2, on observe un **arbitrage d’espace** (contraintes de budget).  
- Si les **T3+** progressent, la sélection glisse vers des gabarits plus grands (familles/haut de gamme).
"""
    )

    st.divider()

    # ================= 4) Variations synthétiques =================
    st.subheader("4) Variations synthétiques — médiane, volumes, part ≤ 40 m²")

    p_med = (
        d2.groupby("periode2", observed=True, as_index=False)
        .agg(prix_m2_median=("prix_m2", "median"), volume=("prix_m2", "size"))
    )

    if "classe_surface_m2" in d2.columns:
        small_mask = d2["classe_surface_m2"].astype(str).isin(["<25", "25–40"])
    else:
        small_mask = d2["surface_reelle_bati"].le(40) if "surface_reelle_bati" in d2.columns else pd.Series(False, index=d2.index)
    part_small = d2.assign(is_small=small_mask).groupby("periode2", as_index=False, observed=True)["is_small"].mean()
    part_small = part_small.rename(columns={"is_small": "part_small"})

    tab = p_med.merge(part_small, on="periode2", how="left")
    if {"P1", "P2"}.issubset(set(tab["periode2"])):
        row = tab.set_index("periode2").loc[["P1", "P2"]]

        def fmt_pct(x): return f"{x*100:,.1f} %".replace(",", " ")
        def fmt_eur(x): return f"{x:,.0f}".replace(",", " ")

        cols = st.columns(3)
        with cols[0]:
            st.metric("Prix médian (€/m²)", fmt_eur(row.loc["P2", "prix_m2_median"]),
                      delta=fmt_eur(row.loc["P2", "prix_m2_median"] - row.loc["P1", "prix_m2_median"]))
        with cols[1]:
            st.metric("Transactions (#)", int(row.loc["P2,","volume"]) if False else int(row.loc["P2", "volume"]),
                      delta=int(row.loc["P2", "volume"] - row.loc["P1", "volume"]))
        with cols[2]:
            st.metric("Part ≤ 40 m²", fmt_pct(row.loc["P2", "part_small"]),
                      delta=fmt_pct(row.loc["P2", "part_small"] - row.loc["P1", "part_small"]))

        st.markdown(
            f"""
**Lecture / Storytelling.**  
- **Prix médian** : confirme l’**inflection** post-2021 si P2 < P1.  
- **Transactions** : degré de **liquidité** (renormalisation ou creux).  
- **Part ≤ 40 m²** : signal d’**accessibilité** et d’**arbitrage**.  
Croise ces deltas avec le **dumbbell** pour voir **où** s’opère le changement.
"""
        )
    else:
        st.info("Impossible de calculer les deltas si P1 ou P2 est vide.")
