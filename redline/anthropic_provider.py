import json
import os
import re
import time
from dataclasses import dataclass

import anthropic
from pydantic import ValidationError

from redline.parse import ParsedDocument
from redline.playbook import Playbook
from redline.prompt import SYSTEM, build_prompt
from redline.schema import ReviewResult

# Set explicitly: some environments export their own ANTHROPIC_BASE_URL.
BASE_URL = "https://api.anthropic.com"
MAX_TOKENS = 16000


class ProviderError(RuntimeError):
    pass


@dataclass
class CallRecord:
    input_tokens: int
    output_tokens: int
    seconds: float


def make_client() -> anthropic.Anthropic:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise ProviderError("ANTHROPIC_API_KEY is not set; put it in .env and run scripts/run_live.sh")
    return anthropic.Anthropic(api_key=key, base_url=BASE_URL)


def model_from_env() -> str:
    model = os.environ.get("REDLINE_MODEL")
    if not model:
        raise ProviderError("REDLINE_MODEL is not set; put it in .env")
    return model


def extract_json(text: str) -> str:
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.S)
    if fenced:
        return fenced.group(1)
    start, end = text.find("{"), text.rfind("}")
    return text[start:end + 1] if start != -1 and end > start else text


def parse_result(text: str) -> ReviewResult:
    return ReviewResult.model_validate(json.loads(extract_json(text)))


class AnthropicProvider:
    def __init__(self, client=None, model: str | None = None):
        self.model = model or model_from_env()
        self.client = client or make_client()
        self.calls: list[CallRecord] = []

    def _send(self, messages: list) -> object:
        started = time.monotonic()
        response = self.client.messages.create(
            model=self.model, max_tokens=MAX_TOKENS, system=SYSTEM, messages=messages,
        )
        self.calls.append(CallRecord(
            response.usage.input_tokens, response.usage.output_tokens, time.monotonic() - started,
        ))
        if response.stop_reason == "refusal":
            raise ProviderError("the model declined the request")
        if response.stop_reason == "max_tokens":
            raise ProviderError(f"response hit max_tokens ({MAX_TOKENS}) before finishing")
        return response

    def complete(self, prompt: str) -> ReviewResult:
        messages = [{"role": "user", "content": prompt}]
        response = self._send(messages)
        try:
            result = parse_result(text_of(response))
        except (json.JSONDecodeError, ValidationError) as first_error:
            messages += [
                {"role": "assistant", "content": response.content},
                {"role": "user", "content": (
                    "Your answer did not validate:\n"
                    f"{first_error}\n"
                    "Answer again with only the corrected JSON object."
                )},
            ]
            response = self._send(messages)
            try:
                result = parse_result(text_of(response))
            except (json.JSONDecodeError, ValidationError) as e:
                raise ProviderError(f"model output failed validation twice: {e}") from e
        result.model = self.model
        return result

    def review(self, document: ParsedDocument, playbook: Playbook) -> ReviewResult:
        return self.complete(build_prompt(document, playbook))


def text_of(response) -> str:
    return "".join(block.text for block in response.content if block.type == "text")
