"""Read-only CCR data providers for IRIS Resolve.

The public competition demonstration uses SyntheticCCRProvider, which reads
local JSON fixtures. CCRAPIProvider is intentionally disabled until an
approved CCR API contract and read-only credentials are available.
"""

from __future__ import annotations

import json
import os
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Final


TEST_DATA_ROOT: Final[Path] = Path(
    os.getenv(
        "CCR_TEST_DATA_ROOT",
        "/opt/irisapp/test_data/ccr",
    )
)

VALID_CCR_ID: Final[re.Pattern[str]] = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$"
)

SUPPORTED_PROVIDERS: Final[set[str]] = {
    "synthetic",
    "api",
}


class CCRProviderError(RuntimeError):
    """Base error raised by a CCR provider."""


class CCRNotFoundError(CCRProviderError):
    """Raised when the requested CCR fixture or record does not exist."""


class CCRConfigurationError(CCRProviderError):
    """Raised when a CCR provider has not been configured correctly."""


class CCRDataError(CCRProviderError):
    """Raised when a CCR response contains invalid or unexpected data."""


class CCRProvider(ABC):
    """Read-only interface for retrieving CCR evidence."""

    provider_name: str

    @abstractmethod
    async def get_details(self, ccr_id: str) -> dict[str, Any]:
        """Return normalised read-only details for a CCR."""

    @abstractmethod
    async def get_transport_logs(
        self,
        ccr_id: str,
    ) -> list[dict[str, Any]]:
        """Return normalised read-only transport logs for a CCR."""


class SyntheticCCRProvider(CCRProvider):
    """Read CCR details and transport logs from local synthetic fixtures."""

    provider_name = "synthetic"

    def __init__(self, data_root: Path | None = None) -> None:
        self.data_root = data_root or TEST_DATA_ROOT

    async def get_details(self, ccr_id: str) -> dict[str, Any]:
        """Return synthetic CCR details from a JSON fixture."""

        safe_ccr_id = validate_ccr_id(ccr_id)
        path = self.data_root / f"{safe_ccr_id}-details.json"

        payload = self._read_json_object(path)
        payload_id = str(payload.get("ccr_id") or "").strip()

        if payload_id != safe_ccr_id:
            raise CCRDataError(
                "CCR details fixture identifier does not match "
                f"the requested CCR: {safe_ccr_id}"
            )

        return {
            "provider": self.provider_name,
            "read_only": True,
            "ccr_id": safe_ccr_id,
            "title": str(payload.get("title") or ""),
            "description": str(payload.get("description") or ""),
            "status": str(payload.get("status") or ""),
            "product": str(payload.get("product") or ""),
            "target_environment": str(
                payload.get("target_environment") or ""
            ),
            "created_at": payload.get("created_at"),
            "updated_at": payload.get("updated_at"),
            "item_sets": _normalise_item_sets(
                payload.get("item_sets")
            ),
            "source_reference": str(
                payload.get("source_reference")
                or f"{safe_ccr_id}-details"
            ),
        }

    async def get_transport_logs(
        self,
        ccr_id: str,
    ) -> list[dict[str, Any]]:
        """Return synthetic CCR transport logs from a JSON fixture."""

        safe_ccr_id = validate_ccr_id(ccr_id)
        path = self.data_root / f"{safe_ccr_id}-transport.json"

        payload = self._read_json(path)

        if isinstance(payload, dict):
            payload_id = str(payload.get("ccr_id") or "").strip()

            if payload_id and payload_id != safe_ccr_id:
                raise CCRDataError(
                    "CCR transport fixture identifier does not match "
                    f"the requested CCR: {safe_ccr_id}"
                )

            logs = payload.get("transport_logs", [])
        elif isinstance(payload, list):
            logs = payload
        else:
            raise CCRDataError(
                "CCR transport fixture must contain a JSON object or array."
            )

        if not isinstance(logs, list):
            raise CCRDataError(
                "The transport_logs field must contain a JSON array."
            )

        return [
            _normalise_transport_log(
                item,
                safe_ccr_id,
                index,
            )
            for index, item in enumerate(logs, start=1)
        ]

    @staticmethod
    def _read_json(path: Path) -> Any:
        """Read and parse one JSON fixture."""

        if not path.is_file():
            raise CCRNotFoundError(
                f"Synthetic CCR fixture was not found: {path.name}"
            )

        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise CCRDataError(
                f"Invalid JSON in CCR fixture {path.name}: {exc}"
            ) from exc
        except OSError as exc:
            raise CCRDataError(
                f"Unable to read CCR fixture {path.name}: {exc}"
            ) from exc

    def _read_json_object(self, path: Path) -> dict[str, Any]:
        """Read one fixture and require a JSON object."""

        payload = self._read_json(path)

        if not isinstance(payload, dict):
            raise CCRDataError(
                f"CCR fixture {path.name} must contain a JSON object."
            )

        return payload


class CCRAPIProvider(CCRProvider):
    """Placeholder for a future approved read-only CCR API integration.

    This provider deliberately performs no network calls. It must not be
    implemented until the CCR service owner supplies an approved endpoint,
    authentication mechanism, read-only scope, and response contract.
    """

    provider_name = "api"

    def __init__(self) -> None:
        self.base_url = os.getenv("CCR_API_BASE_URL", "").strip()
        self.api_key = os.getenv("CCR_API_KEY", "").strip()

    async def get_details(self, ccr_id: str) -> dict[str, Any]:
        validate_ccr_id(ccr_id)
        self._raise_not_configured()

    async def get_transport_logs(
        self,
        ccr_id: str,
    ) -> list[dict[str, Any]]:
        validate_ccr_id(ccr_id)
        self._raise_not_configured()

    def _raise_not_configured(self) -> None:
        raise CCRConfigurationError(
            "The live CCR API provider is disabled. Use "
            "CCR_PROVIDER=synthetic until an approved read-only CCR API "
            "contract, endpoint, authentication method, and response schema "
            "have been supplied by the CCR service owner."
        )


def get_ccr_provider(
    provider_name: str | None = None,
) -> CCRProvider:
    """Return the configured read-only CCR provider."""

    selected = (
        provider_name
        or os.getenv("CCR_PROVIDER", "synthetic")
    ).strip().lower()

    if selected not in SUPPORTED_PROVIDERS:
        supported = ", ".join(sorted(SUPPORTED_PROVIDERS))
        raise CCRConfigurationError(
            f"Unsupported CCR provider '{selected}'. "
            f"Supported providers: {supported}."
        )

    if selected == "synthetic":
        return SyntheticCCRProvider()

    return CCRAPIProvider()


def validate_ccr_id(ccr_id: str) -> str:
    """Validate a CCR identifier before using it in a file path or API."""

    if not isinstance(ccr_id, str):
        raise ValueError("CCR ID must be a string.")

    normalised = ccr_id.strip()

    if not normalised:
        raise ValueError("CCR ID must not be empty.")

    if not VALID_CCR_ID.fullmatch(normalised):
        raise ValueError(
            "CCR ID may contain only letters, numbers, periods, "
            "underscores, and hyphens, with a maximum length of "
            "100 characters."
        )

    return normalised


def _normalise_item_sets(value: Any) -> list[dict[str, Any]]:
    """Normalise the item-set section of a CCR details response."""

    if value is None:
        return []

    if not isinstance(value, list):
        raise CCRDataError("item_sets must contain a JSON array.")

    results: list[dict[str, Any]] = []

    for index, item in enumerate(value, start=1):
        if not isinstance(item, dict):
            raise CCRDataError(
                f"Item set {index} must contain a JSON object."
            )

        results.append(
            {
                "item_set_id": str(
                    item.get("item_set_id") or f"ITEM-{index:03d}"
                ),
                "name": str(item.get("name") or ""),
                "status": str(item.get("status") or ""),
                "target": str(item.get("target") or ""),
            }
        )

    return results


def _normalise_transport_log(
    item: Any,
    ccr_id: str,
    index: int,
) -> dict[str, Any]:
    """Normalise one read-only transport-log result."""

    if not isinstance(item, dict):
        raise CCRDataError(
            f"Transport log {index} must contain a JSON object."
        )

    return {
        "provider": "synthetic",
        "read_only": True,
        "ccr_id": ccr_id,
        "evidence_id": str(
            item.get("evidence_id")
            or f"{ccr_id}-LOG-{index:03d}"
        ),
        "timestamp": item.get("timestamp"),
        "level": str(item.get("level") or "INFO"),
        "status": str(item.get("status") or ""),
        "item_set_id": str(item.get("item_set_id") or ""),
        "message": str(item.get("message") or ""),
        "target_environment": str(
            item.get("target_environment") or ""
        ),
    }