from __future__ import annotations

import re
from typing import Any

import requests

from sources.base_connector import BaseConnector


class MarocAnnoncesConnector(BaseConnector):
    name = "maroc_annonces"

    def fetch_jobs(self, query: str = "") -> list[dict[str, Any]]:
        payload = []
        try:
            response = requests.get("https://www.marocannonces.com/", timeout=10)
            text = response.text
            for match in re.findall(r"<a[^>]*href=[\"']([^\"']+)[\"'][^>]*>([^<]+)</a>", text[:25000], flags=re.I):
                href, title = match
                if "emploi" in title.lower() or query.lower() in title.lower() or not query:
                    payload.append({
                        "source": self.name,
                        "source_job_id": href,
                        "url": href,
                        "title": title.strip(),
                        "company": "Maroc Annonces",
                        "location": "Maroc",
                        "description": "Offre collectée via Maroc Annonces.",
                    })
        except Exception:
            pass
        return payload[:10]
