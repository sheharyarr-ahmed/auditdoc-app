import asyncio
import logging
import os

import httpx

from schemas import GovernmentCitation

logger = logging.getLogger(__name__)

_ENDPOINTS: dict[str, str] = {
    "sec_edgar":        "/v1/sec/filings",
    "federal_register": "/v1/federal_register/documents",
    "fda":              "/v1/fda/recalls",
    "courtlistener":    "/v1/courts/opinions",
}

_QUERY_MAP: dict[str, str] = {
    "soc2_cc6_1": "logical access controls authentication authorization",
    "soc2_cc6_7": "encryption TLS data in transit security",
    "soc2_cc7_2": "audit logging security event retention",
    "esg_e1":     "greenhouse gas emissions Scope 1 Scope 2 disclosure",
    "esg_s1":     "workforce diversity gender disclosure reporting",
    "esg_g1":     "board independence directors governance",
    "cr_auth":    "authentication credential security password hashing",
    "cr_input":   "input validation injection OWASP sanitization",
    "cr_secrets": "secret management API key credential environment variable",
}


def _is_enabled() -> bool:
    return os.getenv("KATZILLA_ENABLED", "false").lower() in ("1", "true", "yes")


async def _fetch_source(
    client: httpx.AsyncClient,
    base: str,
    key: str,
    timeout: float,
    slug: str,
    path: str,
    query: str,
    limit: int,
) -> list[GovernmentCitation]:
    try:
        async with asyncio.timeout(timeout):
            resp = await client.get(
                f"{base}{path}",
                params={"q": query, "limit": limit},
                headers={"X-API-Key": key},
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        logger.warning("katzilla %s fetch failed: %s", slug, type(exc).__name__)
        return []

    citations: list[GovernmentCitation] = []
    for item in data.get("results", [])[:limit]:
        citations.append(GovernmentCitation(
            source=slug,
            title=item.get("title", ""),
            url=item.get("url", ""),
            date=item.get("date", ""),
            summary=item.get("summary") or item.get("description", ""),
            hash=item.get("hash", ""),
        ))
    return citations


async def fetch_citations(item_id: str, *, limit_per_source: int = 3) -> list[GovernmentCitation]:
    if not _is_enabled():
        return []

    query = _QUERY_MAP.get(item_id)
    if not query:
        logger.debug("katzilla: no query mapping for item_id=%s", item_id)
        return []

    base = os.getenv("KATZILLA_API_BASE", "https://api.katzilla.dev")
    key = os.getenv("KATZILLA_API_KEY", "")
    timeout = float(os.getenv("KATZILLA_TIMEOUT", "5"))

    if not key:
        logger.warning("katzilla: KATZILLA_API_KEY not set, skipping")
        return []

    async with httpx.AsyncClient() as client:
        tasks = [
            _fetch_source(client, base, key, timeout, slug, path, query, limit_per_source)
            for slug, path in _ENDPOINTS.items()
        ]
        results = await asyncio.gather(*tasks)

    flat: list[GovernmentCitation] = []
    for batch in results:
        flat.extend(batch[:1])          # 1 from each source first (breadth)
    for batch in results:
        flat.extend(batch[1:])          # fill remaining slots
    return flat[:limit_per_source]
