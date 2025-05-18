from typing import Any
from dataclasses import dataclass

from enum import StrEnum

class NoSpecAction(StrEnum):
    LOG = "log"
    IGNORE = "ignore"

class NumericComparator(StrEnum):
    GT = ">"
    GE = ">="
    LT = "<"
    LE = "<="
    EQ = "=="
    GTLT = "> <"
    GELT = ">= <"
    GTLE = "> <="
    GELE = ">= <="
    LTGT = "< >"
    LTGE = "< >="
    LEGT = "<= >"
    LEGE = "<= >="

@dataclass
class NoSpec:
    action: NoSpecAction

@dataclass
class NumericSpec:
    comparator: NumericComparator
    lower: float | None = None
    upper: float | None = None
    units: str = ""

@dataclass
class StringSpec:
    expected_value: str
    case_sensitive: bool

@dataclass
class Spec:
    name: str
    spec: NoSpec | NumericSpec | StringSpec

@dataclass
class Measurement:
    value: Any
    passed: bool
    spec: Spec

@dataclass
class Step:
    id: int
    name: str
    specs: list[Spec] = None

@dataclass
class StepResult:
    id: int
    name: str
    results: list[Measurement] = None
