from br_hw.motor.command import Command
from br_hw.motor.transport import Transport


class MotorDrive:
    def __init__(self, transport: Transport):
        self._handle = transport

    def connect(self):
        return self._handle.connect()

    def start_stream(self):
        self._handle.start_stream()

    def stop_stream(self):
        self._handle.stop_stream()
    
    def device_id(self):
        reply = self._handle.execute(Command.GET_DEVICE_ID)
        # Maybe some parsing would need to be done here
        return reply

