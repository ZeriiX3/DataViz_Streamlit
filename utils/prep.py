# utils/prep.py
# cleaning, normalization, feature engineering -> df_clean

from __future__ import annotations
import json
from pathlib import Path
import pandas as pd


# ---------- helpers ----------
def _coerce_numeric(s: pd.Series) -> pd.Series:
    """Convertit une série texte (espaces/virgules) en float."""
    s = s.astype(str).str.replace("\u00A0", " ", regex=False)  # NBSP
    s = s.str.replace(" ", "", regex=False)                    # séparateur milliers
    s = s.str.replace(",", ".", regex=False)                   # virgule -> point
    return pd.to_numeric(s, errors="coerce")


# ---------- core pipeline ----------
def make_df_clean(
    df_raw: pd.DataFrame,
    *,
    save_parquet: bool = True,
    cache_dir: str | Path = "data/.cache",
) -> pd.DataFrame:
    """
    Préparation DVF (Paris 75, 2020–2024) -> df_clean, optimisé pour le storytelling.

    Inclus :
      • Déduplication (id_mutation + numero_disposition si dispo).
      • Filtre KPIs : natures = "Vente" et type_local ∈ {Appartement, Maison}.
      • Prix/m² + garde-fous (surfaces <9 m² exclues, coupe douce quantiles + bornes plausibles).
      • Classes (pièces/surfaces), calendrier (année/trimestre).
      • Typage mémoire (category, Int16) pour une app fluide.
      • Sauvegarde parquet optionnelle (df_clean.parquet) pour rechargement rapide.
    """
    df = df_raw.copy()

    # -- coercions minimales
    for col in ["valeur_fonciere", "surface_reelle_bati", "nombre_pieces_principales"]:
        if col in df.columns:
            df[col] = _coerce_numeric(df[col])

    # -- déduplication prudente
    keys = [k for k in ["id_mutation", "numero_disposition"] if k in df.columns]
    if keys:
        df = (
            df.sort_values("date_mutation", na_position="last")
              .drop_duplicates(subset=keys, keep="first")
        )
    else:
        df = df.drop_duplicates()

    # -- filtre périmètre principal pour KPIs
    if "nature_mutation" in df.columns:
        df = df[df["nature_mutation"].astype(str).str.strip().str.lower() == "vente"]
    if "type_local" in df.columns:
        df = df[df["type_local"].isin(["Appartement", "Maison"])]

    # essentiels non nuls
    needed = [c for c in ["valeur_fonciere", "surface_reelle_bati", "date_mutation"] if c in df.columns]
    if needed:
        df = df.dropna(subset=needed)

    # -- CP -> arrondissement
    if "code_postal" in df.columns:
        df["code_postal"] = df["code_postal"].astype(str).str.extract(r"(\d{5})")[0]
        df = df[df["code_postal"].str.startswith("75", na=False)]
        df["arrondissement"] = df["code_postal"].str[-2:].astype("Int16")

    # -- prix/m²
    if {"valeur_fonciere", "surface_reelle_bati"}.issubset(df.columns):
        df["prix_m2"] = df["valeur_fonciere"] / df["surface_reelle_bati"]

    # -- hygiène & garde-fous
    if "surface_reelle_bati" in df.columns:
        df = df[df["surface_reelle_bati"] >= 9]  # surface habitable min
        s_q = df["surface_reelle_bati"].quantile(0.999)
        if pd.notna(s_q):
            df = df[df["surface_reelle_bati"] <= s_q]

    if "prix_m2" in df.columns:
        p_low_q = df["prix_m2"].quantile(0.001)
        p_high_q = df["prix_m2"].quantile(0.999)
        MIN_PLAUSIBLE, MAX_PLAUSIBLE = 1000.0, 50000.0  # ajustables pour Paris
        low = float(max(MIN_PLAUSIBLE, p_low_q)) if pd.notna(p_low_q) else MIN_PLAUSIBLE
        high = float(min(MAX_PLAUSIBLE, p_high_q)) if pd.notna(p_high_q) else MAX_PLAUSIBLE
        df = df[(df["prix_m2"] >= low) & (df["prix_m2"] <= high)]

    # -- périodes
    if "date_mutation" in df.columns:
        df["annee"] = df["date_mutation"].dt.year.astype("Int16")
        df["trimestre"] = df["date_mutation"].dt.to_period("Q").astype(str).astype("category")

    # -- classes analytiques
    if "nombre_pieces_principales" in df.columns:
        df["nombre_pieces_principales"] = df["nombre_pieces_principales"].round().astype("Int16")
        df["classe_pieces"] = pd.cut(
            df["nombre_pieces_principales"],
            bins=[0, 1, 2, 3, 4, 100],
            labels=["T1", "T2", "T3", "T4", "T5+"],
            include_lowest=True,
            right=True,
        ).astype("category")

    if "surface_reelle_bati" in df.columns:
        df["classe_surface_m2"] = pd.cut(
            df["surface_reelle_bati"],
            bins=[0, 25, 40, 60, 80, 120, 10000],
            labels=["<25", "25–40", "40–60", "60–80", "80–120", "120+"],
            include_lowest=True,
            right=False,
        ).astype("category")

    # -- types compacts
    for col in ["type_local"]:
        if col in df.columns:
            df[col] = df[col].astype("category")

    # -- colonnes finales
    final_cols = [c for c in [
        "id_mutation",
        "date_mutation", "annee", "trimestre",
        "nature_mutation", "type_local",
        "valeur_fonciere", "surface_reelle_bati", "prix_m2",
        "nombre_pieces_principales", "classe_pieces", "classe_surface_m2",
        "code_postal", "arrondissement", "nom_commune",
        "adresse_nom_voie", "longitude", "latitude",
    ] if c in df.columns]

    df_clean = (
        df[final_cols]
        .sort_values("date_mutation", na_position="last")
        .reset_index(drop=True)
    )

    # -- sauvegarde parquet (optionnelle)
    if save_parquet:
        cache_dir = Path(cache_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)
        try:
            df_clean.to_parquet(cache_dir / "df_clean.parquet", index=False)
            meta = {
                "rows": int(len(df_clean)),
                "cols": int(df_clean.shape[1]),
                "columns": list(df_clean.columns),
            }
            (cache_dir / "df_clean.meta.json").write_text(
                json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception:
            # si pyarrow/fastparquet absent, on ignore
            pass

    return df_clean

'''
# ---------- petit rapport qualité (optionnel) ----------
def build_quality_report(df_raw: pd.DataFrame, df_clean: pd.DataFrame) -> dict:
    """Résumé lisible pour une section 'Qualité des données'."""
    rep: dict = {}

    rep["rows_raw"] = int(len(df_raw))
    rep["rows_clean"] = int(len(df_clean))
    rep["exclusion_rate_%"] = round(100 * (1 - len(df_clean) / max(len(df_raw), 1)), 2)

    if "nature_mutation" in df_raw.columns:
        rep["nature_top_raw"] = df_raw["nature_mutation"].value_counts(dropna=False).head(10).to_dict()

    for name, d in [("raw", df_raw), ("clean", df_clean)]:
        if "date_mutation" in d.columns:
            rep[f"{name}_date_min"] = str(d["date_mutation"].min())
            rep[f"{name}_date_max"] = str(d["date_mutation"].max())

    return rep
'''