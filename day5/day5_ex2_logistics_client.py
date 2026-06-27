from __future__ import annotations

import json
import time
import logging
from typing import Any, Callable, TypeVar
from functools import wraps

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)-8s] %(message)s",
    datefmt="%H:%M:%S",
)

log = logging.getLogger(__name__)
T = TypeVar("T")


class APIClientError(Exception):
    """Base error for API client failures."""

    def __init__(self, status_code: int, message: str, url: str) -> None:
        super().__init__(f"HTTP {status_code}: {message}")
        self.status_code = status_code
        self.url = url


class RateLimitError(APIClientError):
    """Raised on HTTP 429."""

    def __init__(self, url: str, retry_after: int) -> None:
        super().__init__(429, f"Rate limited, retry after {retry_after}s", url)
        self.retry_after = retry_after


_call_log: list[int] = []


def mock_http_get(url: str, headers: dict) -> tuple[int, str]:
    """
    Simulates an unreliable API.
    """

    if headers.get("X-API-Key") != "valid-test-key-123":
        return 401, json.dumps({"error": "Invalid API key"})

    _call_log.append(1)
    attempt = len(_call_log)

    if attempt == 1:
        return 500, json.dumps({"error": "Internal error"})
    elif attempt == 2:
        return 429, json.dumps({"error": "Rate limited", "retry_after": 1})
    else:
        shipment_id = url.rstrip("/").split("/")[-1]
        return (
            200,
            json.dumps(
                {
                    "shipment_id": shipment_id,
                    "carrier": "DHL",
                    "status": "in_transit",
                    "delay_days": 1,
                }
            ),
        )


def with_retry(max_attempts: int = 4, backoff_base: float = 2.0) -> Callable:
    def decorator(fn: Callable[..., T]) -> Callable[..., T]:

        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exc = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return fn(*args, **kwargs)

                except RateLimitError as e:
                    log.warning(
                        "Rate limited. Waiting %ds before retry.",
                        e.retry_after,
                    )
                    time.sleep(e.retry_after)
                    last_exc = e

                except APIClientError as e:
                    if e.status_code < 500:
                        raise

                    wait = backoff_base**attempt
                    log.warning(
                        "Server error %d. Retrying in %.1fs (attempt %d/%d)",
                        e.status_code,
                        wait,
                        attempt,
                        max_attempts,
                    )
                    time.sleep(wait)
                    last_exc = e

            raise last_exc

        return wrapper

    return decorator


class LogisticsAPIClient:
    """Authenticated, resilient client."""

    def __init__(self, base_url: str, api_key: str) -> None:
        self.base_url = base_url.rstrip("/")
        self._headers = {"X-API-Key": api_key}

    def _handle_response(self, url: str, status: int, body: str) -> dict:
        data = json.loads(body)

        if status == 200:
            return data

        if status == 429:
            raise RateLimitError(url, data["retry_after"])

        if status in (401, 403):
            raise APIClientError(status, data["error"], url)

        if status >= 500:
            raise APIClientError(status, data["error"], url)

        raise APIClientError(status, "Unexpected error", url)

    @with_retry(max_attempts=4, backoff_base=2.0)
    def get_shipment(self, shipment_id: str) -> dict:
        url = f"{self.base_url}/v1/shipments/{shipment_id}"
        status, body = mock_http_get(url, self._headers)
        return self._handle_response(url, status, body)


if __name__ == "__main__":
    client = LogisticsAPIClient(
        base_url="https://api.carrier-platform.in",
        api_key="valid-test-key-123",
    )

    print("=== Fetching SH-001 (will hit 500, then 429, then succeed) ===")
    result = client.get_shipment("SH-001")
    print(f"Final result: {result}")
    print()

    print("=== Testing invalid API key ===")

    bad_client = LogisticsAPIClient(
        base_url="https://api.carrier-platform.in",
        api_key="wrong-key",
    )

    try:
        bad_client.get_shipment("SH-002")
    except APIClientError as e:
        print(f"Expected failure (not retried): {e}")
