from dataclasses import field
from datetime import datetime
from enum import StrEnum
from typing import Annotated, Any, Literal, Union

from pydantic import Field, model_validator
from pydantic.dataclasses import dataclass


class NoSpecAction(StrEnum):
    LOG = "log"
    IGNORE = "ignore"


class NumericComparator(StrEnum):
    GT = "GT"
    GE = "GE"
    LT = "LT"
    LE = "LE"
    EQ = "EQ"
    NEQ = "NEQ"
    GTLT = "GTLT"
    GELT = "GELT"
    GTLE = "GTLE"
    GELE = "GELE"
    LTGT = "LTGT"
    LTGE = "LTGE"
    LEGT = "LEGT"
    LEGE = "LEGE"


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

    @model_validator(mode="after")
    def check_limits(self):
        match self.comparator:
            case NumericComparator.GT | NumericComparator.GE | NumericComparator.EQ | NumericComparator.NEQ:
                if self.lower is None:
                    raise ValueError(f"Comparator {self.comparator} requires a lower limit to be set")
            case NumericComparator.LT | NumericComparator.LE:
                if self.upper is None:
                    raise ValueError(f"Comparator {self.comparator} requires an upper limit to be set")
            case (
                NumericComparator.GTLT
                | NumericComparator.GELT
                | NumericComparator.GTLE
                | NumericComparator.GELE
                | NumericComparator.LTGT
                | NumericComparator.LTGE
                | NumericComparator.LEGT
                | NumericComparator.LEGE
            ):
                if self.lower is None or self.upper is None:
                    raise ValueError(f"Comparator {self.comparator} requires a lower and upper limit to be set")
        if self.upper is not None and self.lower is not None and self.upper < self.lower:
            raise ValueError("Upper limit should be greater or equal to lower limit")
        return self


@dataclass
class StringSpec:
    name: str
    expected: str
    case_sensitive: bool = True
    type: Literal[SpecType.STRING] = SpecType.STRING


Spec = Annotated[Union[NoSpec, NumericSpec, StringSpec, BooleanSpec], Field(discriminator="type")]


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


@dataclass
class SequenceResult:
    start_time: datetime | None = None
    end_time: datetime | None = None
    log_file: str | None = None
    verdict: Verdict = Verdict.UNDEFINED
    step_results: list[StepResult] = field(default_factory=list)
    

class StepCountError(Exception):
    pass


class SpecMismatch(Exception):
    pass


class InvalidSpec(Exception):
    pass


class StepsConfigError(Exception):
    pass
