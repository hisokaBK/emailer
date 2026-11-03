from __future__ import annotations

import streamlit as st

from database.repositories import list_applications, update_application

st.title("Mes candidatures")
applications = list_applications()
if not applications:
    st.info("Aucune candidature n'a encore \u00e9t\u00e9 enregistr\u00e9e.")
    st.stop()

status_options = ["new", "in_progress", "interview", "rejected", "accepted"]
status_labels = {
    "new": "Nouvelle", "in_progress": "En cours", "interview": "Entretien",
    "rejected": "Refus\u00e9e", "accepted": "Accept\u00e9e",
}
for app in applications:
    title = app.get("job_title") or app.get("company_name") or "Candidature"
    with st.expander(f"{title} \u2014 {status_labels.get(app.get('application_status'), app.get('application_status', 'Nouvelle'))}", expanded=False):
        st.write(f"Entreprise : {app.get('company_name') or 'Non renseign\u00e9e'}")
        st.write(f"Type : {app.get('application_type') or 'Non pr\u00e9cis\u00e9'}")
        if app.get("target_position"):
            st.write(f"Poste recherch\u00e9 : {app['target_position']}")
        st.write(f"Destinataire : {app.get('recipient_email') or 'Non renseign\u00e9'}")
        st.write(f"Objet : {app.get('subject') or 'Sans objet'}")
        st.write(f"Statut d'envoi : {app.get('sending_status') or 'Non envoy\u00e9'}")
        st.write(f"Corps du message : {app.get('body') or ''}")
        if app.get("last_error"):
            st.error(app["last_error"])
        status = app.get("application_status") or "new"
        status = status if status in status_options else "new"
        updated_status = st.selectbox(
            "Statut de la candidature", status_options, index=status_options.index(status),
            format_func=lambda value: status_labels[value], key=f"application_status_{app['id']}",
        )
        if updated_status != app.get("application_status") and st.button("Mettre \u00e0 jour", key=f"update_{app['id']}"):
            update_application(app["id"], application_status=updated_status)
            st.rerun()
