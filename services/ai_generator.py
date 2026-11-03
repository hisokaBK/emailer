from __future__ import annotations

from config.settings import get_env
from services.api_key_manager import ApiKeyManager


PURPOSE_GUIDANCE = {
    "Candidature spontanée – Stage": (
        "Exprime une candidature spontanée pour un stage, l'envie de contribuer et de développer "
        "une expérience pratique. Ne mentionne aucune offre publiée."
    ),
    "Candidature spontanée – Emploi": (
        "Exprime une candidature spontanée pour une opportunité d'emploi. Présente honnêtement "
        "les compétences et projets réels, sans parler de stage."
    ),
    "Candidature spontanée – Poste précis": (
        "Exprime une candidature spontanée pour le poste visé. Ne prétends pas que l'entreprise "
        "recrute, sauf si cela est explicitement vérifié."
    ),
    "Réponse à une offre de stage": (
        "Réponds à l'offre de stage publiée en citant son vrai intitulé et en reliant ses critères "
        "aux faits présents dans le profil."
    ),
    "Réponse à une offre d'emploi": (
        "Réponds à l'offre d'emploi publiée en citant son vrai intitulé et en reliant ses critères "
        "aux faits présents dans le profil."
    ),
}


class AIResponseError(RuntimeError):
    pass


class AIGenerator:
    def __init__(self, model: str | None = None) -> None:
        self.model = model or get_env("GEMINI_MODEL", "gemini-2.5-flash")
        self.key_manager = ApiKeyManager()

    def generate_email_body(
        self,
        company_name: str,
        profile: dict,
        offer_context: dict | None = None,
        application_type: str = "Candidature spontanée – Emploi",
        target_position: str = "",
        additional_instructions: str = "",
        cover_letter_context: dict | None = None,
    ) -> str:
        active_key = self.key_manager.get_active_key()
        if not active_key:
            return self._fallback_body(company_name, profile, offer_context, application_type, target_position)

        try:
            import importlib.util

            if importlib.util.find_spec("google.genai") is None:
                return self._fallback_body(company_name, profile, offer_context, application_type, target_position)

            from google import genai

            client = genai.Client(api_key=active_key)
            prompt = self._build_prompt(
                company_name=company_name,
                profile=profile,
                offer_context=offer_context,
                application_type=application_type,
                target_position=target_position,
                additional_instructions=additional_instructions,
                cover_letter_context=cover_letter_context,
            )
            response = client.models.generate_content(model=self.model, contents=prompt)
            text = getattr(response, "text", None) or ""
            cleaned = text.strip()
            if not cleaned:
                raise AIResponseError("Réponse vide reçue de Gemini.")
            return cleaned
        except Exception as exc:  # pragma: no cover - network or SDK errors depend on the user's environment.
            self.key_manager.mark_failure(active_key, str(exc))
            return self._fallback_body(company_name, profile, offer_context, application_type, target_position)

    def _build_prompt(
        self,
        company_name: str,
        profile: dict,
        offer_context: dict | None = None,
        application_type: str = "Candidature spontanée – Emploi",
        target_position: str = "",
        additional_instructions: str = "",
        cover_letter_context: dict | None = None,
    ) -> str:
        context = offer_context or {}
        skills = profile.get("technical_skills", {})
        compact_skills = [skill for group in skills.values() for skill in group][:12]
        is_offer = bool(context.get("is_published_offer"))
        published_details = (
            f"Intitulé réel de l'offre: {context.get('title', '')}. "
            f"Description de l'offre: {context.get('description', '')}. "
            f"Exigences de l'offre: {context.get('requirements', '')}. "
            if is_offer else ""
        )
        return (
            "Rédige uniquement le corps d'un email de candidature en français professionnel. "
            "Ne génère ni objet ni signature. N'invente aucun fait, activité, expérience, exigence "
            "ou recrutement, et n'affirme pas qu'une compétence est maîtrisée si le profil ne le dit pas. "
            f"Type de candidature: {application_type}. "
            f"Consigne de rédaction pour ce type: {PURPOSE_GUIDANCE.get(application_type, '')} "
            f"Type d'opportunité: {context.get('opportunity_type', '')}. "
            f"Poste recherché: {target_position or context.get('title', '')}. "
            f"Entreprise: {company_name}. "
            f"Activité vérifiée fournie: {context.get('activity', '')}. "
            f"Lieu: {context.get('location', '')}. "
            f"Autres informations sur l'entreprise fournies: {context.get('notes', '')}. "
            f"Résumé du profil: {profile.get('professional_summary', '')}. "
            f"Compétences du profil: {', '.join(compact_skills)}. "
            f"Projets réels: {profile.get('projects', [])}. "
            f"Expérience réelle: {profile.get('experience', [])}. "
            f"Objectif: {profile.get('professional_objective', '')}. "
            f"Contexte utile de la lettre de motivation: {cover_letter_context or {}}. "
            f"{published_details}"
            f"Instructions supplémentaires de l'utilisateur: {additional_instructions}. "
            "Mentionne naturellement que le CV et la lettre de motivation sont joints. "
            "Écris un texte bref, naturel et adapté au type sélectionné."
        )

    def _fallback_body(
        self,
        company_name: str,
        profile: dict,
        offer_context: dict | None = None,
        application_type: str = "Candidature spontanée – Emploi",
        target_position: str = "",
    ) -> str:
        context = offer_context or {}
        position = target_position or context.get("title", "")
        skills = [skill for group in profile.get("technical_skills", {}).values() for skill in group][:8]
        skills_sentence = f" Mon profil comprend notamment {', '.join(skills)}." if skills else ""

        if application_type == "Candidature spontanée – Stage":
            opening = f"Je vous adresse une candidature spontanée afin de rejoindre {company_name} dans le cadre d'un stage"
            closing = "Je souhaite contribuer à vos projets tout en développant une expérience pratique."
        elif application_type == "Candidature spontanée – Poste précis":
            opening = (
                f"Je vous adresse une candidature spontanée pour le poste de {position} au sein de {company_name}"
                if position else f"Je vous adresse une candidature spontanée à {company_name}"
            )
            closing = "Je serais ravi(e) d'échanger sur la manière dont mon profil pourrait répondre à vos besoins."
        elif application_type == "Réponse à une offre de stage":
            opening = (
                f"Je vous adresse ma candidature pour l'offre de stage « {position} » chez {company_name}"
                if position else f"Je vous adresse ma candidature pour votre offre de stage chez {company_name}"
            )
            closing = "Les missions de cette offre m'intéressent particulièrement."
        elif application_type == "Réponse à une offre d'emploi":
            opening = (
                f"Je vous adresse ma candidature pour l'offre « {position} » chez {company_name}"
                if position else f"Je vous adresse ma candidature pour votre offre d'emploi chez {company_name}"
            )
            closing = "Je serais ravi(e) d'échanger sur ma candidature et les besoins liés à ce poste."
        else:
            opening = f"Je vous adresse une candidature spontanée pour une opportunité d'emploi au sein de {company_name}"
            closing = "Je serais ravi(e) d'échanger sur ma candidature et les opportunités adaptées à mon profil."

        return (
            f"Madame, Monsieur,\n\n{opening}.{skills_sentence} {closing} "
            "Vous trouverez en pièces jointes mon CV ainsi que ma lettre de motivation.\n\n"
            "Je vous remercie pour votre temps et reste à votre disposition pour échanger davantage."
        )
