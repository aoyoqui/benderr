import random
from pathlib import Path

from br_hw.motor.motor import MotorDrive
from br_hw.motor.transport_mock import TransportMock
from br_sdk.br_logging import setup_logger
from br_sdk.config import AppConfig
from br_sdk.parse_steps import steps_from_file
from br_sdk.sequence import Sequence


class MotorTest(Sequence):
    def setup(self):
        connection_handler = TransportMock()
        self._any_drive = MotorDrive(connection_handler)
        if not self._any_drive.connect():
            raise RuntimeError("Could not connect")

    @Sequence.step("Read Identifier")
    def test_read_id(self):
        return self._any_drive.device_id()

    @Sequence.step("Read calibration values")
    def test_record_calibration_values(self):
        self.k = 0.5 # We can pass values to later steps using member variables
        return self.k

    @Sequence.step("Absolute position")
    def test_absolute_position(self):
        # These values should be a step config
        move_to = [0, 15, 30, 180, 180.01]
        # 1. Command the motor to move to angles
        # 2. Read the values from a precision rotary table
        # 3. Return values in angles
        return [pos + random.random()*0.001 for pos in move_to]

    def cleanup(self):
        self._any_drive.disconnect()


if __name__ == "__main__":
    json_path = Path(__file__).parent / "motor_test_config.json"
    steps_definition = steps_from_file(json_path)
    AppConfig.load(profile="dev", config_dirs=["./config"])
    setup_logger()
    sequence = MotorTest(
        steps_definition.steps,
        sequence_config=steps_definition.config,
    )
    sequence.run()
