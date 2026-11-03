from __future__ import annotations

import sqlite3

import streamlit as st

from config.settings import BASE_DIR
from database.db import get_connection

st.set_page_config(layout="wide")

st.title("Tableau de bord")

conn = get_connection()
try:
    stats = {
        "jobs": conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0],
        "new_jobs": conn.execute("SELECT COUNT(*) FROM jobs WHERE status = 'new'").fetchone()[0],
        "prepared": conn.execute("SELECT COUNT(*) FROM applications WHERE generation_status = 'prepared'").fetchone()[0],
        "sent": conn.execute("SELECT COUNT(*) FROM applications WHERE sending_status = 'sent'").fetchone()[0],
        "failed": conn.execute("SELECT COUNT(*) FROM applications WHERE sending_status = 'failed'").fetchone()[0],
        "interviews": conn.execute("SELECT COUNT(*) FROM applications WHERE application_status = 'interview'").fetchone()[0],
    }
finally:
    conn.close()

col1, col2, col3, col4, col5, col6 = st.columns(6)
col1.metric("Offres enregistrées", stats["jobs"])
col2.metric("Offres nouvelles", stats["new_jobs"])
col3.metric("Candidatures préparées", stats["prepared"])
col4.metric("Candidatures envoyées", stats["sent"])
col5.metric("Emails en échec", stats["failed"])
col6.metric("Entretiens", stats["interviews"])

st.caption("Les statistiques proviennent directement de la base SQLite locale.")
