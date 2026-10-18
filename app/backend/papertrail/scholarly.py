import time
from dataclasses import dataclass, field
from urllib.parse import quote

import httpx
from sqlalchemy.orm import Session

from papertrail.cache import cache_get, cache_key, cache_put
from papertrail.config import Settings
from papertrail.textutil import clean_doi, reconstruct_abstract, titles_match


@dataclass
class Work:
    openalex_id: str | None
    doi: str | None
    title: str
    abstract: str
    authors: list[dict]
    year: int | None
    venue: str | None
    citation_count: int
    source_urls: list[str]
    is_retracted: bool
    referenced_works: list[str]
    raw: dict = field(default_factory=dict)


class Scholarly:
    def __init__(self, settings: Settings, session: Session) -> None:
        email = settings.scholarly_contact_email.strip() or "unset@example.com"
        self.session = session
        self.client = httpx.Client(
            timeout=40,
            headers={"User-Agent": f"papertrail/0.1 (mailto:{email})"},
        )

    def close(self) -> None:
        self.client.close()

    def get_json(self, url: str) -> dict | None:
        key = cache_key("http", url)
        cached = cache_get(self.session, key)
        if cached is not None:
            body = cached.get("body")
            return body if isinstance(body, dict) else None
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                response = self.client.get(url)
                if response.status_code == 404:
                    cache_put(self.session, key, "http", {"body": {}})
                    return None
                if response.status_code in {429, 500, 502, 503, 504}:
                    time.sleep(0.4 * (attempt + 1))
                    continue
                response.raise_for_status()
                body = response.json()
                if isinstance(body, dict):
                    cache_put(self.session, key, "http", {"body": body})
                    return body
                return None
            except httpx.HTTPError as exc:
                last_error = exc
                time.sleep(0.4 * (attempt + 1))
        if last_error is not None:
            return None
        return None

    def by_doi(self, doi: str) -> Work | None:
        cleaned = clean_doi(doi)
        if not cleaned:
            return None
        url = f"https://api.openalex.org/works/https://doi.org/{quote(cleaned, safe='')}"
        body = self.get_json(url)
        if body and body.get("id"):
            return openalex_work(body)
        crossref = self.crossref(cleaned)
        return crossref

    def by_title(self, title: str) -> Work | None:
        query = quote(title.strip())
        url = f"https://api.openalex.org/works?search={query}&per-page=5"
        body = self.get_json(url)
        results = (body or {}).get("results") or []
        best: Work | None = None
        for item in results:
            work = openalex_work(item)
            if titles_match(title, work.title):
                return work
            if best is None:
                best = work
        if best is not None and titles_match(title, best.title):
            return best
        crossref_url = "https://api.crossref.org/works?rows=3&query.bibliographic=" + quote(title.strip())
        crossref_body = self.get_json(crossref_url)
        items = ((crossref_body or {}).get("message") or {}).get("items") or []
        for item in items:
            work = crossref_item(item)
            if work and titles_match(title, work.title):
                return work
        return None

    def crossref(self, doi: str) -> Work | None:
        url = f"https://api.crossref.org/works/{quote(doi, safe='')}"
        body = self.get_json(url)
        if not body:
            return None
        message = body.get("message")
        if not isinstance(message, dict):
            return None
        return crossref_item(message)

    def search(self, query: str, per_page: int = 15) -> list[Work]:
        url = f"https://api.openalex.org/works?search={quote(query)}&per-page={per_page}"
        body = self.get_json(url)
        results = (body or {}).get("results") or []
        return [openalex_work(item) for item in results if item.get("title")]

    def by_ids(self, ids: list[str]) -> list[Work]:
        short = [short_id(item) for item in ids if item][:25]
        if not short:
            return []
        joined = "|".join(short)
        url = f"https://api.openalex.org/works?filter=openalex:{joined}&per-page=25"
        body = self.get_json(url)
        return [openalex_work(item) for item in (body or {}).get("results") or [] if item.get("title")]

    def neighbors(self, openalex_id: str) -> tuple[list[Work], list[Work]]:
        short = short_id(openalex_id)
        if not short:
            return [], []
        citing_url = f"https://api.openalex.org/works?filter=cites:{short}&per-page=25"
        cited_url = f"https://api.openalex.org/works?filter=cited_by:{short}&per-page=25"
        citing = self.get_json(citing_url)
        cited = self.get_json(cited_url)
        incoming = [openalex_work(item) for item in (citing or {}).get("results") or []]
        outgoing = [openalex_work(item) for item in (cited or {}).get("results") or []]
        return incoming, outgoing

    def citing_authors(self, openalex_id: str) -> list[str]:
        short = short_id(openalex_id)
        if not short:
            return []
        url = f"https://api.openalex.org/works?filter=cites:{short}&per-page=10&select=authorships"
        body = self.get_json(url)
        names: list[str] = []
        for item in (body or {}).get("results") or []:
            for authorship in item.get("authorships") or []:
                author = authorship.get("author") or {}
                author_id = author.get("id")
                if author_id:
                    names.append(str(author_id))
        return names

    def author_profile(self, author_id: str) -> dict | None:
        url = f"https://api.openalex.org/authors/{quote(author_id, safe=':/')}"
        return self.get_json(url)


def short_id(value: str | None) -> str:
    if not value:
        return ""
    return value.rstrip("/").split("/")[-1]


def openalex_work(body: dict) -> Work:
    doi = clean_doi(str(body.get("doi") or ""))
    authorships = body.get("authorships") or []
    authors = []
    for item in authorships:
        author = item.get("author") or {}
        authors.append(
            {
                "name": author.get("display_name") or "",
                "openalex_id": short_id(author.get("id")),
                "orcid": author.get("orcid") or "",
            }
        )
    location = body.get("primary_location") or {}
    source = location.get("source") or {}
    urls = []
    if doi:
        urls.append(f"https://doi.org/{doi}")
    if body.get("id"):
        urls.append(str(body["id"]))
    landing = location.get("landing_page_url")
    if landing:
        urls.append(str(landing))
    refs = [short_id(item) for item in body.get("referenced_works") or [] if item]
    return Work(
        openalex_id=short_id(body.get("id")),
        doi=doi or None,
        title=str(body.get("title") or ""),
        abstract=reconstruct_abstract(body.get("abstract_inverted_index")),
        authors=authors,
        year=body.get("publication_year"),
        venue=(source.get("display_name") if isinstance(source, dict) else None),
        citation_count=int(body.get("cited_by_count") or 0),
        source_urls=urls,
        is_retracted=bool(body.get("is_retracted")),
        referenced_works=refs,
        raw={
            "source": source if isinstance(source, dict) else {},
            "openalex_url": body.get("id"),
            "referenced_works": refs,
        },
    )


def crossref_item(message: dict) -> Work | None:
    titles = message.get("title") or []
    title = titles[0] if titles else ""
    if not title:
        return None
    doi = clean_doi(str(message.get("DOI") or ""))
    authors = []
    for author in message.get("author") or []:
        given = author.get("given") or ""
        family = author.get("family") or ""
        name = f"{given} {family}".strip()
        authors.append({"name": name, "orcid": author.get("ORCID") or "", "openalex_id": ""})
    year = None
    issued = ((message.get("issued") or {}).get("date-parts") or [[]])[0]
    if issued:
        year = issued[0]
    containers = message.get("container-title") or []
    venue = containers[0] if containers else None
    retracted = False
    for update in message.get("update-to") or []:
        if str(update.get("type") or "").lower() in {"retraction", "retracted"}:
            retracted = True
    urls = []
    if doi:
        urls.append(f"https://doi.org/{doi}")
    if message.get("URL"):
        urls.append(str(message["URL"]))
    return Work(
        openalex_id=None,
        doi=doi or None,
        title=title,
        abstract=str(message.get("abstract") or ""),
        authors=authors,
        year=year,
        venue=venue,
        citation_count=int(message.get("is-referenced-by-count") or 0),
        source_urls=urls,
        is_retracted=retracted,
        referenced_works=[],
        raw={"crossref": True, "update_to": message.get("update-to") or []},
    )
