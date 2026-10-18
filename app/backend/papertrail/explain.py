from papertrail.llm import GroundedExplanation, LanguageModel
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
    parsed = llm.chat_json(llm.settings.chat_model_large, prompt, GroundedExplanation, max_tokens=500)
    if parsed is None:
        if llm.stopped_for_budget:
            return "Explanation skipped because the LLM call budget was exhausted.", False
        return "The model did not return grounded JSON, so no explanation was kept.", False
    haystack = corpus.lower()
    kept = []
    for quote in parsed.quotes:
        text = quote.text.strip()
        if len(text) >= 12 and text.lower() in haystack:
            kept.append(text)
    explanation = parsed.explanation.strip()
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
