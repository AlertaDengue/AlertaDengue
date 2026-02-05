from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import pandas as pd


class DataChunk(Protocol):
    chunk_id: int
    row_start: int
    df: pd.DataFrame


@dataclass(frozen=True, slots=True)
class Chunk:
    chunk_id: int
    row_start: int
    df: pd.DataFrame


@dataclass(frozen=True)
class MergeCounts:
    inserted: int
    updated: int
