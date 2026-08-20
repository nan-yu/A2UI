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

from abc import ABC, abstractmethod
from typing import Any, List
from ..operations import InternalOperation
from ...schema import A2uiProtocolVersion, ProtocolVersion


class VersionAdapter(ABC):
    """Abstract base class for protocol version adapters."""

    @property
    @abstractmethod
    def version(self) -> A2uiProtocolVersion:
        """The protocol version handled by this adapter (e.g. A2uiProtocolVersion.V1_0)."""
        pass

    @abstractmethod
    def extract_operations(self, payload: Any) -> List[InternalOperation]:
        """Converts a raw message payload or payload list into canonical internal operations."""
        pass
