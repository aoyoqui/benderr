import logging
import numbers
import tempfile
from abc import ABC
from datetime import datetime
from functools import wraps
from itertools import count
from pathlib import Path

from br_sdk.br_types import (
    BooleanSpec,
    Measurement,
    NoSpec,
    NoSpecAction,
    NumericComparator,
    NumericSpec,
    SequenceResult,
    SpecMismatch,
    Step,
    StepCountError,
    StepFailure,
    StepResult,
    StepsConfigError,
    StringSpec,
    Verdict,
)
from br_sdk.config import AppConfig
from br_sdk.events import ensure_event_server, publish_step_ended, publish_step_started
from br_sdk.report import ReportFormatter


class Sequence(ABC):
    _step_order = count()

    def __init__(
        self,
        steps: list[Step],
        report_formatter: ReportFormatter | None = None,
        sequence_config: dict | None = None,
    ):
        self.logger = logging.getLogger("benderr")
        self.report_formatter = report_formatter
        self._log_path = None
        self.steps = list(steps)
        self.step_results = []
        self.sequence_config = sequence_config or {}
        self._stop_at_step_fail = self.sequence_config.get("stop_at_step_fail", True)
        self._registered_steps = self._collect_step_methods()
        self.validate_steps(self.steps)

    def run(self):
        ensure_event_server()
        self.start_time = datetime.now()
        self.step_results = []
        self._config_index = 0
        self._stop_at_step_fail = self.sequence_config.get("stop_at_step_fail", True)
        if AppConfig.get("log_to_file", False):
            self._log_path = self._reset_log_file()
        else:
            self._log_path = None
        run_exception: Exception | None = None
        try:
            for step in self._registered_steps:
                try:
                    step["method"]()
                except Exception as exc:
                    run_exception = exc
                    break
        finally:
            if AppConfig.get("report_enabled", False) and self.report_formatter:
                self._write_report()
        if run_exception:
            raise run_exception

    @staticmethod
    def step(step_name: str):
        if not isinstance(step_name, str) or not step_name.strip():
            raise ValueError("Step name must be a non-empty string")

        def decorator(fn):
            if not callable(fn):
                raise TypeError("@Sequence.step can only decorate callables")
            if not fn.__name__.startswith("test_"):
                raise ValueError("@Sequence.step methods must be named with a 'test_' prefix")
            order = next(Sequence._step_order)

            @wraps(fn)
            def wrapper(self, *args, **kwargs):
                return self._run_registered_step(fn, step_name, *args, **kwargs)

            wrapper.__sequence_step__ = {"name": step_name, "order": order, "method_name": fn.__name__}
            return wrapper

        return decorator

    def _reset_log_file(self):
        logger = logging.getLogger("benderr")
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
        if specs is None or len(specs) == 0:
            step_result.verdict = Verdict.PASSED
        else:
            contains_nospec = any(isinstance(spec, NoSpec) for spec in specs)
            if contains_nospec and not all(isinstance(spec, NoSpec) for spec in specs):
                raise SpecMismatch("NoSpec entries cannot be mixed with other spec types in the same step")
            if contains_nospec:
                step_result = self._test_no_spec(result, specs, step_result)
            elif isinstance(result, bool):
                step_result = self._test_boolean(result, specs, step_result)
            elif isinstance(result, numbers.Number):
                step_result = self._test_numeric(result, specs, step_result)
            elif isinstance(result, str):
                step_result = self._test_string(result, specs, step_result)
            elif isinstance(result, (list, tuple)):
                step_result = self._test_iterable(result, specs, step_result)
            else:
                pass
        return step_result

    @staticmethod
    def _normalize_measurement_value(value):
        if isinstance(value, (bool, numbers.Number, str)) or value is None:
            return value
        return str(value)

    def _test_no_spec(self, result, specs, step_result: StepResult):
        normalized_value = self._normalize_measurement_value(result)
        for spec in specs:
            match spec.action:
                case NoSpecAction.LOG:
                    step_result.results.append(Measurement(normalized_value, True, spec))
                    self.logger.info("NoSpec log for step '%s': %s", step_result.name, normalized_value)
                case NoSpecAction.IGNORE:
                    self.logger.debug("NoSpec ignore for step '%s'", step_result.name)
                case _:
                    raise ValueError(f"Unsupported NoSpec action: {spec.action}")
        step_result.verdict = Verdict.PASSED
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

    @staticmethod
    def _test_string(result: str, specs, step_result: StepResult):
        if len(specs) != 1:
            raise SpecMismatch(
                f"Result is a single string but spec count ({len(specs)}) is not exactly one: {specs}"
            )
        spec = specs[0]
        if not isinstance(spec, StringSpec):
            raise SpecMismatch(f"Result is a string but spec does not define a string check: {spec}")
        if spec.case_sensitive:
            passed = result == spec.expected
        else:
            passed = result.lower() == spec.expected.lower()
        step_result.verdict = Verdict.PASSED if passed else Verdict.FAILED
        step_result.results.append(Measurement(result, passed, spec))
        return step_result

    def _test_iterable(self, result_seq, specs, step_result: StepResult):
        result_list = list(result_seq)
        if len(result_list) != len(specs):
            raise SpecMismatch(
                f"Result sequence length ({len(result_list)}) does not match specs count ({len(specs)})"
            )
        verdict = Verdict.PASSED
        for value, spec in zip(result_list, specs, strict=True):
            if isinstance(value, bool):
                if not isinstance(spec, BooleanSpec):
                    raise SpecMismatch(
                        f"Boolean result encountered but spec does not define a boolean check: {spec}"
                    )
                passed = Sequence._boolean_spec_passes(value, spec)
            elif isinstance(value, numbers.Number):
                if not isinstance(spec, NumericSpec):
                    raise SpecMismatch(
                        f"Numeric result encountered but spec does not define a numeric test: {spec}"
                    )
                passed = Sequence._numeric_test_passes(value, spec)
            elif isinstance(value, str):
                if not isinstance(spec, StringSpec):
                    raise SpecMismatch(
                        f"String result encountered but spec does not define a string check: {spec}"
                    )
                if spec.case_sensitive:
                    passed = value == spec.expected
                else:
                    passed = value.lower() == spec.expected.lower()
            else:
                raise SpecMismatch(
                    f"Unsupported result type '{type(value).__name__}' in sequence; "
                    "only bool, numeric, and string supported"
                )
            step_result.results.append(Measurement(value, passed, spec))
            if not passed:
                verdict = Verdict.FAILED
        step_result.verdict = verdict
        return step_result

    def validate_steps(self, config_steps: list[Step]):
        registered = self._registered_steps
        if len(registered) != len(config_steps):
            raise StepCountError(
                f"Executable steps count ({len(registered)}) do not match configured steps count({len(config_steps)}!)"
            )
        for index, step in enumerate(config_steps):
            if registered[index]["config_name"] != step.name:
                raise StepsConfigError(
                    f"Declared step with name {registered[index]['config_name']} differs from config {step.name}"
                )

    def _collect_step_methods(self):
        steps = []
        for attr_name in dir(self):
            if not attr_name.startswith("test_"):
                continue
            bound = getattr(self, attr_name)
            if not callable(bound):
                continue
            func = getattr(bound, "__func__", None)
            if func is None:
                continue
            metadata = getattr(func, "__sequence_step__", None)
            if metadata is None:
                raise StepsConfigError(
                    f"Method {attr_name} must be decorated with @Sequence.step to be executed"
                )
            steps.append(
                {
                    "order": metadata["order"],
                    "config_name": metadata["name"],
                    "method": bound,
                    "method_name": metadata.get("method_name", attr_name),
                }
            )
        steps.sort(key=lambda entry: entry["order"])
        return steps

    def _next_config_step(self, expected_name: str) -> Step:
        if self._config_index >= len(self.steps):
            raise StepCountError(
                f"Executable steps count ({self._config_index + 1}) exceed configured steps count({len(self.steps)}!)"
            )
        config_step = self.steps[self._config_index]
        self._config_index += 1
        if config_step.name != expected_name:
            raise StepsConfigError(
                f"Declared step with name {expected_name} differs from config {config_step.name}"
            )
        return config_step

    def _run_registered_step(self, func, expected_step_name: str, *args, **kwargs):
        config_step = self._next_config_step(expected_step_name)
        publish_step_started(config_step)
        self.logger.info(f"Start step: {config_step.name}")
        self.logger.info(f"Step config/specs: {config_step}")
        step_result = StepResult(config_step.id, config_step.name, datetime.now())
        exception_to_raise: Exception | None = None
        result = None
        try:
            result = Sequence._execute(func, self, *args, **kwargs)
            step_result = self._test(result, step_result, config_step.specs)
        except Exception as exc:
            self.logger.exception("Unexpected error during sequence execution")
            step_result.verdict = Verdict.ABORTED
            exception_to_raise = exc
        finally:
            step_result.end_time = datetime.now()
            self.logger.info(f"Result from step {config_step.name}: {step_result}")
            self.logger.info(f"End step: {config_step.name}")
            self.step_results.append(step_result)
            publish_step_ended(step_result)
        if exception_to_raise:
            if isinstance(exception_to_raise, SpecMismatch):
                raise exception_to_raise
            if config_step.ignore_fail:
                self.logger.warning(
                    "Ignoring failure for step '%s' due to ignore_fail=True",
                    config_step.name,
                )
            elif self._stop_at_step_fail:
                raise exception_to_raise
            else:
                self.logger.warning(
                    "Continuing after failure for step '%s' because stop_at_step_fail is False",
                    config_step.name,
                )
        elif step_result.verdict == Verdict.FAILED:
            if config_step.ignore_fail:
                self.logger.warning(
                    "Step '%s' failed but will be ignored due to ignore_fail=True",
                    config_step.name,
                )
            elif self._stop_at_step_fail:
                raise StepFailure(step_result)
        return result
