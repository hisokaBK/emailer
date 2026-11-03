from __future__ import annotations

import streamlit as st

from database.repositories import list_jobs, upsert_job
from services.job_fetcher import JobFetcher, resolve_job_url

st.title("Chercheur d'offres")
query = st.text_input("Mot-cl\u00e9 ou comp\u00e9tence", value="")
city = st.text_input("Ville (optionnel)", value="")

if st.button("Rechercher des offres", type="primary"):
    with st.spinner("Recherche dans les sources d'offres..."):
        jobs = JobFetcher().fetch_jobs(query.strip())
    if city.strip():
        jobs = [job for job in jobs if city.casefold() in (job.get("location") or "").casefold()]
    st.session_state["job_search_results"] = jobs
    st.session_state["job_search_query"] = query

results = st.session_state.get("job_search_results", [])
if results:
    st.success(f"{len(results)} offres trouv\u00e9es.")
    for index, job in enumerate(results):
        title = job.get("title") or "Offre sans titre"
        company = job.get("company") or "Entreprise inconnue"
        st.markdown(f"### {title}")
        st.write(f"{company} | {job.get('location') or 'Lieu non pr\u00e9cis\u00e9'} | {job.get('source') or 'Source inconnue'}")
        st.write(job.get("description") or "Description non disponible.")
        job_url = resolve_job_url(job.get("url"), job.get("source"))
        if job_url:
            st.link_button("Consulter l'offre", job_url)
        key = job.get("source_job_id") or job.get("url") or f"{title}-{index}"
        if st.button("Enregistrer l'offre", key=f"save_{job.get('source', 'unknown')}_{key}"):
            upsert_job({
                **job,
                "source": job.get("source") or "unknown",
                "source_job_id": key,
                "url": job_url,
                "title": title,
                "company": company,
                "status": "new",
                "is_active": 1,
            })
            st.success("Offre enregistr\u00e9e dans votre suivi local.")
elif "job_search_results" in st.session_state:
    st.info("Aucune offre correspondante trouv\u00e9e dans les sources actives.")

st.subheader("Offres enregistr\u00e9es")
for job in list_jobs(10):
    st.write(f"- {job['title'] or 'Offre sans titre'} | {job['company'] or 'Entreprise inconnue'} | {job['location'] or 'Lieu non pr\u00e9cis\u00e9'}")
