# utils/io.py
from pathlib import Path
import pandas as pd
import re
import csv
import json
import time

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

# ---------- caching utils (parquet + signature des CSV) ----------
def _cache_paths(data_dir: Path):
    cache_dir = data_dir / ".cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    parquet_path = cache_dir / "df_raw.parquet"
    meta_path = cache_dir / "df_raw.meta.json"
    return parquet_path, meta_path

def _dir_signature(data_dir: Path, pattern: str = "75_*.csv") -> dict:
    files = sorted(data_dir.glob(pattern))
    sig = {
        "pattern": pattern,
        "files": [
            {
                "name": f.name,
                "size": f.stat().st_size,
                "mtime": int(f.stat().st_mtime),
            }
            for f in files
        ],
        "count": len(files),
        "total_size": sum(f.stat().st_size for f in files),
    }
    return sig

def _same_signature(a: dict, b: dict) -> bool:
    return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)

# ---------- core readers ----------
def _read_one_csv(path: Path) -> pd.DataFrame:
    """
    Lecture robuste DVF avec auto-détection du séparateur et de l'encodage.
    1) Tentative auto (sep=None, engine='python', utf-8-sig)
    2) Fallbacks explicites sur encodages et séparateurs.
    """
    # 1) Auto (IMPORTANT: ne PAS passer low_memory avec engine='python')
    try:
        df = pd.read_csv(
            path,
            sep=None,               # auto-detec (python engine)
            engine="python",
            dtype=str,
            encoding="utf-8-sig",
            quoting=csv.QUOTE_MINIMAL,
        )
    except Exception:
        df = None

    # 2) Si échec ou 1 seule colonne -> fallbacks
    if df is None or df.shape[1] == 1:
        encodings = ["utf-8-sig", "utf-8", "latin1"]
        seps = [";", ",", "\t"]
        read_ok = False
        for enc in encodings:
            for sep in seps:
                try:
                    df_try = pd.read_csv(
                        path,
                        sep=sep,
                        dtype=str,
                        encoding=enc,
                        # ici on peut remettre low_memory pour C engine
                        low_memory=False,
                    )
                    if df_try.shape[1] > 1:
                        df = df_try
                        read_ok = True
                        break
                except Exception:
                    continue
            if read_ok:
                break
        if not read_ok:
            # Dernière chance : relire sans options pour remonter une erreur lisible
            df = pd.read_csv(path)

    # ---------- standardisation colonnes ----------
    df.columns = [_snake(c) for c in df.columns]

    # ---------- dates & année ----------
    if "date_mutation" in df.columns:
        df["date_mutation"] = pd.to_datetime(df["date_mutation"], errors="coerce")
        df["annee"] = df["date_mutation"].dt.year

    # ---------- filtre Paris (si colonne dispo) ----------
    if "code_departement" in df.columns:
        df["code_departement"] = df["code_departement"].astype(str).str.strip()
        df = df[df["code_departement"] == "75"]

    # ---------- coercions numériques usuelles ----------
    for col in ["valeur_fonciere", "surface_reelle_bati", "nombre_pieces_principales", "surface_terrain"]:
        if col in df.columns:
            df[col] = _coerce_numeric(df[col])

    return df

# ---------- public API ----------
def load_data(
    data_dir: str | Path = "data",
    pattern: str = "75_*.csv",
    use_parquet_cache: bool = True,
    force_rebuild: bool = False,
) -> pd.DataFrame:
    """
    Charge tous les CSV DVF Paris (pattern ex: 75_*.csv) depuis `data_dir`,
    concatène et renvoie un df brut standardisé (df_raw).

    Accélération :
      - Si `use_parquet_cache=True`, lit/écrit un cache Parquet (.cache/df_raw.parquet)
        + un fichier méta avec la "signature" des CSV (noms, tailles, mtimes).
      - Si la signature est identique, on lit directement le Parquet.
      - `force_rebuild=True` ignore le cache et reconstruit depuis les CSV.
    """
    data_dir = Path(data_dir)
    parquet_path, meta_path = _cache_paths(data_dir)
    current_sig = _dir_signature(data_dir, pattern=pattern)

    # --- Fast path: lire le cache si signature identique (et pas force)
    if (
        use_parquet_cache
        and not force_rebuild
        and parquet_path.exists()
        and meta_path.exists()
    ):
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                old_meta = json.load(f)
            if _same_signature(old_meta.get("signature", {}), current_sig):
                return pd.read_parquet(parquet_path)
        except Exception:
            pass  # si erreur de lecture cache -> on reconstruit

    # --- Reconstruire depuis les CSV
    files = sorted(data_dir.glob(pattern))
    if not files:
        raise FileNotFoundError(f"Aucun fichier trouvé dans {data_dir} (pattern {pattern}).")

    dfs = [_read_one_csv(p) for p in files]
    df_raw = pd.concat(dfs, ignore_index=True, sort=False)

    # Colonnes clés d'abord si présentes
    preferred = [
        "annee", "date_mutation", "nature_mutation", "valeur_fonciere",
        "type_local", "nombre_pieces_principales", "surface_reelle_bati",
        "adresse_nom_voie", "code_postal", "nom_commune", "longitude", "latitude"
    ]
    cols = [c for c in preferred if c in df_raw.columns] + [c for c in df_raw.columns if c not in preferred]
    df_raw = df_raw[cols]

    # --- Écrire le cache parquet + méta (si activé)
    if use_parquet_cache:
        try:
            df_raw.to_parquet(parquet_path, index=False)  # nécessite pyarrow ou fastparquet
            meta = {
                "created_at": int(time.time()),
                "signature": current_sig,
                "parquet_path": str(parquet_path),
            }
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False, indent=2, sort_keys=True)
        except Exception:
            # Si l'écriture du cache échoue, on continue sans interrompre la lecture
            pass

    return df_raw
