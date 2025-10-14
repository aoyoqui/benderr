from pathlib import Path

from br_hw.motor.motor import MotorDrive
from br_hw.motor.transport_mock import TransportMock
from br_sdk.br_logging import setup_logger
from br_sdk.config import AppConfig
from br_sdk.parse_steps import steps_from_file
from br_sdk.sequence import Sequence


class MotorTest(Sequence):
    @Sequence.step("Setup")
    def test_setup(self):
        connection_handler = TransportMock()
        self._any_drive = MotorDrive(connection_handler)
        if not self._any_drive.connect():
            raise RuntimeError("Could not connect")

    @Sequence.step("Read Identifier")
    def test_read_id(self):
        return self._any_drive.device_id()

    @Sequence.step("Read calibration values")
    def test_record_calibration_values(self):
        pass

    @Sequence.step("Absolute position")
    def test_absolute_position(self):
        # Ask operator to setup rig
        # Execute commands to move the drive
        pass

    @Sequence.step("Torque resolution")
    def test_torque_resolution(self):
        pass

    @Sequence.step("Teardown")
    def test_teardown(self):
        pass



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
