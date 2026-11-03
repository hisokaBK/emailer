from __future__ import annotations

from urllib.parse import urljoin, urlparse

from sources.anapec import AnapecConnector
from sources.emploi_ma import EmploiMaConnector
from sources.maroc_annonces import MarocAnnoncesConnector
from sources.rekrute import RekruteConnector


class JobFetcher:
    def __init__(self) -> None:
        self.connectors = [
            AnapecConnector(),
            RekruteConnector(),
            EmploiMaConnector(),
            MarocAnnoncesConnector(),
        ]

    def fetch_jobs(self, query: str = "") -> list[dict]:
        jobs = []
        for connector in self.connectors:
            try:
                jobs.extend(connector.fetch_jobs(query))
            except Exception:
                continue
        return jobs


SOURCE_BASE_URLS = {
    "anapec": "https://www.anapec.org/",
    "emploi_ma": "https://www.emploi.ma/",
    "maroc_annonces": "https://www.marocannonces.com/",
    "rekrute": "https://www.rekrute.com/",
}


def resolve_job_url(url: str | None, source: str | None = None) -> str | None:
    if not url:
        return None
    base_url = SOURCE_BASE_URLS.get(source or "")
    resolved = urljoin(base_url, url) if base_url else url
    parsed = urlparse(resolved)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return resolved
