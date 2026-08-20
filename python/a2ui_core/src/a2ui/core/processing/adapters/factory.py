# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from typing import Any, Dict, Union
from .base import VersionAdapter
from .v0_8 import V0_8VersionAdapter
from .v0_9 import V0_9VersionAdapter
from .v1_0 import V1_0VersionAdapter
from ...exceptions import A2uiValidationError
from ...schema import A2uiProtocolVersion


class VersionAdapterFactory:
    """Resolves version adapters for protocol specification versions."""

    _adapters: Dict[str, VersionAdapter] = {
        "v0.8": V0_8VersionAdapter(),
        "v0.9": V0_9VersionAdapter(),
        "v0.9.1": V0_9VersionAdapter(),
        "v1.0": V1_0VersionAdapter(),
    }

    @classmethod
    def register_adapter(cls, adapter: VersionAdapter) -> None:
        """Dynamically registers a version adapter."""
        key = (
            adapter.version.value
            if isinstance(adapter.version, A2uiProtocolVersion)
            else str(adapter.version)
        )
        cls._adapters[key] = adapter

    @classmethod
    def get_adapter(cls, version: Union[str, A2uiProtocolVersion]) -> VersionAdapter:
        """Resolves the version adapter for the specified version string."""
        ver_str = (
            version.value if isinstance(version, A2uiProtocolVersion) else str(version)
        )
        if not ver_str.startswith("v"):
            ver_str = f"v{ver_str}"
        adapter = cls._adapters.get(ver_str)
        if not adapter:
            supported = ", ".join(cls._adapters.keys())
            raise A2uiValidationError(
                f"[VersionAdapterFactory] Unsupported protocol version '{version}'."
                f" Supported versions: {supported}."
            )
        return adapter

    @classmethod
    def resolve_from_payload(cls, payload: Any) -> VersionAdapter:
        """Resolves the version adapter directly from an incoming message payload."""
        item = payload[0] if isinstance(payload, list) and payload else payload
        if isinstance(item, dict):
            if "messages" in item and isinstance(item["messages"], list):
                return cls.resolve_from_payload(item["messages"])
            if "version" in item and isinstance(item["version"], str):
                return cls.get_adapter(item["version"])
        # Default fallback to v0.9 for legacy payloads lacking explicit version header
        return cls.get_adapter("v0.9")
