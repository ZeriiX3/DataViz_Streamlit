# sections/deep_dives.py
import streamlit as st
import plotly.express as px

def render(app_state):
    st.subheader("Analyses détaillées : les disparités entre arrondissements")

    tables = app_state["data"]["tables"]
    if "by_arrondissement" not in tables or tables["by_arrondissement"].empty:
        st.warning("Les données par arrondissement ne sont pas disponibles avec les filtres actuels.")
        return

    by_arr = tables["by_arrondissement"].copy()
    year_max = int(by_arr["annee"].max())
    arr_latest = by_arr[by_arr["annee"] == year_max].copy()

    # --- Top & Bottom (dernière année filtrée) ---
    top5 = arr_latest.sort_values("prix_m2_median", ascending=False).head(5)
    bottom5 = arr_latest.sort_values("prix_m2_median", ascending=True).head(5)

    c1, c2 = st.columns(2)
    with c1:
        fig_top = px.bar(
            top5, x="arrondissement", y="prix_m2_median",
            title=f"🏆 Top 5 arrondissements (prix/m²) — {year_max}",
            labels={"arrondissement": "Arr.", "prix_m2_median": "€ / m²"},
            color="prix_m2_median", color_continuous_scale="Blues",
        )
        st.plotly_chart(fig_top, use_container_width=True)
    with c2:
        fig_bot = px.bar(
            bottom5, x="arrondissement", y="prix_m2_median",
            title=f"💸 Bottom 5 arrondissements (prix/m²) — {year_max}",
            labels={"arrondissement": "Arr.", "prix_m2_median": "€ / m²"},
            color="prix_m2_median", color_continuous_scale="Reds",
        )
        st.plotly_chart(fig_bot, use_container_width=True)

    st.markdown("---")
    st.write(f"### Carte des prix au m² ({year_max})")

        # --- Carte des prix au m² (chargement local, pas de réseau) ---
    try:
        import json, os

        # 1) chemin du fichier local
        geo_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "arrondissements-75.geojson"))
        if not os.path.exists(geo_path):
            raise FileNotFoundError(
                "Fichier GeoJSON manquant. Placez 'arrondissements-75.geojson' dans le dossier data/."
            )

        # 2) lecture BOM-safe
        with open(geo_path, "r", encoding="utf-8-sig") as f:
            geojson_paris = json.load(f)

        # 3) harmoniser le format de l'arrondissement côté données
        arr_latest["arrondissement"] = arr_latest["arrondissement"].astype(str).str.zfill(2)

        fig_map = px.choropleth_mapbox(
            arr_latest,
            geojson=geojson_paris,
            locations="arrondissement",
            featureidkey="properties.c_ar",  # clé des arrondissements dans ce GeoJSON
            color="prix_m2_median",
            color_continuous_scale="Blues",
            mapbox_style="carto-positron",
            center={"lat": 48.8566, "lon": 2.3522},
            zoom=9.5,
            opacity=0.8,
            title=f"Prix médian au m² par arrondissement — {year_max}",
        )
        fig_map.update_layout(margin={"r": 0, "t": 40, "l": 0, "b": 0})
        st.plotly_chart(fig_map, use_container_width=True)

    except Exception as e:
        st.warning(f"Carte non disponible : {e}")


    st.markdown(
        """
        📊 **Lecture :** l’Ouest (6ᵉ, 7ᵉ, 8ᵉ) concentre les prix les plus élevés,
        tandis que l’Est/Nord-Est (18ᵉ, 19ᵉ, 20ᵉ) demeure plus abordable.
        """
    )
