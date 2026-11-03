from __future__ import annotations

import streamlit as st

from config.constants import DEFAULT_EMAIL_SIGNATURE, DEFAULT_EMAIL_SUBJECT
from config.settings import get_env
from database.repositories import get_document_status, get_setting, record_document, save_setting
from services.api_key_manager import ApiKeyManager
from services.cover_letter_service import load_cover_letter_context, save_cover_letter_context
from services.gmail_service import GmailService
from services.pdf_service import extract_text_from_pdf_bytes, save_uploaded_pdf
from services.profile_service import load_profile, parse_cv_text_to_profile, save_profile

st.title("Paramètres")

st.subheader("Documents du profil")
cv_file = st.file_uploader("Téléverser le CV (PDF)", type=["pdf"], key="cv_upload")
cover_file = st.file_uploader("Téléverser la lettre de motivation (PDF)", type=["pdf"], key="cover_upload")

if st.button("Enregistrer les documents", disabled=cv_file is None and cover_file is None):
    try:
        if cv_file is not None:
            cv_bytes = cv_file.getvalue()
            cv_path = save_uploaded_pdf(cv_bytes, cv_file.name, "cv")
            record_document("cv", cv_path.name, str(cv_path))
            extracted_text = extract_text_from_pdf_bytes(cv_bytes)
            if extracted_text:
                profile = parse_cv_text_to_profile(extracted_text, cv_path.name)
                save_profile(profile)
                st.success("CV enregistré et profil prérempli \u00e0 partir du texte extrait.")
            else:
                st.warning("CV enregistré, mais aucun texte n'a pu être extrait. Complétez le profil manuellement.")
        if cover_file is not None:
            cover_path = save_uploaded_pdf(cover_file.getvalue(), cover_file.name, "cover_letter")
            record_document("cover_letter", cover_path.name, str(cover_path))
            st.success("Lettre de motivation enregistrée.")
    except (OSError, ValueError) as exc:
        st.error(str(exc))

profile = load_profile()
cv_status = get_document_status("cv")
cover_status = get_document_status("cover_letter")
st.caption(f"CV : {cv_status['file_name'] if cv_status else 'non fourni'} | Lettre : {cover_status['file_name'] if cover_status else 'non fournie'}")

st.subheader("Contexte de la lettre de motivation")
st.caption("Ajoutez uniquement les arguments utiles à la personnalisation ; le PDF complet n'est pas envoyé à Gemini.")
cover_context = load_cover_letter_context()
with st.form("cover_letter_context"):
    cover_objective = st.text_area(
        "Objectif professionnel",
        value=cover_context.get("professional_objective", ""),
    )
    preferred_opportunity = st.text_area(
        "Type d'opportunité souhaité",
        value=cover_context.get("preferred_opportunity", ""),
    )
    professional_positioning = st.text_area(
        "Positionnement professionnel",
        value=cover_context.get("professional_positioning", ""),
    )
    main_arguments = st.text_area(
        "Arguments principaux",
        value=cover_context.get("main_arguments", ""),
    )
    writing_style = st.text_area(
        "Style de rédaction souhaité",
        value=cover_context.get("writing_style", ""),
    )
    professional_strengths = st.text_area(
        "Points forts professionnels",
        value=cover_context.get("professional_strengths", ""),
    )
    context_saved = st.form_submit_button("Enregistrer le contexte")
if context_saved:
    save_cover_letter_context({
        "professional_objective": cover_objective,
        "preferred_opportunity": preferred_opportunity,
        "professional_positioning": professional_positioning,
        "main_arguments": main_arguments,
        "writing_style": writing_style,
        "professional_strengths": professional_strengths,
    })
    st.success("Contexte enregistré localement dans data/cover_letter_context.json.")

st.subheader("Profil candidat")
with st.form("profile_form"):
    full_name = st.text_input("Nom complet", value=profile.get("personal", {}).get("full_name", ""))
    location = st.text_input("Ville", value=profile.get("personal", {}).get("location", ""))
    summary = st.text_area("Résumé professionnel", value=profile.get("professional_summary", ""), height=120)
    objective = st.text_area("Objectif professionnel", value=profile.get("professional_objective", ""), height=90)
    skills = st.text_input(
        "Compétences (séparées par des virgules)",
        value=", ".join(skill for values in profile.get("technical_skills", {}).values() for skill in values),
    )
    profile_saved = st.form_submit_button("Enregistrer le profil", type="primary")
if profile_saved:
    profile["personal"] = {**profile.get("personal", {}), "full_name": full_name.strip(), "location": location.strip()}
    profile["professional_summary"] = summary.strip()
    profile["professional_objective"] = objective.strip()
    profile["technical_skills"] = {"other": [skill.strip() for skill in skills.split(",") if skill.strip()]}
    save_profile(profile)
    st.success("Profil enregistré localement.")

st.subheader("Email")
with st.form("email_settings"):
    subject = st.text_input("Objet par défaut", value=st.session_state.get("email_subject", get_setting("email_subject", DEFAULT_EMAIL_SUBJECT)))
    signature = st.text_area("Signature professionnelle", value=st.session_state.get("email_signature", get_setting("email_signature", DEFAULT_EMAIL_SIGNATURE)), height=120)
    email_settings_saved = st.form_submit_button("Enregistrer les préférences email")
if email_settings_saved:
    if not subject.strip() or not signature.strip():
        st.error("L'objet et la signature ne peuvent pas être vides.")
    else:
        save_setting("email_subject", subject)
        save_setting("email_signature", signature)
        st.session_state["email_subject"] = subject
        st.session_state["email_signature"] = signature
        st.success("Préférences email enregistrées.")

st.subheader("Gemini")
key_manager = ApiKeyManager()
st.write(f"Clés API configurées : {len(key_manager.get_configured_keys())}")
st.write(f"Modèle : {get_env('GEMINI_MODEL', 'gemini-2.5-flash')}")

st.subheader("Gmail")
service = GmailService()
if st.button("Connecter Gmail"):
    try:
        service.authorize()
        st.success("Compte Gmail autorisé.")
    except Exception as exc:
        st.error(f"Erreur d'authentification Gmail : {exc}")
st.write(f"Statut : {'connecté' if service.is_configured() else 'non connecté'}")
