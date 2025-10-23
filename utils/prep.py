# utils/prep.py
# cleaning, normalization, feature engineering -> df_clean

from __future__ import annotations
import json
from pathlib import Path
import pandas as pd
import streamlit as st

# ---------- helpers ----------
def _coerce_numeric(s: pd.Series) -> pd.Series:
    s = s.astype(str).str.replace("\u00A0", " ", regex=False)
    s = s.str.replace(" ", "", regex=False)
    s = s.str.replace(",", ".", regex=False)
    return pd.to_numeric(s, errors="coerce")

# ---------- pipeline principal ----------
def make_df_clean(
    df_raw: pd.DataFrame,
    *,
    save_parquet: bool = True,
    cache_dir: str | Path = "data/.cache",
) -> pd.DataFrame:
    df = df_raw.copy()

    for col in ["valeur_fonciere", "surface_reelle_bati", "nombre_pieces_principales"]:
        if col in df.columns:
            df[col] = _coerce_numeric(df[col])

    # Dédup
    keys = [k for k in ["id_mutation", "numero_disposition"] if k in df.columns]
    if keys:
        df = df.sort_values("date_mutation", na_position="last").drop_duplicates(subset=keys, keep="first")
    else:
        df = df.drop_duplicates()

    # Périmètre principal
    if "nature_mutation" in df.columns:
        df = df[df["nature_mutation"].astype(str).str.strip().str.lower() == "vente"]
    if "type_local" in df.columns:
        df = df[df["type_local"].isin(["Appartement", "Maison"])]

    needed = [c for c in ["valeur_fonciere", "surface_reelle_bati", "date_mutation"] if c in df.columns]
    if needed:
        df = df.dropna(subset=needed)

    # Arrondissements
    if "code_postal" in df.columns:
        df["code_postal"] = df["code_postal"].astype(str).str.extract(r"(\d{5})")[0]
        df = df[df["code_postal"].str.startswith("75", na=False)]
        df["arrondissement"] = df["code_postal"].str[-2:].astype("Int16")

    # Prix/m²
    if {"valeur_fonciere", "surface_reelle_bati"}.issubset(df.columns):
        df["prix_m2"] = df["valeur_fonciere"] / df["surface_reelle_bati"]

    # Garde-fous
    if "surface_reelle_bati" in df.columns:
        df = df[df["surface_reelle_bati"] >= 9]
        s_q = df["surface_reelle_bati"].quantile(0.999)
        if pd.notna(s_q):
            df = df[df["surface_reelle_bati"] <= s_q]

    if "prix_m2" in df.columns:
        ql = df["prix_m2"].quantile(0.001)
        qh = df["prix_m2"].quantile(0.999)
        MIN_PLAUSIBLE, MAX_PLAUSIBLE = 1000.0, 50000.0
        low = float(max(MIN_PLAUSIBLE, ql)) if pd.notna(ql) else MIN_PLAUSIBLE
        high = float(min(MAX_PLAUSIBLE, qh)) if pd.notna(qh) else MAX_PLAUSIBLE
        df = df[(df["prix_m2"] >= low) & (df["prix_m2"] <= high)]

    # Périodes / classes
    if "date_mutation" in df.columns:
        df["annee"] = df["date_mutation"].dt.year.astype("Int16")
        df["trimestre"] = df["date_mutation"].dt.to_period("Q").astype(str).astype("category")

    if "nombre_pieces_principales" in df.columns:
        df["nombre_pieces_principales"] = df["nombre_pieces_principales"].round().astype("Int16")
        df["classe_pieces"] = pd.cut(
            df["nombre_pieces_principales"],
            bins=[0,1,2,3,4,100],
            labels=["T1","T2","T3","T4","T5+"],
            include_lowest=True, right=True
        ).astype("category")

    if "surface_reelle_bati" in df.columns:
        df["classe_surface_m2"] = pd.cut(
            df["surface_reelle_bati"],
            bins=[0,25,40,60,80,120,10000],
            labels=["<25","25–40","40–60","60–80","80–120","120+"],
            include_lowest=True, right=False
        ).astype("category")

    for col in ["type_local"]:
        if col in df.columns:
            df[col] = df[col].astype("category")

    final_cols = [c for c in [
        "id_mutation",
        "date_mutation","annee","trimestre",
        "nature_mutation","type_local",
        "valeur_fonciere","surface_reelle_bati","prix_m2",
        "nombre_pieces_principales","classe_pieces","classe_surface_m2",
        "code_postal","arrondissement","nom_commune",
        "adresse_nom_voie","longitude","latitude",
    ] if c in df.columns]

    df_clean = df[final_cols].sort_values("date_mutation", na_position="last").reset_index(drop=True)

    # Parquet optionnel
    if save_parquet:
        cache_dir = Path(cache_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)
        try:
            df_clean.to_parquet(cache_dir / "df_clean.parquet", index=False)
            (cache_dir / "df_clean.meta.json").write_text(
                json.dumps({"rows": int(len(df_clean)), "cols": int(df_clean.shape[1])}, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass

    return df_clean

# ---------- wrapper caché Streamlit ----------
@st.cache_data(show_spinner=False)
def make_df_clean_cached(
    df_raw: pd.DataFrame,
    save_parquet: bool = True,
    cache_dir: str | Path = "data/.cache",
) -> pd.DataFrame:
    """Version cachée de make_df_clean()."""
    return make_df_clean(df_raw, save_parquet=save_parquet, cache_dir=cache_dir)
