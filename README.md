# Paris, un marché en mutation (2020–2024)

Tableau de bord Streamlit construit sur les **DVF géolocalisées** (Paris - 75) pour analyser le basculement post-Covid.

Par Sébastien XU - EFREI Paris - Promo 2027

Déploiement : https://zeriix3-dataviz-streamlit-app-vypzl2.streamlit.app/

Repo : https://github.com/ZeriiX3/DataViz_Streamlit

## 1) Fonctionnalités

- **Intro** : contexte, carte des transactions.
- **Overview** : KPIs, trajectoires, classement des arrondissements.
- **Deep Dives** : comparaisons **P1 (2020–2021)** vs **P2 (2022–2024)**
  - baisses de médiane par arrondissement,
  - **volume vs niveau** 
  - distributions de prix superposées,
  - tableau détaillé
- **Conclusions** : synthèse, implications et “next steps”.

## 2) Prérequis

- **Python 3.10+** (ok 3.11/3.12/3.13).

## 3) Installation

```bash
# 1) Cloner le dépôt
git clone https://github.com/ZeriiX3/DataViz_Streamlit.git

# 2) Créer un environnement
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# 3) Installer les dépendances
pip install --upgrade pip
pip install -r requirements.txt
```

## 4) Lancer l’application

```bash
streamlit run app.py
```

- L’interface s’ouvre dans le navigateur (par défaut http://localhost:8501).

## 5) Structure du projet

```
.
├── app.py
├── sections/
│   ├── intro.py
│   ├── overview.py
│   ├── deep_dives.py
│   └── conclusions.py
├── utils/
│   ├── io.py         # lecture CSV + cache parquet (.cache)
│   └── prep.py       # nettoyage / features (prix_m2, classes, périodes…)
├── data/
│   └── 75_YYYY.csv   # les fichiers DVF
└── requirements.txt
```

## 6) Performance & cache

- Un **cache parquet** est créé dans `data/.cache/`.
- La **signature** du dossier data est vérifiée : si tu ajoutes/remplaces un CSV, le cache est invalidé automatiquement.
- Pour repartir de zéro, supprime `data/.cache/` ou passe `force_rebuild=True` (cf. `utils/io.py` si besoin).

## 7) Dépannage

- **Carte absente** : `pydeck` non installé → `pip install pydeck` (sinon la carte est simplement désactivée).
- **Lecture parquet** : installe `pyarrow` (`pip install pyarrow`) si tu vois une erreur liée au parquet.
- **Charts Altair** : utilise Altair **v5** (`pip install "altair>=5,<6"`).
- **Aucun point / visuel vide** : les filtres sont peut-être trop restrictifs -> bouton `Réinitialiser les filtres` dans la sidebar.
- **Colonnes manquantes** : vérifie les noms/encodages (le lecteur standardise automatiquement la casse/accents/espaces).

## 8) Licence & source

- Données : **DVF géolocalisées – data.gouv.fr**
- Réutilisation : **Licence Ouverte 2.0 (Etalab)**
- Le tableau de bord n'embarque aucune donnée personnelle.
