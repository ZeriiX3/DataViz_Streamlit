import streamlit as st

def render():
    st.header("Introduction")
    st.subheader("Ce tableau de bord raconte le basculement post-Covid : **prix au m², volumes et mix** par période, arrondissement et typologie.")
    st.markdown(
        """

***Comment le marché immobilier parisien a-t-il évolué depuis la crise du Covid ?***

## Périmètre
- **Zone** : Département **75** (Paris)
- **Période** : **2020 → 2024**
- **Source** : Demandes de valeurs foncières (**DVF**) géolocalisées — data.gouv.fr
- **Statut** : chargement brut ➜ prochaine étape : **préparation** + **explorations**
- **Nettoyage** : normalisation, **prix/m²**, filtres de cohérence (*surfaces < 9 m² exclues*, coupe douce des extrêmes)

## Navigation
- **Intro** — Contexte, question, méthode & limites.  
- **Overview** — Trajectoire globale 2020–2024 :  
  - **KPI 1** : *Prix médian au m²*  
  - **KPI 2** : *Volumes trimestriels*  
  - **KPI 3** : *Part des petites surfaces (≤ 40 m² / T1–T2)*  
- **Deep Dives**  
  - **Temps** : pentes, ruptures (2021, 2023), dispersion (p10–p90).  
  - **Géographie** : arrondissements, résistances/décrochages, rattrapages.  
  - **Mix & Typologies** : surfaces, nombre de pièces, **effet mix**.  
  - **Distribution des prix** : médiane vs extrêmes, recentrage/polarisation.  
  - **Qualité des données** : périmètre, exclusions, diagnostics (transparence).  
- **Conclusion**

"""
    )
