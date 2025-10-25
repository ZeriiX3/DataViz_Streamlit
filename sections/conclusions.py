# sections/conclusions.py
import streamlit as st

def render(df):
    st.header("Conclusion")

    st.markdown(
        """
L'analyse conduite sur les **DVF 2020-2024** du marché parisien met en évidence plusieurs constats robustes.

D'abord, le marché a bien connu un **changement de régime post-Covid**. On observe un palier puis un **repli des médianes**
après 2021, tandis que la **liquidité** (volumes de ventes) se contracte nettement en **2023-2024**. Ce mouvement n'est
pas linéaire : des phases de respiration existent selon les segments et le timing des hausses de taux.

Ensuite, les **écarts territoriaux** restent marqués et **structurels**. Le **gradient intra-Paris** persiste : centre/ouest
plus cher, nord/est plus modéré. Certaines zones résistent, d'autres décrochent davantage ; la lecture doit donc se faire
au **niveau local (arrondissement)** plutôt qu'à travers une moyenne unique.

Par ailleurs, l'évolution tient aussi au **mix de biens**. La hausse de la **part des petites surfaces (<= 40 m²)** dans
certaines sélections pousse mécaniquement la médiane vers le bas **à mix constant** : une médiane qui recule ne traduit
pas forcément une chute des **prix unitaires**, mais parfois un recentrage de la demande vers des biens plus compacts.

Enfin, la **dispersion des prix** évolue : les distributions P1 vs P2 montrent dans plusieurs cas un **décalage vers le bas**
et un **resserrement** (moins d'extrêmes), sans uniformité selon les types de biens. Cela confirme que le cycle actuel est
**hétérogène** par zone et par segment.
"""
    )

    st.markdown("---")
    st.subheader("Et maintenant, qu'est-ce qu'on en fait ?")

    st.markdown(
        """
- **Cibler localement:** Adapter la stratégie **par arrondissement** et **par typologie**.
- **Piloter la liquidité:** Prioriser les zones où **volumes** et **niveau de prix** coexistent (meilleure absorption), ajuster là où l'activité reste faible.
- **Segmenter la communication:** Si la part des **petites surfaces** progresse, adresser spécifiquement **primo-accédants** et **investisseurs** (budget, financement, rendement).
- **Mettre en place une veille:** Suivi **trimestriel** sur les zones clés : médiane €/m², **p10-p90** (dispersion), **volumes**, **% ≤ 40 m²**.
"""
    )

    st.markdown("---")
    st.subheader("Limites & prochains pas")

    st.markdown(
        """
- Résultats dépendants des **filtres** (période, types, surfaces, périmètre) et du **nettoyage** appliqué aux DVF.
- À consolider : contrôle des **extrêmes**, vérification **géoloc** sur les arrondissements en bout de classement, extension **2025+** pour confirmer les tendances.
- Extensions utiles : croiser avec **taux / pouvoir d'achat**, **stocks & délais**, signaux **financement** et **offre**.
"""
    )

    st.caption(
        "Synthèse des faits, implications opérationnelles et pistes concrètes pour piloter le marché parisien post-Covid."
    )
