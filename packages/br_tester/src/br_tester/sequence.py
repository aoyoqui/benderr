import ast
import inspect
import numbers
import textwrap
import tempfile
import logging
from pathlib import Path
from abc import ABC, abstractmethod
from datetime import datetime
from typing import get_origin, get_type_hints, get_args

from br_tester.br_types import (
    BooleanSpec,
    Measurement,
    NumericComparator,
    NumericSpec,
    SpecMismatch,
    Step,
    StepCountError,
    StepResult,
    Verdict,
    StepsConfigError,
    SequenceResult
)
from br_tester.events import step_ended, step_started
from br_tester.config import AppConfig
from br_tester.report import ReportFormatter

class Sequence(ABC):
    def __init__(self, steps: list[Step], report_formatter: ReportFormatter=None):
        self.logger = logging.getLogger("benderr")
        self.report_formatter = report_formatter
        self.validate_steps(steps)
        self.steps = steps
        self.step_results = []

    def run(self):
        self.start_time = datetime.now()
        if AppConfig.get("log_to_file", False):
            self._log_path = self._reset_log_file()
        """Call run to execute a sequence. Do not call sequence directly"""
        self.sequence()
        if AppConfig.get("report_enabled", False) and self.report_formatter:
            self._write_report()

    @abstractmethod
    def sequence(self):
        """
        Derive from this and implement the steps in this method, wrapping steps in the form:
            self.step(f, arg1, arg2, arg3, kwarg1, kwarg2)
        """
        pass

    def step(self, f, *args, **kwargs):
        config_step = self.steps.pop(0)
        step_started.send(self, step=config_step)
        self.logger.info(f"Start step: {config_step.name}")
        self.logger.info(f"Step config/specs: {config_step}")
        step_result = StepResult(config_step.id, config_step.name, datetime.now())
        try:
            kwargs.pop('step_name', None)
            result = Sequence._execute(f, *args, **kwargs)
            step_result = self._test(result, step_result, config_step.specs)
        except Exception:
            self.logger.error(f"Unexpected error during sequence execution")
            step_result.verdict = Verdict.ABORTED
            raise
        finally:
            step_result.end_time = datetime.now()
            self.logger.info(f"Result from step {config_step.name}: {step_result}")
            self.logger.info(f"End step: {config_step.name}")
            self.step_results.append(step_result)
            step_ended.send(self, result=step_result)
        return result

    def _reset_log_file(self):
        logger = logging.getLogger("myapp")
        for h in logger.handlers[:]:
            if isinstance(h, logging.FileHandler):
                logger.removeHandler(h)
                h.close()

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_dir = Path(AppConfig.get("output_dir", tempfile.gettempdir()))
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / f"{timestamp}_run.log"

        fh = logging.FileHandler(log_path)
        fh.setLevel(AppConfig.get("log_level_file", logging.DEBUG))
        fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(fh)

        return log_path

    def _write_report(self):
        verdict = Verdict.PASSED
        for step in self.step_results:
            if step.verdict != Verdict.PASSED:
                verdict = step.verdict
                break
        log_file = str(self._log_path) if self._log_path else ""
        now = datetime.now()
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        filename = timestamp + "_report" + self.report_formatter.ext
        report_path = Path(AppConfig.get("output_dir")) / filename
        report = SequenceResult(self.start_time, now, log_file, verdict, self.step_results)
        with open(report_path, "w") as f:
            f.write(self.report_formatter.format(report))


    def _execute(f, *args, **kwargs):
        if args is not None or kwargs is not None:
            result = f(*args, **kwargs)  # deal with exceptions
        else:
            result = f()
        return result

    def _test(self, result, step_result: StepResult, specs) -> StepResult:
        # How do we turn a list of Specs into a list of Measurement
        # First, we need to process the result in some way. What form can result have? WHat should we support??
        # Supported types:
        # - str - Spec supported StringSpec. len(specs) == 1. Take name from Spec
        # - dataclass - Convention to check for attribute name in dataclass and compare to that value
        #               using the other supported datatypes. len(specs) >= number of attributes
        #               Nested dataclasses not supported
        # - tuple/list - If tuples of primitive types, use name from Spec, use same order as provided. Use with care
        #                If tuples of dataclasses,
        if specs is None or len(specs) == 0:
            step_result.verdict = Verdict.PASSED
        elif isinstance(result, bool):
            step_result = self._test_boolean(result, specs, step_result)
        elif isinstance(result, numbers.Number):
            step_result = self._test_numeric(result, specs, step_result)
        else:
            pass
        return step_result

    @staticmethod
    def _test_boolean(result, specs, step_result: StepResult):
        if len(specs) > 1:
            raise SpecMismatch(
                f"Result is a single boolean but more than one spec for this result has been defined: {specs}"
            )
        spec = specs[0]
        if isinstance(spec, BooleanSpec):
            passed = Sequence._boolean_spec_passes(result, spec)
            step_result.verdict = Verdict.PASSED if passed else Verdict.FAILED
            step_result.results.append(Measurement(result, passed, spec))
        else:
            raise SpecMismatch(f"Result is a single boolean but spec does not define a boolean check: {spec}")
        return step_result

    @staticmethod
    def _boolean_spec_passes(result: bool, spec: BooleanSpec):
        return (spec.pass_if_true and result) or (not spec.pass_if_true and not result)

    @staticmethod
    def _test_numeric(result, specs, step_result: StepResult):
        if len(specs) > 1:
            raise SpecMismatch(
                f"Result is a single number but more than one spec for this result has been defined: {specs}"
            )
        spec = specs[0]
        if isinstance(spec, NumericSpec):
            passed = Sequence._numeric_test_passes(result, spec)
            step_result.verdict = Verdict.PASSED if passed else Verdict.FAILED
            step_result.results.append(Measurement(result, passed, spec))
        else:
            raise SpecMismatch(f"Result is a single number but spec does not define a numeric test: {spec}")
        return step_result

    @staticmethod
    def _numeric_test_passes(result: numbers.Number, spec: NumericSpec):
        match spec.comparator:
            case NumericComparator.GT:
                passed = result > spec.lower
            case NumericComparator.GE:
                passed = result >= spec.lower
            case NumericComparator.LT:
                passed = result < spec.upper
            case NumericComparator.LE:
                passed = result <= spec.upper
            case NumericComparator.EQ:
                passed = result == spec.lower
            case NumericComparator.NEQ:
                passed = result != spec.lower
            case NumericComparator.GTLT:
                passed = spec.lower < result < spec.upper
            case NumericComparator.GELT:
                passed = spec.lower <= result < spec.upper
            case NumericComparator.GTLE:
                passed = spec.lower < result <= spec.upper
            case NumericComparator.GELE:
                passed = spec.lower <= result <= spec.upper
            case NumericComparator.LTGT:
                passed = spec.lower > result or result > spec.upper
            case NumericComparator.LTGE:
                passed = spec.lower > result or result >= spec.upper
            case NumericComparator.LEGT:
                passed = spec.lower >= result or result > spec.upper
            case NumericComparator.LEGE:
                passed = spec.lower >= result or result >= spec.upper
            case _:
                raise ValueError(f"{spec.comparator} not handled")
        return passed

    @classmethod
    def declared_steps_with_return(cls) -> list[tuple[str, str]]:
        """
        Inspect the source of cls.sequence() and return a list of
        (step_name, return_type) as per our AST extractor logic.
        """
        # grab and dedent
        source = inspect.getsource(cls.sequence)
        source = textwrap.dedent(source)
        tree = ast.parse(source)

        # collect all step(...) calls
        calls: list[tuple[str | None, ast.expr | None]] = []

        class V(ast.NodeVisitor):
            def visit_Call(self, node: ast.Call):
                if (
                    isinstance(node.func, ast.Attribute)
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "self"
                    and node.func.attr == "step"
                ):
                    custom = next(
                        (
                            kw.value.value
                            for kw in node.keywords
                            if kw.arg == "step_name" and isinstance(kw.value, ast.Constant)
                        ),
                        None,
                    )
                    pos = node.args[0] if node.args else None
                    calls.append((custom, pos))
                self.generic_visit(node)

        V().visit(tree)

        results: list[tuple[str, str]] = []

        def is_numeric_val(v):
            return isinstance(v, numbers.Number) and not isinstance(v, bool)

        for custom, pos in calls:
            # 1) name
            if custom is not None:
                name = custom
            elif isinstance(pos, ast.Attribute):
                name = pos.attr
            elif isinstance(pos, ast.Name):
                name = pos.id
            elif isinstance(pos, ast.Lambda):
                name = "lambda"
            else:
                name = "none"

            # 2) return-type
            ret_type = "none"
            # Lambda literal inference
            if isinstance(pos, ast.Lambda):
                body = pos.body
                if isinstance(body, ast.Constant) and isinstance(body.value, bool):
                    ret_type = "bool"
                elif (isinstance(body, ast.Constant) and is_numeric_val(body.value)) or (
                    isinstance(body, ast.UnaryOp)
                    and isinstance(body.op, ast.USub)
                    and isinstance(body.operand, ast.Constant)
                    and is_numeric_val(body.operand.value)
                ):
                    ret_type = "numeric"
                elif isinstance(body, ast.Constant) and isinstance(body.value, str):
                    ret_type = "str"
            else:
                # Named method — use annotations
                fn_name = pos.attr if isinstance(pos, ast.Attribute) else pos.id if isinstance(pos, ast.Name) else None
                if fn_name:
                    fn = getattr(cls, fn_name, None)
                    if fn:
                        hints = get_type_hints(fn, include_extras=False)
                        ann = hints.get("return", None)

                        origin = get_origin(ann) or ann
                        if origin is tuple:
                            args = get_args(ann)
                            if args:
                                ret_type = f"tuple[{', '.join(a.__name__ for a in args)}]"
                            else:
                                ret_type = "tuple"
                        elif ann is bool:
                            ret_type = "bool"
                        elif ann and issubclass(ann, numbers.Number):
                            ret_type = "numeric"
                        elif ann is str:
                            ret_type = "str"
                        elif isinstance(ann, type):
                            ret_type = ann.__name__

            results.append((name, ret_type))

        return results

    def validate_steps(self, config_steps: list[Step]):
        self_steps = self.declared_steps_with_return()
        if len(self_steps) != len(config_steps):
            raise StepCountError(
                f"Executable steps count ({len(self_steps)}) do not match configured steps count({len(config_steps)}!)"
            )
        for i, step in enumerate(config_steps):
            if self_steps[i][0] != step.name :
                raise StepsConfigError(f"Declared step with name {self_steps[i][0]} differs from config {step.name}")
