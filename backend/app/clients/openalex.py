"""OpenAlex API client with retries and cursor pagination."""
import time
from typing import Any, Dict, Iterator, List, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.core.config import settings


def _session() -> requests.Session:
    s = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503],
    )
    s.mount("https://", HTTPAdapter(max_retries=retries))
    s.headers["User-Agent"] = (
        f"PaperRanking/1.0 (mailto:{settings.OPENALEX_MAILTO})"
        if settings.OPENALEX_MAILTO
        else "PaperRanking/1.0"
    )
    return s


def abstract_inverted_index_to_text(inverted: Optional[Dict[str, List[int]]]) -> str:
    if not inverted:
        return ""
    parts = []
    for word, positions in inverted.items():
        for pos in positions:
            parts.append((pos, word))
    parts.sort(key=lambda x: x[0])
    return " ".join(w for _, w in parts)


def concepts_to_hint_string(concepts: Optional[List[Dict[str, Any]]], top_n: int = 10) -> str:
    if not concepts:
        return ""
    out = []
    for c in concepts[:top_n]:
        name = c.get("display_name") or ""
        score = c.get("score")
        if name:
            out.append(f"{name} ({score:.2f})" if score is not None else name)
    return "; ".join(out)


def get_source_by_issn(issn: str) -> Optional[Dict[str, Any]]:
    url = f"{settings.OPENALEX_BASE_URL}/sources/issn:{issn}"
    try:
        r = _session().get(url, timeout=30)
        r.raise_for_status()
        return r.json()
    except requests.RequestException:
        return None


def search_source_by_name(name: str) -> Optional[Dict[str, Any]]:
    url = f"{settings.OPENALEX_BASE_URL}/sources"
    try:
        r = _session().get(url, params={"search": name, "per_page": 1}, timeout=30)
        r.raise_for_status()
        data = r.json()
        results = data.get("results", [])
        return results[0] if results else None
    except requests.RequestException:
        return None


def iter_works_by_source(
    source_id: str,
    per_page: int = 200,
    sort: str = "publication_date:desc",
) -> Iterator[Dict[str, Any]]:
    """Yield works (papers) for a source using cursor pagination."""
    cursor = "*"
    session = _session()
    while True:
        url = f"{settings.OPENALEX_BASE_URL}/works"
        params = {
            "filter": f"primary_location.source.id:{source_id}",
            "per-page": per_page,
            "cursor": cursor,
            "sort": sort,
        }
        try:
            r = session.get(url, params=params, timeout=60)
            if r.status_code == 429:
                time.sleep(60)
                continue
            r.raise_for_status()
            data = r.json()
        except requests.RequestException as e:
            raise RuntimeError(f"OpenAlex request failed: {e}") from e
        results = data.get("results", [])
        for work in results:
            yield work
        meta = data.get("meta", {})
        next_cursor = meta.get("next_cursor")
        if not next_cursor or not results:
            break
        cursor = next_cursor
        time.sleep(0.2)
