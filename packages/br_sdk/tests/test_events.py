import copy
import queue
import time
from datetime import datetime

import pytest
from br_sdk.br_types import (
    BooleanSpec,
    Measurement,
    NoSpec,
    NoSpecAction,
    Step,
    StepResult,
    Verdict,
)
from br_sdk.config import AppConfig
from br_sdk.events import (
    EventSubscriber,
    ensure_event_server,
    publish_log,
    publish_step_ended,
    publish_step_started,
    shutdown_event_server,
)


@pytest.fixture
def event_config(tmp_path):
    original_config = copy.deepcopy(AppConfig._config)
    original_loaded = AppConfig._loaded
    socket_path = tmp_path / "events.sock"
    AppConfig._config = {"event_socket_path": str(socket_path)}
    AppConfig._loaded = True
    shutdown_event_server()
    yield socket_path
    shutdown_event_server()
    AppConfig._config = original_config
    AppConfig._loaded = original_loaded


def test_event_roundtrip(event_config):
    received = queue.Queue()

    def on_started(step: Step):
        received.put(("started", step))

    def on_ended(result: StepResult):
        received.put(("ended", result))

    def on_log(message: str, level: str):
        received.put(("log", (message, level)))

    server = ensure_event_server()
    subscriber = EventSubscriber(
        on_step_started=on_started,
        on_step_ended=on_ended,
        on_log=on_log,
        address=server.address,
    )
    subscriber.start()
    assert subscriber.wait_until_ready(timeout=2.0)
    time.sleep(0.1)

    step = Step(1, "Example", [])
    publish_step_started(step)
    event_type, payload = received.get(timeout=2.0)
    assert event_type == "started"
    assert payload.id == step.id
    assert payload.name == step.name

    spec = BooleanSpec("flag", True)
    measurement = Measurement(True, True, spec)
    no_spec = NoSpec("log value", NoSpecAction.LOG)
    no_spec_measurement = Measurement("logged", True, no_spec)
    result = StepResult(
        step.id,
        step.name,
        start_time=datetime.now(),
        end_time=datetime.now(),
        verdict=Verdict.PASSED,
        results=[measurement, no_spec_measurement],
    )
    publish_step_ended(result)
    event_type, payload = received.get(timeout=2.0)
    assert event_type == "ended"
    assert payload.id == step.id
    assert payload.verdict == Verdict.PASSED
    assert payload.results[0].spec.name == "flag"
    assert payload.results[1].spec.name == "log value"
    assert payload.results[1].spec.action == NoSpecAction.LOG
    assert payload.results[1].value == "logged"

    publish_log("Hello", "INFO")
    event_type, payload = received.get(timeout=2.0)
    assert event_type == "log"
    assert payload[0] == "Hello"
    assert payload[1] == "INFO"

    subscriber.stop(grace_period=0.1)


def test_shutdown_removes_socket(event_config):
    ensure_event_server()
    socket_path = event_config

    # wait briefly for server to create socket file
    for _ in range(20):
        if socket_path.exists():
            break
        time.sleep(0.05)
    assert socket_path.exists()

    shutdown_event_server()
    assert not socket_path.exists()
