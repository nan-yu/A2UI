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

from typing import Any, Dict, List
from .base import VersionAdapter
from ...schema import A2uiProtocolVersion
from ..operations import (
    InternalCreateSurfaceOp,
    InternalDeleteSurfaceOp,
    InternalOperation,
    InternalUpdateComponentsOp,
    InternalUpdateDataModelOp,
)
from ...exceptions import A2uiValidationError


class V0_9VersionAdapter(VersionAdapter):
    """Protocol version adapter for specification v0.9."""

    @property
    def version(self) -> A2uiProtocolVersion:
        return A2uiProtocolVersion.V0_9

    def extract_operations(self, payload: Any) -> List[InternalOperation]:
        if not payload:
            return []
        if isinstance(payload, list):
            ops: List[InternalOperation] = []
            for item in payload:
                ops.extend(self.extract_operations(item))
            return ops
        if (
            isinstance(payload, dict)
            and "messages" in payload
            and isinstance(payload["messages"], list)
        ):
            return self.extract_operations(payload["messages"])
        if not isinstance(payload, dict):
            return []

        message = payload
        update_types = [
            k
            for k in (
                "createSurface",
                "updateComponents",
                "updateDataModel",
                "deleteSurface",
            )
            if k in message
        ]
        if not update_types:
            raise A2uiValidationError(
                "A2UI Protocol message must contain exactly one update action: "
                "createSurface, updateComponents, updateDataModel, or deleteSurface."
            )
        if len(update_types) > 1:
            raise ValueError(
                f"Message contains multiple conflicting update actions: {update_types}"
            )

        res: List[InternalOperation] = []
        if "createSurface" in message:
            cs = message["createSurface"]
            res.append(
                InternalCreateSurfaceOp(
                    surface_id=str(cs.get("surfaceId", "")),
                    catalog_id=cs.get("catalogId"),
                    theme=cs.get("theme"),
                    send_data_model=bool(cs.get("sendDataModel", False)),
                    components=cs.get("components"),
                    data_model=cs.get("dataModel"),
                )
            )
        elif "updateComponents" in message:
            uc = message["updateComponents"]
            res.append(
                InternalUpdateComponentsOp(
                    surface_id=str(uc.get("surfaceId", "")),
                    components=uc.get("components", []),
                )
            )
        elif "updateDataModel" in message:
            ud = message["updateDataModel"]
            res.append(
                InternalUpdateDataModelOp(
                    surface_id=str(ud.get("surfaceId", "")),
                    path=ud.get("path", "/"),
                    value=ud.get("value"),
                )
            )
        elif "deleteSurface" in message:
            ds = message["deleteSurface"]
            res.append(
                InternalDeleteSurfaceOp(
                    surface_id=str(ds.get("surfaceId", "")),
                )
            )
        return res
