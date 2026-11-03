from __future__ import annotations

import streamlit as st

from database.repositories import list_jobs
from services.job_fetcher import resolve_job_url

st.title("D\u00e9tails de l'offre")
jobs = list_jobs(100)
if not jobs:
    st.info("Aucune offre n'a encore \u00e9t\u00e9 enregistr\u00e9e. Utilisez le chercheur d'offres pour en ajouter.")
    st.stop()

labels = {f"{job['title'] or 'Offre sans titre'} \u2014 {job['company'] or 'Entreprise inconnue'} \u2014 #{job['id']}": job for job in jobs}
choices = list(labels)
selected_label = st.selectbox("Choisir une offre", choices)
selected = labels[selected_label]
st.session_state["selected_offer"] = selected

st.markdown(f"### {selected['title'] or 'Offre sans titre'}")
st.write(f"Entreprise : {selected['company'] or 'Non renseign\u00e9e'}")
st.write(f"Source : {selected['source']}")
st.write(f"Lieu : {selected['location'] or 'Non pr\u00e9cis\u00e9'}")
job_url = resolve_job_url(selected.get("url"), selected.get("source"))
if job_url:
    st.link_button("Consulter l'offre", job_url)
st.write(selected.get("description") or "Description non disponible.")

if st.button("Pr\u00e9parer ma candidature", type="primary"):
    st.switch_page("pages/4_Email_Generator.py")
