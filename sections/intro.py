import streamlit as st

def render():
    st.header("🎬 Introduction")
    st.subheader("Paris, un marché en mutation (2020–2024)")
    st.markdown(
        """
**Question directrice :** *Comment le marché immobilier parisien a-t-il évolué depuis la crise du Covid ?*

**Périmètre**
- Zone : Département 75 (Paris)
- Période : 2020 → 2024
- Source : **Demandes de valeurs foncières (DVF) géolocalisées – data.gouv.fr**
- Statut : chargement brut (prochaine étape : préparation + explorations)

**Navigation**
- Cette section présente le contexte.
- L’onglet **Overview** accueillera les premiers KPIs et visuels.
"""
    )
