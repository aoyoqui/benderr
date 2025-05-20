from dataclasses import field
from datetime import datetime
from enum import StrEnum
from typing import Annotated, Any, Literal, Union

from pydantic import Field
from pydantic.dataclasses import dataclass


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

class Verdict(StrEnum):
    UNDEFINED = "undefined"
    PASSED = "passed"
    FAILED = "failed"
    ABORTED = "aborted"

class SpecType(StrEnum):
    NONE = "none"
    NUMERIC = "numeric"
    STRING = "string"
    BOOLEAN = "boolean"

@dataclass
class NoSpec:
    name: str
    action: NoSpecAction
    type: Literal[SpecType.NONE] = SpecType.NONE

@dataclass
class BooleanSpec:
    name: str
    pass_if_true: bool
    type: Literal[SpecType.BOOLEAN] = SpecType.BOOLEAN
   

@dataclass
class NumericSpec:
    name: str
    comparator: NumericComparator
    lower: float | None = None
    upper: float | None = None
    units: str = ""
    type: Literal[SpecType.NUMERIC] = SpecType.NUMERIC

@dataclass
class StringSpec:
    expected_value: str
    case_sensitive: bool
    type: Literal[SpecType.STRING] = SpecType.STRING

Spec = Annotated[
    Union[NoSpec, NumericSpec, StringSpec, BooleanSpec],
    Field(discriminator="type")
]

@dataclass
class Measurement:
    value: Any
    passed: bool
    spec: Spec

@dataclass
class Step:
    id: int
    name: str
    specs: list[Spec] = field(default_factory=list)

@dataclass
class StepResult:
    id: int
    name: str
    start_time: datetime | None = None
    end_time: datetime | None = None
    verdict: Verdict = Verdict.UNDEFINED
    results: list[Measurement] = field(default_factory=list)

class StepCountError(Exception):
    pass

class SpecMismatch(Exception):
    pass    
