from __future__ import annotations

import streamlit as st

from config.settings import BASE_DIR
from database.db import initialize_database

initialize_database()

st.set_page_config(page_title="Auto Candidature", page_icon="📧", layout="wide")

st.title("Auto Candidature")
st.caption("Assistant local de recherche et de candidature pour le marché marocain.")

st.markdown(
    """
    ### Vue d'ensemble
    Cette application aide à :
    - collecter les offres d'emploi disponibles,
    - extraire un profil depuis le CV PDF,
    - générer des emails personnalisés,
    - envoyer les candidatures via Gmail,
    - suivre les candidatures dans SQLite.
    """
)

st.info("L'interface est entièrement en français. La configuration Gmail et Gemini reste locale et sécurisée.")

with st.sidebar:
    st.markdown("## Navigation")
    st.page_link("pages/1_Dashboard.py", label="Tableau de bord")
    st.page_link("pages/2_Job_Finder.py", label="Chercheur d'offres")
    st.page_link("pages/3_Job_Details.py", label="Détails de l'offre")
    st.page_link("pages/4_Email_Generator.py", label="Générateur d'emails")
    st.page_link("pages/5_My_Applications.py", label="Mes candidatures")
    st.page_link("pages/6_Settings.py", label="Paramètres")

st.subheader("Étapes recommandées")
col1, col2, col3 = st.columns(3)
with col1:
    st.write("1. Configurer le profil et les documents")
with col2:
    st.write("2. Chercher et filtrer les offres")
with col3:
    st.write("3. Préparer et envoyer les candidatures")
