MAX_UPLOAD_SIZE_BYTES = 8 * 1024 * 1024
ALLOWED_PDF_MIME_TYPES = {"application/pdf"}
ALLOWED_EXCEL_EXTENSIONS = {".xlsx", ".xls"}
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
DEFAULT_BATCH_PAUSE_SECONDS = 3
DEFAULT_EMAIL_SUBJECT = "Candidature pour une opportunité professionnelle"
DEFAULT_EMAIL_SIGNATURE = "Cordialement,\n\n[Votre nom]\n[Telephone]\n[Adresse e-mail]"
APPLICATION_TYPES = [
    "Candidature spontanée – Stage",
    "Candidature spontanée – Emploi",
    "Candidature spontanée – Poste précis",
    "Réponse à une offre de stage",
    "Réponse à une offre d'emploi",
]

JOB_FILTERS = [
    "Casablanca",
    "Berrechid",
    "Nouaceur",
    "Rabat",
    "Stage",
    "Junior",
    "Bac+2",
]
