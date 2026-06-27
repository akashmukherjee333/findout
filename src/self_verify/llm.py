"""LLM client abstraction — OpenAI-compatible."""

from typing import Optional
import httpx


class LLMClient:
    """Thin wrapper around any OpenAI-compatible API endpoint."""

    def __init__(
        self,
        model: str,
        base_url: str = "http://localhost:11434/v1",
        api_key: str = "ollama",
        max_tokens: int = 4096,
        timeout: int = 120,
    ):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.max_tokens = max_tokens
        self.timeout = timeout

    def generate(
        self,
        system: str,
        prompt: str,
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Send a chat completion request and return the response text.

        Raises:
            ConnectionError: Endpoint unreachable.
            ValueError: Bad response format.
            RuntimeError: HTTP/server error.
        """
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens or self.max_tokens,
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"].strip()
        except httpx.ConnectError:
            raise ConnectionError(
                f"Cannot connect to {self.base_url} — is the model server running?"
            )
        except httpx.TimeoutException:
            raise ConnectionError(
                f"Request to {self.base_url} timed out after {self.timeout}s."
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise RuntimeError(f"Auth failed for {self.base_url} — check API key.")
            if e.response.status_code == 404:
                raise RuntimeError(
                    f"Model '{self.model}' not found on {self.base_url}."
                )
            raise RuntimeError(f"HTTP {e.response.status_code} from {self.base_url}.")
        except (KeyError, IndexError, ValueError) as e:
            raise ValueError(f"Unexpected API response format: {e}")

    async def agenerate(
        self,
        system: str,
        prompt: str,
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Async version of generate.

        Raises:
            ConnectionError: Endpoint unreachable.
            ValueError: Bad response format.
            RuntimeError: HTTP/server error.
        """
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens or self.max_tokens,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"].strip()
        except httpx.ConnectError:
            raise ConnectionError(
                f"Cannot connect to {self.base_url} — is the model server running?"
            )
        except httpx.TimeoutException:
            raise ConnectionError(
                f"Request to {self.base_url} timed out after {self.timeout}s."
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise RuntimeError(f"Auth failed for {self.base_url} — check API key.")
            if e.response.status_code == 404:
                raise RuntimeError(
                    f"Model '{self.model}' not found on {self.base_url}."
                )
            raise RuntimeError(f"HTTP {e.response.status_code} from {self.base_url}.")
        except (KeyError, IndexError, ValueError) as e:
            raise ValueError(f"Unexpected API response format: {e}")

    def generate_batch(
        self,
        system: str,
        prompt: str,
        n: int = 3,
        temperature: float = 0.7,
    ) -> list[str]:
        """Generate N responses with the same prompt (for consistency pipeline)."""
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
            "max_tokens": self.max_tokens,
            "n": n,
        }

        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return [
                choice["message"]["content"].strip()
                for choice in data["choices"]
            ]
