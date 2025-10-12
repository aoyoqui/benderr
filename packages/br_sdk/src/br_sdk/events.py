import atexit
import logging
import os
import queue
import threading
import time
from concurrent import futures
from datetime import datetime
from typing import Callable, Optional

import grpc

from br_sdk._grpc import events_pb2, events_pb2_grpc
from br_sdk.br_types import (
    BooleanSpec,
    Measurement,
    NumericComparator,
    NumericSpec,
    Step,
    StepResult,
    StringSpec,
    Verdict,
)
from br_sdk.config import AppConfig

LOGGER = logging.getLogger(__name__)

DEFAULT_EVENT_SOCKET = "/tmp/benderr_events.sock"


def _get_socket_path() -> str:
    return AppConfig.get("event_socket_path", DEFAULT_EVENT_SOCKET)


def get_event_address(start_server: bool = False) -> str:
    if start_server:
        return ensure_event_server().address
    return f"unix://{_get_socket_path()}"


class _EventStream(events_pb2_grpc.EventStreamServicer):
    def __init__(self):
        self._subscribers: list[queue.Queue[Optional[events_pb2.Event]]] = []
        self._lock = threading.Lock()

    def Subscribe(self, request, context):
        q: queue.Queue[Optional[events_pb2.Event]] = queue.Queue()
        with self._lock:
            self._subscribers.append(q)
        try:
            while True:
                event = q.get()
                if event is None:
                    break
                yield event
        except Exception:  # pragma: no cover - defensive
            LOGGER.exception("Event subscriber crashed")
        finally:
            with self._lock:
                if q in self._subscribers:
                    self._subscribers.remove(q)

    def broadcast(self, event: events_pb2.Event):
        with self._lock:
            subscribers = list(self._subscribers)
        for q in subscribers:
            q.put(event)

    def shutdown(self):
        with self._lock:
            subscribers = list(self._subscribers)
            self._subscribers.clear()
        for q in subscribers:
            q.put(None)


class EventServer:
    def __init__(self, socket_path: str):
        self._socket_path = socket_path
        self._address = f"unix://{socket_path}"
        self._servicer = _EventStream()
        self._server = grpc.server(futures.ThreadPoolExecutor(max_workers=8))
        events_pb2_grpc.add_EventStreamServicer_to_server(self._servicer, self._server)
        self._started = False
        self._lock = threading.Lock()

    @property
    def address(self) -> str:
        self.ensure_started()
        return self._address

    def ensure_started(self):
        with self._lock:
            if self._started:
                return
            if not self._socket_path.startswith("@") and os.path.exists(self._socket_path):
                os.remove(self._socket_path)
            self._server.add_insecure_port(self._address)
            self._server.start()
            self._started = True

    def stop(self):
        with self._lock:
            if not self._started:
                return
            self._servicer.shutdown()
            self._server.stop(0)
            self._started = False
            if (
                self._socket_path
                and not self._socket_path.startswith("@")
                and os.path.exists(self._socket_path)
            ):
                os.remove(self._socket_path)

    def publish_step_started(self, step: Step):
        self.ensure_started()
        event = events_pb2.Event(
            step_started=events_pb2.StepStartedEvent(step=_to_proto_step(step)),
        )
        self._servicer.broadcast(event)

    def publish_step_ended(self, result: StepResult):
        self.ensure_started()
        event = events_pb2.Event(
            step_ended=events_pb2.StepEndedEvent(result=_to_proto_step_result(result)),
        )
        self._servicer.broadcast(event)

    def publish_log(self, message: str, level: str):
        self.ensure_started()
        event = events_pb2.Event(
            log=events_pb2.LogEvent(message=message, level=level),
        )
        self._servicer.broadcast(event)


_SERVER_LOCK = threading.Lock()
_SERVER: Optional[EventServer] = None


def ensure_event_server() -> EventServer:
    global _SERVER
    with _SERVER_LOCK:
        if _SERVER is None:
            _SERVER = EventServer(_get_socket_path())
        _SERVER.ensure_started()
        return _SERVER


def shutdown_event_server():
    global _SERVER
    with _SERVER_LOCK:
        if _SERVER is None:
            return
        _SERVER.stop()
        _SERVER = None


def publish_step_started(step: Step):
    ensure_event_server().publish_step_started(step)


def publish_step_ended(result: StepResult):
    ensure_event_server().publish_step_ended(result)


def publish_log(message: str, level: str):
    ensure_event_server().publish_log(message, level)


class EventSubscriber:
    def __init__(
        self,
        on_step_started: Callable[[Step], None],
        on_step_ended: Callable[[StepResult], None],
        on_log: Callable[[str, str], None],
        *,
        start_server: bool = False,
        address: Optional[str] = None,
    ):
        self._on_step_started = on_step_started
        self._on_step_ended = on_step_ended
        self._on_log = on_log
        self._stop = threading.Event()
        self._channel: Optional[grpc.Channel] = None
        self._thread: Optional[threading.Thread] = None
        self._start_server = start_server
        self._address = address
        self._ready = threading.Event()

    def start(self):
        address = self._address or get_event_address(start_server=self._start_server)
        self._channel = grpc.insecure_channel(address)
        grpc.channel_ready_future(self._channel).add_done_callback(lambda _: self._ready.set())
        stub = events_pb2_grpc.EventStreamStub(self._channel)
        self._thread = threading.Thread(target=self._consume, args=(stub,), daemon=True)
        self._thread.start()

    def wait_until_ready(self, timeout: Optional[float] = None) -> bool:
        return self._ready.wait(timeout)

    def stop(self, grace_period: float = 0.0):
        if grace_period:
            time.sleep(grace_period)
        self._stop.set()
        if self._channel:
            self._channel.close()
        if self._thread:
            self._thread.join(timeout=1)
        self._ready.clear()

    def _consume(self, stub: events_pb2_grpc.EventStreamStub):
        while not self._stop.is_set():
            try:
                for event in stub.Subscribe(events_pb2.SubscribeRequest()):
                    if self._stop.is_set():
                        break
                    if event.HasField("step_started"):
                        self._on_step_started(_from_proto_step(event.step_started.step))
                    elif event.HasField("step_ended"):
                        self._on_step_ended(_from_proto_step_result(event.step_ended.result))
                    elif event.HasField("log"):
                        self._on_log(event.log.message, event.log.level)
            except grpc.RpcError as exc:
                if self._stop.is_set():
                    break
                if exc.code() == grpc.StatusCode.CANCELLED:
                    break
                LOGGER.debug("Event subscription retry after error: %s", exc)
                time.sleep(0.5)


atexit.register(shutdown_event_server)


def _to_proto_step(step: Step) -> events_pb2.Step:
    return events_pb2.Step(id=step.id, name=step.name)


def _to_proto_step_result(result: StepResult) -> events_pb2.StepResult:
    measurements = [_to_proto_measurement(m) for m in result.results]
    start_ms = int(result.start_time.timestamp() * 1000) if result.start_time else 0
    end_ms = int(result.end_time.timestamp() * 1000) if result.end_time else 0
    return events_pb2.StepResult(
        step=_to_proto_step(Step(result.id, result.name)),
        verdict=_to_proto_verdict(result.verdict),
        measurements=measurements,
        start_time_ms=start_ms,
        end_time_ms=end_ms,
    )


def _to_proto_measurement(measurement: Measurement) -> events_pb2.Measurement:
    spec_msg = _to_proto_spec(measurement.spec)
    return events_pb2.Measurement(
        spec=spec_msg,
        value=_measurement_value_to_str(measurement.value),
        passed=measurement.passed,
    )


def _measurement_value_to_str(value) -> str:
    if isinstance(value, (int, float, bool)):
        return str(value)
    return str(value)


def _to_proto_spec(spec) -> events_pb2.Spec:
    match spec.type:
        case "boolean":
            return events_pb2.Spec(
                type=spec.type,
                name=spec.name,
                pass_if_true=spec.pass_if_true,
            )
        case "numeric":
            has_lower = spec.lower is not None
            has_upper = spec.upper is not None
            return events_pb2.Spec(
                type=spec.type,
                name=spec.name,
                comparator=spec.comparator.value,
                lower=spec.lower if has_lower else 0.0,
                upper=spec.upper if has_upper else 0.0,
                units=spec.units,
                has_lower=has_lower,
                has_upper=has_upper,
            )
        case "string":
            return events_pb2.Spec(
                type=spec.type,
                name=spec.name,
                expected=spec.expected,
                case_sensitive=spec.case_sensitive,
                has_expected=True,
            )
        case _:
            raise ValueError(f"Unsupported spec type: {spec.type}")


def _from_proto_step(step: events_pb2.Step) -> Step:
    return Step(step.id, step.name, [])


def _from_proto_step_result(result: events_pb2.StepResult) -> StepResult:
    step = _from_proto_step(result.step)
    measurements = [_from_proto_measurement(m) for m in result.measurements]
    start_time = (
        datetime.fromtimestamp(result.start_time_ms / 1000) if result.start_time_ms else None
    )
    end_time = (
        datetime.fromtimestamp(result.end_time_ms / 1000) if result.end_time_ms else None
    )
    verdict = _from_proto_verdict(result.verdict)
    return StepResult(
        step.id,
        step.name,
        start_time=start_time,
        end_time=end_time,
        verdict=verdict,
        results=measurements,
    )


def _from_proto_measurement(measurement: events_pb2.Measurement) -> Measurement:
    spec = _from_proto_spec(measurement.spec)
    value: object = measurement.value
    if spec.type == "boolean":
        value = measurement.value.lower() == "true"
    elif spec.type == "numeric":
        try:
            value = float(measurement.value)
        except ValueError:
            value = measurement.value
    return Measurement(value=value, passed=measurement.passed, spec=spec)


def _from_proto_spec(spec: events_pb2.Spec):
    match spec.type:
        case "boolean":
            return BooleanSpec(name=spec.name, pass_if_true=spec.pass_if_true)
        case "numeric":
            lower = spec.lower if spec.has_lower else None
            upper = spec.upper if spec.has_upper else None
            comparator = NumericComparator(spec.comparator)
            return NumericSpec(
                name=spec.name,
                comparator=comparator,
                lower=lower,
                upper=upper,
                units=spec.units,
            )
        case "string":
            expected = spec.expected if spec.has_expected else ""
            return StringSpec(
                name=spec.name,
                expected=expected,
                case_sensitive=spec.case_sensitive,
            )
        case _:
            raise ValueError(f"Unsupported spec type: {spec.type}")


def _to_proto_verdict(verdict: Verdict) -> events_pb2.Verdict:
    mapping = {
        Verdict.PASSED: events_pb2.VERDICT_PASSED,
        Verdict.FAILED: events_pb2.VERDICT_FAILED,
        Verdict.ABORTED: events_pb2.VERDICT_ABORTED,
    }
    return mapping.get(verdict, events_pb2.VERDICT_UNSPECIFIED)


def _from_proto_verdict(verdict: events_pb2.Verdict) -> Verdict:
    mapping = {
        events_pb2.VERDICT_PASSED: Verdict.PASSED,
        events_pb2.VERDICT_FAILED: Verdict.FAILED,
        events_pb2.VERDICT_ABORTED: Verdict.ABORTED,
    }
    return mapping.get(verdict, Verdict.UNDEFINED)
