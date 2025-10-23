# utils/io.py
from pathlib import Path
import pandas as pd
import re
import csv
import json
import time
import streamlit as st

# ---------- helpers ----------
def _snake(s: str) -> str:
    s = s.strip()
    s = s.replace("(", " ").replace(")", " ").replace("/", " ")
    s = re.sub(r"[^0-9a-zA-Z]+", "_", s)
    s = re.sub(r"_+", "_", s)
    return s.strip("_").lower()

def _coerce_numeric(series: pd.Series) -> pd.Series:
    s = series.astype(str)
    s = s.str.replace("\u00A0", " ", regex=False)     # NBSP
    s = s.str.replace(" ", "", regex=False)           # sep milliers
    s = s.str.replace(",", ".", regex=False)          # virgule -> point
    return pd.to_numeric(s, errors="coerce")

# ---------- signature dossier (pour invalider les caches) ----------
def dir_signature(data_dir: str | Path, pattern: str = "75_*.csv") -> str:
    """
    Retourne une signature JSON (str) basée sur la liste des fichiers, leur taille et mtime.
    Si un CSV change/ajout/suppression -> la signature change.
    """
    data_dir = Path(data_dir)
    files = sorted(data_dir.glob(pattern))
    payload = {
        "pattern": pattern,
        "files": [
            {"name": f.name, "size": f.stat().st_size, "mtime": int(f.stat().st_mtime)}
            for f in files
        ],
        "count": len(files),
        "total_size": sum((f.stat().st_size for f in files), 0),
    }
    return json.dumps(payload, sort_keys=True)

# ---------- parquet cache local ----------
def _cache_paths(data_dir: Path):
    cache_dir = data_dir / ".cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / "df_raw.parquet", cache_dir / "df_raw.meta.json"

# ---------- core readers ----------
def _read_one_csv(path: Path) -> pd.DataFrame:
    """Lecture robuste DVF avec auto-détection, avec fallbacks."""
    try:
        df = pd.read_csv(
            path, sep=None, engine="python", dtype=str, encoding="utf-8-sig",
            quoting=csv.QUOTE_MINIMAL,
        )
    except Exception:
        df = None

    if df is None or df.shape[1] == 1:
        for enc in ["utf-8-sig", "utf-8", "latin1"]:
            for sep in [";", ",", "\t"]:
                try:
                    df_try = pd.read_csv(path, sep=sep, dtype=str, encoding=enc, low_memory=False)
                    if df_try.shape[1] > 1:
                        df = df_try
                        break
                except Exception:
                    continue
            if df is not None and df.shape[1] > 1:
                break
        if df is None:
            df = pd.read_csv(path)

    df.columns = [_snake(c) for c in df.columns]

    if "date_mutation" in df.columns:
        df["date_mutation"] = pd.to_datetime(df["date_mutation"], errors="coerce")
        df["annee"] = df["date_mutation"].dt.year

    if "code_departement" in df.columns:
        df["code_departement"] = df["code_departement"].astype(str).str.strip()
        df = df[df["code_departement"] == "75"]

    for col in ["valeur_fonciere", "surface_reelle_bati", "nombre_pieces_principales", "surface_terrain"]:
        if col in df.columns:
            df[col] = _coerce_numeric(df[col])

    return df

# ---------- build df_raw (avec contrôle de signature parquet) ----------
def load_data(
    data_dir: str | Path = "data",
    pattern: str = "75_*.csv",
    use_parquet_cache: bool = True,
    force_rebuild: bool = False,
) -> pd.DataFrame:
    """
    Charge tous les CSV DVF (pattern) depuis `data_dir` et renvoie df_raw standardisé.
    Si `use_parquet_cache=True`, on lit le parquet **uniquement** si la signature .meta.json
    correspond à la signature courante du dossier. Sinon on reconstruit depuis CSV.
    """
    data_dir = Path(data_dir)
    parquet_path, meta_path = _cache_paths(data_dir)
    current_sig = json.loads(dir_signature(data_dir, pattern))

    # Lecture rapide via parquet si signature OK et pas force_rebuild
    if use_parquet_cache and not force_rebuild and parquet_path.exists() and meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            cached_sig = meta.get("signature", None)
            if cached_sig == current_sig:
                return pd.read_parquet(parquet_path)
            # sinon: signature mismatch -> on reconstruit plus bas
        except Exception:
            # meta illisible -> on reconstruit
            pass

    # Reconstruire depuis les CSV (signature mismatch, force, ou pas de cache)
    files = sorted(data_dir.glob(pattern))
    if not files:
        raise FileNotFoundError(f"Aucun fichier trouvé dans {data_dir} (pattern {pattern}).")

    dfs = [_read_one_csv(p) for p in files]
    df_raw = pd.concat(dfs, ignore_index=True, sort=False)

    # Colonnes clés d'abord si présentes
    preferred = [
        "annee", "date_mutation", "nature_mutation", "valeur_fonciere",
        "type_local", "nombre_pieces_principales", "surface_reelle_bati",
        "adresse_nom_voie", "code_postal", "nom_commune", "longitude", "latitude",
    ]
    cols = [c for c in preferred if c in df_raw.columns] + [c for c in df_raw.columns if c not in preferred]
    df_raw = df_raw[cols]

    # Écrit le cache parquet + meta **avec la signature courante**
    if use_parquet_cache:
        try:
            df_raw.to_parquet(parquet_path, index=False)
            meta = {
                "created_at": int(time.time()),
                "signature": current_sig,  # on stocke l'objet (dict)
            }
            meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            # si l'écriture du cache échoue, on n'empêche pas l'app de tourner
            pass

    return df_raw

# ---------- wrapper caché Streamlit ----------
@st.cache_data(show_spinner=False)
def load_data_cached(
    signature: str,
    data_dir: str = "data",
    pattern: str = "75_*.csv",
    use_parquet_cache: bool = True,
    force_rebuild: bool = False,
) -> pd.DataFrame:
    """
    Version cachée de load_data().
    Le paramètre 'signature' (cf. dir_signature) force l'invalidation du cache Streamlit
    si les CSV changent.
    """
    return load_data(data_dir=data_dir, pattern=pattern,
                     use_parquet_cache=use_parquet_cache, force_rebuild=force_rebuild)
