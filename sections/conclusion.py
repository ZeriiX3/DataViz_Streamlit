# sections/conclusion.py
import streamlit as st

def render(app_state):
    st.subheader("Conclusions et perspectives")

    st.markdown(
        """
        ### 💡 Synthèse

        - Entre **2020 et 2024**, le prix médian au m² à Paris est passé de **~11 000 € à ~9 800 €**.  
        - Les **volumes de transactions** ont reculé d’environ **−20 %**, surtout après 2022.  
        - Les **écarts géographiques** se sont creusés : l’Ouest reste très haut, l’Est plus abordable.  

        ---

        ### 🔍 Analyse

        Ce recul mesuré s’explique par :
        - la **hausse des taux d’intérêt**,  
        - la **baisse du pouvoir d’achat immobilier**,  
        - et une **sélectivité accrue** (qualité, localisation, DPE).  

        Paris connaît donc une **normalisation**, pas une crise.

        ---

        ### 🚀 Perspectives

        - **Court terme (2025)** : stabilisation si les taux se détendent.  
        - **Moyen terme** : revalorisation des biens rénovés ou à fort rendement énergétique.  
        - **Long terme** : poursuite du rééquilibrage entre Est et Ouest.

        ---

        ### ⚙️ Données et limites

        - Données : **DVF géolocalisées (data.gouv.fr, 2020–2024)**.  
        - Les transactions sans surface ou valeur foncière ont été **exclues** (pas imputées).  
        - Les chiffres présentés sont **médianes**, donc robustes aux valeurs extrêmes.  

        ---

        📘 *Projet EFREI — Data Storytelling 2025*  
        *Auteur : <PRIVATE_PERSON> — Source : data.gouv.fr — Licence Etalab*
        """
    )
