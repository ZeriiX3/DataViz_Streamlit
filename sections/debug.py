import streamlit as st
import pandas as pd

def render(df_clean: pd.DataFrame):
    st.header("🧪 Debug des données (df_clean)")

    # --- KPIs rapides ---
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Lignes", f"{len(df_clean):,}".replace(",", " "))
    with c2:
        st.metric("Colonnes", f"{df_clean.shape[1]}")
    with c3:
        if "date_mutation" in df_clean.columns:
            min_d = df_clean["date_mutation"].min()
            max_d = df_clean["date_mutation"].max()
            min_txt = min_d.date() if pd.notna(min_d) else "NA"
            max_txt = max_d.date() if pd.notna(max_d) else "NA"
            st.metric("Période", f"{min_txt} → {max_txt}")
        else:
            st.metric("Période", "NA → NA")

    # --- Aperçu & schéma ---
    st.subheader("Aperçu (head)")
    st.dataframe(df_clean.head(20), width="stretch")

    st.subheader("Colonnes & types")
    st.write(list(df_clean.columns))
    st.write(df_clean.dtypes.astype(str))

    # --- Données manquantes ---
    st.subheader("Taux de valeurs manquantes (Top 20)")
    st.dataframe(
        df_clean.isna().mean().sort_values(ascending=False).head(20).mul(100).round(1).to_frame("% NaN"),
        width="stretch"
    )

    # --- Volumes par année ---
    st.subheader("Volumes par année")
    if "annee" in df_clean.columns:
        counts = df_clean["annee"].value_counts().sort_index()
        st.write(counts.to_frame("count"))
        st.bar_chart(counts, width="stretch")
    else:
        st.info("Colonne 'annee' absente.")

    # --- Typologies ---
    st.subheader("Typologies (si dispo)")
    if "type_local" in df_clean.columns:
        st.write(df_clean["type_local"].value_counts(dropna=False).to_frame("count"))
    else:
        st.info("Colonne 'type_local' absente.")

    # --- Sanity checks prix/surfaces ---
    st.subheader("Sanity checks Prix & Surfaces (logements)")
    if {"valeur_fonciere", "surface_reelle_bati"}.issubset(df_clean.columns):
        mask_log = df_clean["type_local"].isin(["Appartement", "Maison"]) if "type_local" in df_clean.columns else slice(None)
        prix_m2 = (df_clean.loc[mask_log, "valeur_fonciere"] / df_clean.loc[mask_log, "surface_reelle_bati"])
        st.markdown("**Résumé `valeur_fonciere` :**")
        st.write(df_clean.loc[mask_log, "valeur_fonciere"].describe(percentiles=[.1,.5,.9,.99]).to_frame().T)
        st.markdown("**Résumé `surface_reelle_bati` :**")
        st.write(df_clean.loc[mask_log, "surface_reelle_bati"].describe(percentiles=[.1,.5,.9,.99]).to_frame().T)
        st.markdown("**Prix/m² (brut) :**")
        st.write(prix_m2.describe(percentiles=[.1,.5,.9,.99]).to_frame().T)
    else:
        st.info("Colonnes nécessaires absentes pour le check prix/m².")

    # =========================
    # 🔎 QUALITÉ & FLAGS
    # =========================
    st.subheader("Qualité & flags (is_vente_std, is_vefa, is_terrain)")

    # 1) Présence des colonnes
    has_flags = {"is_vente_std", "is_vefa", "is_terrain"}.issubset(df_clean.columns)
    if not has_flags:
        st.info("Colonnes de flags absentes (is_vente_std / is_vefa / is_terrain).")
        return

    # 2) Ratios (part dans df_clean)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Part ventes 'standard' (clean)", f"{100*df_clean['is_vente_std'].mean():.2f}%")
    with c2:
        st.metric("Part VEFA (clean)", f"{100*df_clean['is_vefa'].mean():.2f}%")
    with c3:
        st.metric("Part terrains (clean)", f"{100*df_clean['is_terrain'].mean():.2f}%")

    # 3) Nature mutation (si dispo) – top 10
    if "nature_mutation" in df_clean.columns:
        st.markdown("**Top 10 nature_mutation (dans df_clean)**")
        st.dataframe(
            df_clean["nature_mutation"].value_counts(dropna=False).head(10).to_frame("count"),
            width="stretch"
        )

    # 4) Échantillons utiles
    with st.expander("Voir un échantillon des lignes VEFA / terrains / non-vente (si présent)"):
        cols_display = [c for c in [
            "date_mutation","nature_mutation","type_local",
            "valeur_fonciere","surface_reelle_bati","prix_m2",
            "code_postal","arrondissement"
        ] if c in df_clean.columns]

        if df_clean["is_vefa"].any():
            st.markdown("**Exemples VEFA**")
            st.dataframe(df_clean.loc[df_clean["is_vefa"], cols_display].head(20), width="stretch")
        else:
            st.caption("Aucune ligne VEFA détectée dans df_clean.")

        if df_clean["is_terrain"].any():
            st.markdown("**Exemples Terrains**")
            st.dataframe(df_clean.loc[df_clean["is_terrain"], cols_display].head(20), width="stretch")
        else:
            st.caption("Aucune ligne 'terrain' détectée dans df_clean.")

        if (~df_clean["is_vente_std"]).any():
            st.markdown("**Exemples non-vente standard**")
            st.dataframe(df_clean.loc[~df_clean["is_vente_std"], cols_display].head(20), width="stretch")
        else:
            st.caption("Toutes les lignes sont des ventes 'standard' (ou ont été filtrées).")
