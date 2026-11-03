from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from config.constants import APPLICATION_TYPES, DEFAULT_EMAIL_SIGNATURE, DEFAULT_EMAIL_SUBJECT
from database.repositories import (
    add_application,
    get_application,
    get_document_status,
    get_setting,
    list_applications,
    save_company,
    save_setting,
    update_application,
)
from services.ai_generator import AIGenerator
from services.cover_letter_service import load_cover_letter_context
from services.excel_service import detect_upload_sheets, read_excel_upload
from services.gmail_service import GmailService
from services.profile_service import load_profile
from services.validation_service import is_valid_email, normalize_email

st.title("Générateur d'emails")
profile = load_profile()
cover_letter_context = load_cover_letter_context()
st.caption(f"Profil : {profile.get('personal', {}).get('full_name') or 'non configuré'}")

subject = get_setting("email_subject", DEFAULT_EMAIL_SUBJECT)
signature = get_setting("email_signature", DEFAULT_EMAIL_SIGNATURE)
if not subject:
    st.error("Configurez l'objet fixe dans Paramètres avant de générer un email.")
    st.stop()
st.text_input("Objet fixe utilisé pour chaque email", value=subject, disabled=True)

selected_offer = st.session_state.get("selected_offer")
if selected_offer:
    if st.button("Nouvelle candidature spontanée"):
        for key in (
            "selected_offer",
            "draft_application_id",
            "draft_job_id",
            "email_body",
            "manual_draft_context",
            "manual_draft_application_id",
        ):
            st.session_state.pop(key, None)
        st.rerun()
    selected_title = selected_offer.get("title") or "Offre sans titre"
    previous_job_id = st.session_state.get("draft_job_id")
    if previous_job_id is not None and previous_job_id != selected_offer.get("id"):
        st.session_state.pop("draft_application_id", None)
        st.session_state.pop("email_body", None)
    st.session_state["draft_job_id"] = selected_offer.get("id")
    contract_info = " ".join(
        str(selected_offer.get(key) or "")
        for key in ("contract_type", "experience_level", "title")
    ).casefold()
    is_internship = any(term in contract_info for term in ("stage", "internship", "stagiaire"))
    application_type = (
        "Réponse à une offre de stage" if is_internship else "Réponse à une offre d'emploi"
    )
    opportunity_type = "Stage" if is_internship else "Emploi"
    company_name = selected_offer.get("company") or ""
    st.info(
        f"Réponse à une offre publiée — type détecté : **{application_type}**. "
        f"Poste réel : **{selected_title}**."
    )
    st.write(f"Entreprise : **{company_name or 'non renseignée'}**")
    st.write(f"Lieu : {selected_offer.get('location') or 'non précisé'}")
    recipient = st.text_input(
        "Adresse e-mail du recruteur",
        value=st.session_state.get("email_recipient", ""),
        key="offer_recipient",
    )
    instructions = st.text_area("Instructions complémentaires (facultatif)", key="offer_instructions")
    offer_context = {
        "is_published_offer": True,
        "title": selected_title,
        "opportunity_type": opportunity_type,
        "location": selected_offer.get("location") or "",
        "description": selected_offer.get("description") or "",
        "requirements": selected_offer.get("requirements") or "",
        "activity": selected_offer.get("activity") or "",
    }
    if st.button("Générer le brouillon", type="primary"):
        st.session_state["email_body"] = AIGenerator().generate_email_body(
            company_name=company_name or "Entreprise",
            profile=profile,
            offer_context=offer_context,
            application_type=application_type,
            target_position=selected_title,
            additional_instructions=instructions,
            cover_letter_context=cover_letter_context,
        )
        st.session_state["email_subject"] = subject
        st.session_state["draft_application_type"] = application_type
        st.session_state["draft_opportunity_type"] = opportunity_type
        st.session_state["draft_target_position"] = selected_title

    with st.form("offer_application_email"):
        edited_body = st.text_area(
            "Corps du message (à relire avant envoi)",
            value=st.session_state.get("email_body", ""),
            height=240,
        )
        edited_signature = st.text_area("Signature", value=signature, height=120)
        save_clicked = st.form_submit_button("Enregistrer le brouillon")
        send_clicked = st.form_submit_button("Enregistrer et envoyer via Gmail", type="primary")

    if save_clicked or send_clicked:
        try:
            if not company_name:
                raise ValueError("L'offre ne contient pas de nom d'entreprise.")
            if not edited_body.strip():
                raise ValueError("Le corps du message est vide. Générez ou rédigez un brouillon.")
            if not edited_signature:
                raise ValueError("La signature professionnelle doit être configurée dans Paramètres.")
            if send_clicked and not is_valid_email(recipient):
                raise ValueError("Veuillez saisir une adresse e-mail valide avant l'envoi.")
            final_body = f"{edited_body.strip()}\n\n{edited_signature}"
            draft_id = st.session_state.get("draft_application_id")
            existing = get_application(draft_id) if draft_id else None
            if send_clicked and existing and existing.get("sending_status") == "sent":
                raise ValueError("Cette candidature a déjà été envoyée.")
            company_id = save_company(company_name)
            payload = {
                "company_id": company_id,
                "job_id": selected_offer.get("id"),
                "recipient_email": recipient.strip() or None,
                "subject": subject,
                "body": final_body,
                "generation_status": "prepared",
                "sending_status": existing.get("sending_status", "not_sent") if existing else "not_sent",
                "application_status": existing.get("application_status", "new") if existing else "new",
                "application_type": application_type,
                "opportunity_type": opportunity_type,
                "target_position": selected_title,
                "additional_instructions": instructions,
            }
            if draft_id:
                update_application(
                    draft_id,
                    **{key: value for key, value in payload.items() if key not in {"company_id", "job_id"}},
                )
            else:
                draft_id = add_application(payload)
                st.session_state["draft_application_id"] = draft_id
            save_setting("email_signature", edited_signature)
            if send_clicked:
                cv = get_document_status("cv")
                cover = get_document_status("cover_letter")
                if not cv or not cover:
                    raise ValueError("Téléversez votre CV et votre lettre de motivation dans Paramètres avant l'envoi.")
                files = [Path(cv["file_path"]), Path(cover["file_path"])]
                if not all(path.is_file() for path in files):
                    raise ValueError("Un document joint est introuvable. Téléversez-le à nouveau dans Paramètres.")
                update_application(draft_id, sending_status="sending", last_error=None)
                try:
                    message_id = GmailService().send_message(
                        to_email=recipient.strip(),
                        subject=subject,
                        body=final_body,
                        attachments=[(path.name, path.read_bytes()) for path in files],
                    )
                except Exception as exc:
                    update_application(draft_id, sending_status="failed", last_error=str(exc))
                    raise
                update_application(
                    draft_id,
                    sending_status="sent",
                    gmail_message_id=message_id,
                    sent_at=datetime.utcnow().isoformat(),
                    last_error=None,
                )
                st.success("Candidature envoyée via Gmail et enregistrée dans votre suivi.")
            else:
                st.success("Brouillon enregistré dans Mes candidatures.")
        except (OSError, RuntimeError, ValueError) as exc:
            st.error(str(exc))

    if st.session_state.get("email_body"):
        st.subheader("Prévisualisation")
        st.text_area("Email généré", value=st.session_state["email_body"], height=220, disabled=True)
    st.stop()

st.subheader("Type de candidature")
application_type = st.selectbox("Type de candidature", APPLICATION_TYPES, key="application_type")
opportunity_type = "Stage" if application_type.endswith("Stage") else "Emploi"
target_position = st.text_input(
    "Poste recherché (facultatif, requis pour un poste précis)",
    placeholder="Ex. Développeur Full-Stack",
)
is_published_offer = application_type in {
    "Réponse à une offre de stage",
    "Réponse à une offre d'emploi",
}

additional_instructions = st.text_area(
    "Instructions complémentaires (facultatif)",
    placeholder="Ex. Mettre l'accent sur un projet précis ou une disponibilité.",
)
source = st.radio("Préparer pour", ["Une entreprise", "Un lot Excel"], horizontal=True)

if source == "Une entreprise":
    company_name = st.text_input("Nom de l'entreprise")
    recipient = st.text_input("Adresse e-mail du recruteur")
    activity = st.text_input("Activité vérifiée de l'entreprise (facultatif)")
    location = st.text_input("Ville (facultatif)")
    offer_description = ""
    offer_requirements = ""
    if is_published_offer:
        target_position = st.text_input(
            "Intitulé réel de l'offre",
            value=target_position,
            placeholder="Ex. Stage Développeur Web",
        )
        offer_description = st.text_area("Description réelle de l'offre")
        offer_requirements = st.text_area("Exigences réelles de l'offre (facultatif)")
    if st.button("Générer le brouillon", type="primary"):
        if not company_name.strip():
            st.error("Saisissez le nom de l'entreprise.")
        elif application_type == "Candidature spontanée – Poste précis" and not target_position.strip():
            st.error("Saisissez le poste recherché pour cette candidature.")
        elif is_published_offer and (not target_position.strip() or not offer_description.strip()):
            st.error("Pour répondre à une offre, saisissez son intitulé et sa description réels.")
        else:
            previous_context = st.session_state.get("manual_draft_context")
            current_context = {
                "company_name": company_name.strip(),
                "recipient": recipient.strip(),
                "application_type": application_type,
                "opportunity_type": opportunity_type,
                "target_position": target_position.strip(),
                "additional_instructions": additional_instructions,
            }
            if previous_context and any(
                previous_context.get(key) != current_context.get(key)
                for key in ("company_name", "application_type", "target_position")
            ):
                st.session_state.pop("manual_draft_application_id", None)
            st.session_state["email_body"] = AIGenerator().generate_email_body(
                company_name=company_name.strip(),
                profile=profile,
                offer_context={
                    "is_published_offer": is_published_offer,
                    "opportunity_type": opportunity_type,
                    "activity": activity.strip(),
                    "location": location.strip(),
                    "title": target_position.strip(),
                    "description": offer_description.strip(),
                    "requirements": offer_requirements.strip(),
                },
                application_type=application_type,
                target_position=target_position.strip(),
                additional_instructions=additional_instructions,
                cover_letter_context=cover_letter_context,
            )
            st.session_state["email_subject"] = subject
            st.session_state["manual_draft_context"] = current_context
    manual_context = st.session_state.get("manual_draft_context")
    if manual_context and st.session_state.get("email_body"):
        with st.form("manual_application_email"):
            recipient = st.text_input("Adresse e-mail du recruteur", value=manual_context["recipient"])
            edited_body = st.text_area("Corps du message (à relire avant envoi)", value=st.session_state["email_body"], height=240)
            edited_signature = st.text_area("Signature", value=signature, height=120)
            save_clicked = st.form_submit_button("Enregistrer le brouillon")
            send_clicked = st.form_submit_button("Enregistrer et envoyer via Gmail", type="primary")
        if save_clicked or send_clicked:
            try:
                if not edited_body.strip():
                    raise ValueError("Le corps du message est vide.")
                if not edited_signature:
                    raise ValueError("La signature professionnelle doit être configurée dans Paramètres.")
                if send_clicked and not is_valid_email(recipient):
                    raise ValueError("Veuillez saisir une adresse e-mail valide avant l'envoi.")
                final_body = f"{edited_body.strip()}\n\n{edited_signature}"
                draft_id = st.session_state.get("manual_draft_application_id")
                company_id = save_company(manual_context["company_name"])
                payload = {
                    "company_id": company_id,
                    "recipient_email": recipient.strip() or None,
                    "subject": subject,
                    "body": final_body,
                    "generation_status": "prepared",
                    "sending_status": "not_sent",
                    "application_status": "new",
                    "application_type": manual_context["application_type"],
                    "opportunity_type": manual_context["opportunity_type"],
                    "target_position": manual_context["target_position"],
                    "additional_instructions": manual_context["additional_instructions"],
                }
                if draft_id:
                    update_application(
                        draft_id,
                        **{key: value for key, value in payload.items() if key != "company_id"},
                    )
                else:
                    draft_id = add_application(payload)
                    st.session_state["manual_draft_application_id"] = draft_id
                save_setting("email_signature", edited_signature)
                if send_clicked:
                    cv = get_document_status("cv")
                    cover = get_document_status("cover_letter")
                    if not cv or not cover:
                        raise ValueError("Téléversez votre CV et votre lettre de motivation dans Paramètres avant l'envoi.")
                    files = [Path(cv["file_path"]), Path(cover["file_path"])]
                    if not all(path.is_file() for path in files):
                        raise ValueError("Un document joint est introuvable. Téléversez-le à nouveau dans Paramètres.")
                    update_application(draft_id, sending_status="sending")
                    try:
                        message_id = GmailService().send_message(
                            recipient.strip(), subject, final_body,
                            [(path.name, path.read_bytes()) for path in files],
                        )
                    except Exception as exc:
                        update_application(draft_id, sending_status="failed", last_error=str(exc))
                        raise
                    update_application(
                        draft_id, sending_status="sent", gmail_message_id=message_id,
                        sent_at=datetime.utcnow().isoformat(), last_error=None,
                    )
                    st.success("Candidature envoyée via Gmail et enregistrée dans votre suivi.")
                else:
                    st.success("Brouillon enregistré dans Mes candidatures.")
            except (OSError, RuntimeError, ValueError) as exc:
                st.error(str(exc))
        st.subheader("Prévisualisation")
        st.text_area("Email généré", value=st.session_state["email_body"], height=220, disabled=True)
else:
    uploaded_file = st.file_uploader("Fichier Excel des entreprises", type=["xlsx", "xls"])
    if uploaded_file is None:
        st.info("Chargez un fichier Excel contenant au minimum le nom de l'entreprise et son adresse e-mail.")
        st.stop()
    try:
        excel_bytes = uploaded_file.getvalue()
        sheets = detect_upload_sheets(excel_bytes)
        sheet_name = st.selectbox("Feuille Excel", sheets)
        dataframe = read_excel_upload(excel_bytes, sheet_name)
    except (ValueError, OSError, ImportError) as exc:
        st.error(f"Impossible de lire ce fichier Excel : {exc}")
        st.stop()
    headers = ["— Ne pas mapper —", *[str(column) for column in dataframe.columns]]
    st.caption("Associez les colonnes du fichier aux informations nécessaires. Nom et e-mail sont requis.")
    mapping_fields = [
        ("company_name", "Nom de l'entreprise", True),
        ("email", "Adresse e-mail", True),
        ("activity", "Activité de l'entreprise", False),
        ("city", "Ville", False),
        ("job_title", "Poste recherché / titre d'offre", False),
        ("description", "Description d'offre publiée", False),
        ("requirements", "Exigences d'offre", False),
        ("notes", "Informations complémentaires", False),
    ]
    mapping: dict[str, str] = {}
    mapping_columns = st.columns(3)
    for index, (field, label, required) in enumerate(mapping_fields):
        default = next(
            (
                header for header in headers[1:]
                if (field == "company_name" and any(term in header.casefold() for term in ("entreprise", "company", "société", "nom")))
                or (field == "email" and ("email" in header.casefold() or "e-mail" in header.casefold() or "mail" in header.casefold()))
                or (field == "activity" and any(term in header.casefold() for term in ("activité", "activity", "secteur")))
                or (field == "city" and any(term in header.casefold() for term in ("ville", "city", "localisation")))
                or (field == "job_title" and any(term in header.casefold() for term in ("poste", "job", "titre")))
                or (field == "description" and any(term in header.casefold() for term in ("description", "descriptif", "mission")))
                or (field == "requirements" and any(term in header.casefold() for term in ("exigence", "requirement", "pré-requis", "prerequis")))
                or (field == "notes" and any(term in header.casefold() for term in ("note", "info", "commentaire")))
            ),
            headers[1] if field == "company_name" and len(headers) > 1 else headers[0],
        )
        selected_header = mapping_columns[index % 3].selectbox(
            f"{label}{' *' if required else ''}",
            headers,
            index=headers.index(default),
            key=f"excel_map_{field}",
        )
        if selected_header != headers[0]:
            mapping[field] = selected_header

    if "company_name" not in mapping or "email" not in mapping:
        st.warning("Sélectionnez une colonne pour le nom d'entreprise et une pour l'adresse e-mail.")
        st.stop()

    records: list[dict] = []
    for _, row in dataframe.iterrows():
        record = {
            field: str(row.get(column, "")).strip()
            for field, column in mapping.items()
        }
        records.append(record)

    prior_emails = {
        normalize_email(application.get("recipient_email"))
        for application in list_applications()
        if application.get("recipient_email")
    }
    seen_batch: set[str] = set()
    rows = []
    for record in records:
        company = record.get("company_name", "")
        email = record.get("email", "")
        normalized_email = normalize_email(email)
        if not company and not email:
            continue
        if not company:
            status = "Nom d'entreprise manquant"
        elif not normalized_email:
            status = "Adresse e-mail invalide"
        elif normalized_email in seen_batch:
            status = "Doublon dans le fichier"
        elif normalized_email in prior_emails:
            status = "Déjà présent dans l'historique"
        else:
            status = "Prêt"
        if normalized_email:
            seen_batch.add(normalized_email)
        rows.append({
            "Entreprise": company,
            "E-mail": email,
            "Activité": record.get("activity", ""),
            "Ville": record.get("city", ""),
            "Poste recherché": record.get("job_title", "") or target_position,
            "Description d'offre": record.get("description", ""),
            "Exigences d'offre": record.get("requirements", ""),
            "Informations": record.get("notes", ""),
            "Type de candidature": application_type,
            "Statut de validation": status,
        })
    if not rows:
        st.warning("Aucune ligne exploitable dans cette feuille.")
        st.stop()
    editable = st.data_editor(
        pd.DataFrame(rows),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Type de candidature": st.column_config.SelectboxColumn(
                "Type de candidature", options=APPLICATION_TYPES, required=True
            ),
            "Poste recherché": st.column_config.TextColumn("Poste recherché"),
            "Statut de validation": st.column_config.TextColumn("Statut de validation", disabled=True),
        },
        disabled=[
            "Entreprise", "E-mail", "Activité", "Ville", "Description d'offre",
            "Exigences d'offre", "Informations", "Statut de validation",
        ],
        key="excel_application_rows",
    )
    status_counts = editable["Statut de validation"].value_counts().to_dict()
    invalid_count = status_counts.get("Adresse e-mail invalide", 0) + status_counts.get("Nom d'entreprise manquant", 0)
    duplicate_count = status_counts.get("Doublon dans le fichier", 0) + status_counts.get("Déjà présent dans l'historique", 0)
    st.write(
        f"Entreprises prêtes : {status_counts.get('Prêt', 0)} · "
        f"invalides : {invalid_count} · "
        f"doublons/déjà contactées : {duplicate_count}"
    )
    if application_type == "Candidature spontanée – Poste précis" and not target_position.strip():
        st.info("Chaque ligne peut définir son propre poste recherché.")
    if st.button("Générer les emails du lot", type="primary"):
        ready_rows = editable[editable["Statut de validation"] == "Prêt"]
        batch_result = []
        if ready_rows.empty:
            st.warning("Aucune entreprise éligible à traiter.")
        else:
            generator = AIGenerator()
            for _, row in ready_rows.iterrows():
                selected_type = row["Type de candidature"]
                per_row_position = str(row["Poste recherché"] or "").strip()
                row_is_published_offer = selected_type in {
                    "Réponse à une offre de stage",
                    "Réponse à une offre d'emploi",
                }
                if selected_type == "Candidature spontanée – Poste précis" and not per_row_position:
                    batch_result.append({
                        "company": row["Entreprise"], "email": row["E-mail"],
                        "status": "Erreur : poste recherché requis", "body": "",
                    })
                    continue
                if row_is_published_offer and (
                    not per_row_position or not str(row["Description d'offre"] or "").strip()
                ):
                    batch_result.append({
                        "company": row["Entreprise"], "email": row["E-mail"],
                        "status": "Erreur : intitulé ou description d'offre manquant", "body": "",
                    })
                    continue
                per_row_opportunity = "Stage" if selected_type.endswith("Stage") else "Emploi"
                try:
                    generated_body = generator.generate_email_body(
                        company_name=row["Entreprise"],
                        profile=profile,
                        offer_context={
                            "is_published_offer": row_is_published_offer,
                            "opportunity_type": per_row_opportunity,
                            "activity": row["Activité"],
                            "location": row["Ville"],
                            "notes": row["Informations"],
                            "title": per_row_position,
                            "description": row["Description d'offre"],
                            "requirements": row["Exigences d'offre"],
                        },
                        application_type=selected_type,
                        target_position=per_row_position,
                        additional_instructions=additional_instructions,
                        cover_letter_context=cover_letter_context,
                    )
                    final_body = f"{generated_body.strip()}\n\n{signature}"
                    company_id = save_company(row["Entreprise"])
                    application_id = add_application({
                        "company_id": company_id,
                        "recipient_email": row["E-mail"],
                        "subject": subject,
                        "body": final_body,
                        "generation_status": "prepared",
                        "sending_status": "not_sent",
                        "application_status": "new",
                        "application_type": selected_type,
                        "opportunity_type": per_row_opportunity,
                        "target_position": per_row_position,
                        "additional_instructions": additional_instructions,
                        "notes": row["Informations"],
                    })
                    batch_result.append({
                        "company": row["Entreprise"], "email": row["E-mail"],
                        "status": f"Brouillon enregistré #{application_id}",
                        "subject": subject, "body": final_body,
                        "application_type": selected_type,
                    })
                except (RuntimeError, ValueError, OSError) as exc:
                    batch_result.append({
                        "company": row["Entreprise"], "email": row["E-mail"],
                        "status": f"Erreur : {exc}", "body": "",
                    })
            st.session_state["generated_batch"] = batch_result
            st.success(f"{sum(item['status'].startswith('Brouillon enregistré') for item in batch_result)} brouillons générés et enregistrés.")

    for item in st.session_state.get("generated_batch", []):
        st.markdown(f"#### {item['company']} — {item['email']}")
        st.caption(f"{item['status']} · {item.get('application_type', '')}")
        if item.get("body"):
            st.text_area(
                f"Prévisualisation — {item['company']}",
                value=f"Objet : {item.get('subject', subject)}\n\n{item['body']}",
                height=220,
                key=f"preview_{item['email']}",
                disabled=True,
            )
