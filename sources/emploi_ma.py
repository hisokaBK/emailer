from __future__ import annotations

import re
from typing import Any

import requests

from sources.base_connector import BaseConnector


class EmploiMaConnector(BaseConnector):
    name = "emploi_ma"

    def fetch_jobs(self, query: str = "") -> list[dict[str, Any]]:
        payload = []
        try:
            response = requests.get("https://www.emploi.ma/", timeout=10)
            text = response.text
            for match in re.findall(r"<a[^>]*href=[\"']([^\"']+)[\"'][^>]*>([^<]+)</a>", text[:25000], flags=re.I):
                href, title = match
                if "offre" in title.lower() or query.lower() in title.lower() or not query:
                    payload.append({
                        "source": self.name,
                        "source_job_id": href,
                        "url": href,
                        "title": title.strip(),
                        "company": "Emploi.ma",
                        "location": "Maroc",
                        "description": "Offre collectée via Emploi.ma.",
                    })
        except Exception:
            pass
        return payload[:10]
