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

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union


@dataclass
class InternalCreateSurfaceOp:
    surface_id: str
    catalog_id: Optional[str] = None
    theme: Optional[Any] = None
    send_data_model: bool = False
    components: Optional[List[Dict[str, Any]]] = None
    data_model: Optional[Dict[str, Any]] = None
    type: str = "createSurface"


@dataclass
class InternalUpdateComponentsOp:
    surface_id: str
    components: List[Dict[str, Any]] = field(default_factory=list)
    type: str = "updateComponents"


@dataclass
class InternalUpdateDataModelOp:
    surface_id: str
    value: Any = None
    path: Optional[str] = "/"
    type: str = "updateDataModel"


@dataclass
class InternalDeleteSurfaceOp:
    surface_id: str
    type: str = "deleteSurface"


InternalOperation = Union[
    InternalCreateSurfaceOp,
    InternalUpdateComponentsOp,
    InternalUpdateDataModelOp,
    InternalDeleteSurfaceOp,
]
