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

from typing import Any, Optional, Union
from ..catalog import Catalog
from ..schema import A2uiProtocolVersion
from .expression_parser import ExpressionParser, Scanner
from .locale_config import (
    LocaleFormattingRules,
    register_locale_rules,
    get_locale_rules,
    CURRENCY_SYMBOLS,
)
from . import v0_8
from . import v0_9
from . import v1_0
from .v0_9 import *


def get_basic_catalog(
    version: Union[str, A2uiProtocolVersion] = "v1.0",
    locale: Optional[str] = None,
) -> Catalog[Any, Any]:
    """Factory function returning the BasicCatalog for a specified protocol version."""
    ver_str = (
        version.value if isinstance(version, A2uiProtocolVersion) else str(version)
    )
    ver_str = ver_str.strip().replace(".", "_")
    if not ver_str.startswith("v"):
        ver_str = f"v{ver_str}"

    if ver_str == "v0_8":
        return v0_8.BasicCatalog(locale=locale)
    elif ver_str in ("v0_9", "v0_9_1"):
        return v0_9.BasicCatalog(locale=locale)
    elif ver_str in ("v1_0", "v1"):
        return v1_0.BasicCatalog(locale=locale)
    else:
        raise ValueError(f"Unsupported basic catalog version: {version}")


__all__ = [
    "ExpressionParser",
    "Scanner",
    "LocaleFormattingRules",
    "register_locale_rules",
    "get_locale_rules",
    "CURRENCY_SYMBOLS",
    "v0_8",
    "v0_9",
    "v1_0",
    "BasicCatalog",
    "get_basic_catalog",
]
