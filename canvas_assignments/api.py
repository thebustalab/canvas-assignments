"""Thin helpers over the Canvas REST API. No state, no side effects on import."""

from __future__ import annotations

import re
from typing import Dict, Iterable, List

import requests

TIMEOUT = 60


def auth_headers(token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Accept": "application/json"}


def course_base(domain: str, course_id: str) -> str:
    return f"https://{domain}/api/v1/courses/{course_id}"


def paginated_get(url: str, headers: Dict[str, str]) -> Iterable[List[Dict]]:
    """Yield each page of a Canvas list endpoint, following the Link: rel=next header."""
    while url:
        resp = requests.get(url, headers=headers, timeout=TIMEOUT)
        resp.raise_for_status()
        yield resp.json()
        url = ""
        for part in resp.headers.get("Link", "").split(","):
            match = re.search(r'<([^>]+)>;\s*rel="next"', part.strip())
            if match:
                url = match.group(1)
                break


def fetch_all(url: str, headers: Dict[str, str]) -> List[Dict]:
    """Collect every page of a list endpoint into one list."""
    items: List[Dict] = []
    for page in paginated_get(url, headers):
        items.extend(page)
    return items
