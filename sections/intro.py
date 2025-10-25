# sections/intro.py
import streamlit as st
import pandas as pd
import numpy as np

try:
    import pydeck as pdk
except Exception:
    pdk = None


def _map_block(df: pd.DataFrame):
    """Carte pydeck des transactions colorées par quantiles de prix/m² (échantillon perf)."""
    st.subheader("Carte des transactions")

    if pdk is None:
        st.info("pydeck non disponible. Installez `pydeck` pour activer la carte.")
        return

    needed = {"latitude", "longitude", "prix_m2"}
    if not needed.issubset(df.columns):
        st.info("Colonnes nécessaires absentes pour la carte (latitude, longitude, prix_m2).")
        return

    df_geo = df.dropna(subset=["latitude", "longitude", "prix_m2"]).copy()
    df_geo["lat"] = pd.to_numeric(df_geo["latitude"], errors="coerce")
    df_geo["lon"] = pd.to_numeric(df_geo["longitude"], errors="coerce")
    df_geo["prix_m2"] = pd.to_numeric(df_geo["prix_m2"], errors="coerce")
    df_geo = df_geo.dropna(subset=["lat", "lon", "prix_m2"])

    if df_geo.empty:
        st.info("Aucun point géolocalisé dans la sélection actuelle.")
        return

    # Échantillon (perf/visibilité)
    sample_size = 6000
    if len(df_geo) > sample_size:
        df_geo = df_geo.sample(sample_size, random_state=42)

    # Binning quantiles
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
        labels[0]: (33, 158, 188),   # bleu
        labels[1]: (67, 170, 139),   # vert
        labels[2]: (253, 210, 97),   # jaune
        labels[3]: (244, 96, 54),    # orange/rouge
        labels[4]: (157, 0, 57),     # bordeaux
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
        get_radius=10,      
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

    # Légende
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

    st.caption(
        "Alt text : carte des transactions DVF (échantillon ≤ 6000 points) colorées par quantiles de prix au m². "
        "Chaque point = une mutation ; bleu = moins cher, bordeaux = plus cher."
    )

    st.markdown(
        """
**Comment lire la carte**  
- La **couronne périphérique** affiche davantage de points bleus/verts -> niveaux de prix plus **modérés**.  
- Le **centre et l'ouest** (6e, 7e, 8e, 16e) tirent vers l'orange/bordeaux -> **hauts niveaux** de prix.  
- En ajustant la **période** dans la sidebar, tu peux voir si la répartition se **recentre** après 2021.
"""
    )


def render(df: pd.DataFrame):
    # ===== Ton header et ton sous-titre, conservés =====
    st.header("***Comment le marché immobilier parisien a-t-il évolué depuis la crise du Covid ?***")
    st.subheader(
        "Ce tableau de bord raconte le basculement post-Covid : "
        "**prix au m², volumes et mix** par période, arrondissement et typologie."
    )

    st.markdown(
        """
**Contexte & source.**  
La base **DVF géolocalisées** (data.gouv.fr) recense les mutations immobilières enregistrées par l'administration fiscale.  
En suivant **2020-2024** sur Paris (75), on peut objectiver le **changement de régime** post-Covid : niveaux de **prix au m²**,  
**liquidité** (volumes de ventes) et **composition** du marché (mix par surfaces/pièces).


**Trois questions essentielles**
1. **Cycle** - Observe-t-on un **avant/après 2021** et un **refroidissement 2023-2024** ?  
2. **Liquidité** - Les **volumes** se renormalisent-ils ? Où le marché reste-t-il **actif** ?  
3. **Mix** - La part des **petites surfaces (<= 40 m²)** progresse-t-elle ? q

> Les sections suivantes reprennent ces questions dans l'ordre : *Overview* (trajectoires globales) puis *Deep Dives* (comparaisons ciblées).
"""
    )

    # ===== "Périmètre" et "Navigation" =====
    st.markdown(
        """
## Périmètre
- **Zone** : Département **75** (Paris)
- **Période** : **2020 à 2024**
- **Source** : Demandes de valeurs foncières (**DVF**) géolocalisées - data.gouv.fr

## Navigation
- **Intro** — Contexte, question, carte.
- **Overview** — Trajectoire globale 2020-2024 :  
  - **KPI** : *Prix médian au m²*, *Volumes trimestriels*, *Part en dessous de 40 m²*, etc.
- **Deep Dives**:  
  - **Où la baisse est la plus marquée ?**
  - **Mix & typologies** (<=40 m², pièces médianes)  
  - **Distribution des prix** (P1 vs P2)  
  - **Tableau détaillé**
"""
    )

    # ===== Carte =====
    _map_block(df)
