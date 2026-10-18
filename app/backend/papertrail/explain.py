from papertrail.llm import LanguageModel, parse_json_object
from papertrail.models import Paper


def explain_paper(paper: Paper, seeds: list[Paper], llm: LanguageModel) -> tuple[str, bool]:
    linked = _linked_seeds(paper, seeds)[:3]
    if not paper.abstract:
        return "The candidate has no abstract, so the explanation cannot be grounded.", False
    blocks = [f"CANDIDATE\nTitle: {paper.title}\nAbstract: {paper.abstract[:1500]}"]
    for seed in linked:
        abstract = (seed.abstract or "")[:1200]
        blocks.append(f"SEED\nTitle: {seed.title}\nAbstract: {abstract}")
    corpus = "\n\n".join(blocks)
    prompt = (
        "Explain why the candidate is relevant to the seeds. Use only the text below. "
        "Reply with JSON: "
        '{"explanation":"2-4 sentences naming the seed titles",'
        '"grounded":true,"quotes":[{"paper":"title","text":"exact substring"}]}. '
        "Every quote text must be copied from the abstracts below. "
        "If you cannot ground the claim, set grounded to false and say so.\n\n" + corpus
    )
    raw = llm.chat(llm.settings.chat_model_large, prompt, max_tokens=500)
    parsed = parse_json_object(raw)
    if parsed is None:
        if raw is None:
            return "Explanation skipped because the LLM call budget was exhausted.", False
        return "The model did not return grounded JSON, so no explanation was kept.", False
    quotes = parsed.get("quotes") if isinstance(parsed.get("quotes"), list) else []
    haystack = corpus.lower()
    kept = []
    for quote in quotes:
        if not isinstance(quote, dict):
            continue
        text = str(quote.get("text") or "").strip()
        if len(text) >= 12 and text.lower() in haystack:
            kept.append(text)
    explanation = str(parsed.get("explanation") or "").strip()
    if not kept or not explanation:
        return "The model could not ground a claim in the supplied abstracts.", False
    named = any(seed.title and seed.title.split()[0].lower() in explanation.lower() for seed in linked)
    if linked and not named:
        titles = ", ".join(seed.title for seed in linked)
        explanation = f"{explanation} Connected seeds: {titles}."
    return explanation, True


def _linked_seeds(paper: Paper, seeds: list[Paper]) -> list[Paper]:
    wanted = set()
    for path in paper.discovery_paths or []:
        if isinstance(path, dict) and path.get("seed_id"):
            wanted.add(str(path["seed_id"]))
    linked = [seed for seed in seeds if seed.id in wanted]
    return linked or seeds[:2]
