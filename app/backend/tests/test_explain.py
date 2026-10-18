from papertrail.explain import _linked_seeds, explain_paper
from papertrail.models import Paper


class ModelMustNotRun:
    stopped_for_budget = False

    def chat_json(self, *_args, **_kwargs):
        raise AssertionError("tests must not call a model")


def _paper(paper_id: str, **kwargs) -> Paper:
    values = {"id": paper_id, "project_id": "j", "title": paper_id, "discovery_paths": []}
    values.update(kwargs)
    return Paper(**values)


def test_missing_abstract_does_not_call_a_model():
    text, grounded = explain_paper(_paper("c", abstract=None), [], ModelMustNotRun())  # type: ignore[arg-type]
    assert grounded is False
    assert "no abstract" in text


def test_linked_seeds_prefer_the_discovery_path_and_otherwise_the_first_two():
    first = _paper("s1", title="First seed")
    second = _paper("s2", title="Second seed")
    third = _paper("s3", title="Third seed")
    linked = _paper("c", discovery_paths=[{"seed_id": "s2"}, "ignore", {"other": 1}])
    assert [item.id for item in _linked_seeds(linked, [first, second, third])] == ["s2"]
    assert [item.id for item in _linked_seeds(_paper("c"), [first, second, third])] == ["s1", "s2"]
