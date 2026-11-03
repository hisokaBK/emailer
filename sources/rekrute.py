from __future__ import annotations

import re
from typing import Any

import requests

from sources.base_connector import BaseConnector


class RekruteConnector(BaseConnector):
    name = "rekrute"

    def fetch_jobs(self, query: str = "") -> list[dict[str, Any]]:
        payload = []
        try:
            response = requests.get("https://www.rekrute.com/", timeout=10)
            text = response.text
            for match in re.findall(r"<a[^>]*href=[\"']([^\"']+)[\"'][^>]*>([^<]+)</a>", text[:25000], flags=re.I):
                href, title = match
                if "emploi" in title.lower() or query.lower() in title.lower() or not query:
                    payload.append({
                        "source": self.name,
                        "source_job_id": href,
                        "url": href,
                        "title": title.strip(),
                        "company": "Rekrute",
                        "location": "Maroc",
                        "description": "Offre collectée via Rekrute.",
                    })
        except Exception:
            pass
        return payload[:10]
