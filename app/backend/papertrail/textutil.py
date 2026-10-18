import math
import re
from difflib import SequenceMatcher

DOI_RE = re.compile(r"10\.\d{4,9}/[^\s\"'<>]+", re.IGNORECASE)


def clean_doi(raw: str) -> str:
    match = DOI_RE.search(raw.strip())
    if match is None:
        return ""
    return match.group(0).rstrip(").,;]}>'\"")


def norm_title(title: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", title.lower())).strip()


def titles_match(left: str, right: str) -> bool:
    a = norm_title(left)
    b = norm_title(right)
    if not a or not b:
        return False
    if a == b or a in b or b in a:
        return True
    return SequenceMatcher(None, a, b).ratio() >= 0.82


def cosine(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    na = math.sqrt(sum(a * a for a in left))
    nb = math.sqrt(sum(b * b for b in right))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def mean_vector(vectors: list[list[float]]) -> list[float]:
    usable = [item for item in vectors if item]
    if not usable:
        return []
    width = len(usable[0])
    usable = [item for item in usable if len(item) == width]
    if not usable:
        return []
    count = float(len(usable))
    return [sum(item[index] for item in usable) / count for index in range(width)]


def reconstruct_abstract(inverted: dict[str, list[int]] | None) -> str:
    if not inverted:
        return ""
    slots: dict[int, str] = {}
    for word, positions in inverted.items():
        for position in positions:
            slots[int(position)] = word
    if not slots:
        return ""
    return " ".join(slots[index] for index in sorted(slots))


def parse_bibtex(raw: str) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for block in re.split(r"\n(?=@)", raw):
        if "@" not in block:
            continue
        doi = ""
        title = ""
        doi_match = re.search(r"doi\s*=\s*[{\"]([^}\"]+)", block, re.IGNORECASE)
        title_match = re.search(r"title\s*=\s*[{\"]([^}\"]+)", block, re.IGNORECASE)
        if doi_match:
            doi = clean_doi(doi_match.group(1))
        if title_match:
            title = re.sub(r"\s+", " ", title_match.group(1)).strip()
        if doi or title:
            entries.append({"doi": doi, "title": title})
    return entries
