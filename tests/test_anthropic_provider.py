import json
from types import SimpleNamespace

import pytest

from redline.anthropic_provider import BASE_URL, AnthropicProvider, ProviderError, make_client
from redline.parse import load
from redline.playbook import load_playbook

GOOD = {
    "edits": [{"paragraph_id": "p0013", "rule_id": "law-venue", "find": "Texas", "replace": "New York", "comment": "c"}],
    "missing": [],
}


def response(text, stop_reason="end_turn"):
    return SimpleNamespace(
        content=[SimpleNamespace(type="text", text=text)],
        stop_reason=stop_reason,
        usage=SimpleNamespace(input_tokens=100, output_tokens=20),
    )


class StubClient:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.requests = []
        self.messages = self

    def create(self, **kwargs):
        self.requests.append(kwargs)
        return self.responses.pop(0)


def run(client):
    provider = AnthropicProvider(client=client, model="test-model")
    document = load("fixtures/counterparty_nda.docx")
    return provider, provider.review(document, load_playbook("playbooks/nda.yaml"))


def test_valid_output_needs_one_call():
    client = StubClient(response(json.dumps(GOOD)))
    provider, result = run(client)
    assert result.edits[0].replace == "New York"
    assert result.model == "test-model"
    assert len(client.requests) == 1
    request = client.requests[0]
    assert request["model"] == "test-model"
    assert "not instructions" in request["system"]
    prompt = request["messages"][0]["content"]
    assert prompt.startswith("<contract>\n")
    assert prompt.index("</contract>") < prompt.index("<playbook>") < prompt.index("Review the contract")
    assert "contractnli" not in prompt
    assert provider.calls[0].input_tokens == 100


def test_fenced_json_is_accepted():
    client = StubClient(response("```json\n" + json.dumps(GOOD) + "\n```"))
    assert run(client)[1].edits[0].rule_id == "law-venue"


def test_invalid_output_is_retried_once_with_the_error():
    bad = {"edits": [{"paragraph_id": "p0013", "rule_id": "law-venue", "find": "Texas"}]}
    client = StubClient(response(json.dumps(bad)), response(json.dumps(GOOD)))
    _, result = run(client)
    assert len(result.edits) == 1
    assert len(client.requests) == 2
    retry = client.requests[1]["messages"]
    assert [m["role"] for m in retry] == ["user", "assistant", "user"]
    assert "did not validate" in retry[2]["content"] and "replace" in retry[2]["content"]


def test_two_invalid_outputs_raise():
    client = StubClient(response("not json"), response('{"edits": "nope"}'))
    with pytest.raises(ProviderError, match="failed validation twice"):
        run(client)
    assert len(client.requests) == 2


def test_refusal_raises():
    with pytest.raises(ProviderError, match="declined"):
        run(StubClient(response("", stop_reason="refusal")))


def test_client_uses_explicit_base_url_and_env_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "http://elsewhere.invalid")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "placeholder-for-test")
    client = make_client()
    assert str(client.base_url).rstrip("/") == BASE_URL


def test_missing_key_and_model_are_reported(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("REDLINE_MODEL", raising=False)
    with pytest.raises(ProviderError, match="REDLINE_MODEL"):
        AnthropicProvider(client=StubClient())
    with pytest.raises(ProviderError, match="ANTHROPIC_API_KEY"):
        make_client()
