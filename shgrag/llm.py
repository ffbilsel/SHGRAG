"""Thin Claude client with an on-disk response cache.

Both conditions (text-only and graph-assisted) go through `LLMClient.verdict`
with the same model, effort and output schema. Responses are cached by a hash
of (model, effort, system, prompt, run index) so experiments can be re-scored
without new API calls; different run indices give independent samples for the
repeatability test.

Note on sampling: Claude Opus 5.5 does not accept `temperature`; the model,
effort level, prompts and output schema are held fixed instead. If you switch
to a model that accepts sampling parameters, set `temperature` in LLMConfig.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .prompts import SYSTEM_PROMPT, Verdict

DEFAULT_MODEL = os.environ.get("SHGRAG_MODEL", "claude-opus-5-5")
DEFAULT_EFFORT = os.environ.get("SHGRAG_EFFORT", "medium")
DEFAULT_CACHE = Path(os.environ.get("SHGRAG_CACHE", Path(__file__).resolve().parent.parent / ".cache" / "llm"))


@dataclass
class LLMConfig:
    model: str = DEFAULT_MODEL
    effort: str = DEFAULT_EFFORT
    max_tokens: int = 16000
    temperature: float | None = None  # only for models that accept sampling params
    cache_dir: Path = DEFAULT_CACHE
    use_cache: bool = True


@dataclass
class LLMResult:
    verdict: Verdict | None
    error: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    latency_s: float = 0.0
    cached: bool = False
    meta: dict = field(default_factory=dict)


class LLMClient:
    def __init__(self, config: LLMConfig | None = None, client=None):
        self.config = config or LLMConfig()
        self._client = client  # injectable for tests
        self._locks: dict[str, threading.Lock] = {}
        self._locks_guard = threading.Lock()

    @property
    def client(self):
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic(max_retries=5)
        return self._client

    def _key(self, prompt: str, run: int) -> str:
        c = self.config
        blob = json.dumps(
            {"model": c.model, "effort": c.effort, "temperature": c.temperature, "system": SYSTEM_PROMPT, "prompt": prompt, "run": run},
            sort_keys=True,
        )
        return hashlib.sha256(blob.encode()).hexdigest()

    def _cache_path(self, key: str) -> Path:
        return Path(self.config.cache_dir) / f"{key}.json"

    def verdict(self, prompt: str, run: int = 0) -> LLMResult:
        key = self._key(prompt, run)
        # Identical prompts (e.g. a case with no AFFECTS edges in both graph
        # conditions) share one cache entry; serialise them so it is called once.
        with self._locks_guard:
            lock = self._locks.setdefault(key, threading.Lock())
        with lock:
            return self._verdict(prompt, run, key)

    def _verdict(self, prompt: str, run: int, key: str) -> LLMResult:
        path = self._cache_path(key)
        if self.config.use_cache and path.exists():
            data = json.loads(path.read_text())
            return LLMResult(
                verdict=Verdict.model_validate(data["verdict"]) if data.get("verdict") else None,
                error=data.get("error"),
                input_tokens=data.get("input_tokens", 0),
                output_tokens=data.get("output_tokens", 0),
                latency_s=data.get("latency_s", 0.0),
                cached=True,
            )

        result = self._call(prompt)
        # Transient failures (network, rate limit) are not cached; refusals and
        # schema failures are, because they are deterministic outcomes of the run.
        if self.config.use_cache and not (result.error or "").startswith("api_error"):
            path.parent.mkdir(parents=True, exist_ok=True)
            data = asdict(result)
            data["verdict"] = result.verdict.model_dump() if result.verdict else None
            tmp = path.with_suffix(f".{os.getpid()}.{threading.get_ident()}.tmp")
            tmp.write_text(json.dumps(data, indent=2))
            os.replace(tmp, path)  # atomic
        return result

    def _call(self, prompt: str) -> LLMResult:
        import anthropic

        c = self.config
        kwargs = dict(
            model=c.model,
            max_tokens=c.max_tokens,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
            output_config={"effort": c.effort},
            output_format=Verdict,
        )
        if c.temperature is not None:  # anthropic 1.x has no typed sampling params
            kwargs["extra_body"] = {"temperature": c.temperature}
        t0 = time.perf_counter()
        try:
            resp = self.client.messages.parse(**kwargs)
        except anthropic.BadRequestError as e:
            return LLMResult(None, error=f"bad_request: {e.message}", latency_s=time.perf_counter() - t0)
        except (anthropic.RateLimitError, anthropic.APIStatusError, anthropic.APIConnectionError) as e:
            return LLMResult(None, error=f"api_error: {type(e).__name__}: {e}", latency_s=time.perf_counter() - t0)
        latency = time.perf_counter() - t0
        usage = dict(input_tokens=resp.usage.input_tokens, output_tokens=resp.usage.output_tokens, latency_s=latency)
        if resp.stop_reason == "refusal":
            return LLMResult(None, error="refusal", **usage)
        if resp.stop_reason == "max_tokens":
            return LLMResult(None, error="max_tokens", **usage)
        if resp.parsed_output is None:
            return LLMResult(None, error="unparsed_output", **usage)
        return LLMResult(resp.parsed_output, **usage)
