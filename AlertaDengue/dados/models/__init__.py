"""Canonical ORM adapters for retained database objects."""

from .dengue_global import (
    CID10,
    City,
    MacroRegion,
    Parameter,
    ParameterUF,
    Regional,
    State,
)
from .episcanner import EpiscannerSirParams
from .municipio import (
    LegacyHistoricalAlertChikungunya,
    LegacyHistoricalAlertDengue,
    LegacyHistoricalAlertZika,
    Notification,
)

__all__ = [
    "CID10",
    "City",
    "EpiscannerSirParams",
    "LegacyHistoricalAlertChikungunya",
    "LegacyHistoricalAlertDengue",
    "LegacyHistoricalAlertZika",
    "MacroRegion",
    "Notification",
    "Parameter",
    "ParameterUF",
    "Regional",
    "State",
]
