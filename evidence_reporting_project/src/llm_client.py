from __future__ import annotations

import json
import time

import requests

from .io_utils import get_env_value
from .report_utils import parse_json_candidate


class DeepSeekLLMClient:
    def __init__(self, model: str = "deepseek-chat", max_retries: int = 3):
        self.model = model
        self.max_retries = max_retries
        self.api_key = get_env_value("DEEPSEEK_API_KEY")
        self.base_url = get_env_value("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1/chat/completions")
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY is not configured.")

    def generate(self, prompt: str) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        last_error = None
        for attempt in range(1, self.max_retries + 1):
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "You are a conservative reporting assistant for activated sludge operation. Return a single valid JSON object only."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.2,
                "response_format": {"type": "json_object"},
            }
            try:
                response = requests.post(self.base_url, headers=headers, data=json.dumps(payload), timeout=120)
                response.raise_for_status()
                body = response.json()
                content = body["choices"][0]["message"]["content"]
                # Validate JSON early so retry can recover malformed responses.
                parse_json_candidate(content)
                return content
            except Exception as exc:
                last_error = exc
                if attempt < self.max_retries:
                    time.sleep(2 * attempt)
                else:
                    raise
        raise last_error  # pragma: no cover
