from br_hw.motor.command import Command
from random import randint

replies = {
    Command.GET_DEVICE_ID: "0x0010",
    Command.RUN_DIAGNOSTICS: True,
    Command.ABSOLUTE_POSITION: randint(0, 131072)
}

class TransportMock:
    def __init__(self):
        self._sync_period_s = 0.5
        self._encoder_value = 0

    def connect(self):
        return True
    
    def execute(self, command, **kwargs):
        print(f"Executing {command} with {self.__class__.__name__}")
        return replies[command]

    def start_stream(self):
        self._sync_running = True
        import threading
        def _run_sync():
            import contextlib
            def loop():
                import time
                next_t = time.time()
                msg = "Some message"
                while self._sync_running:
                    now = time.time()
                    if now >= next_t:
                        with contextlib.suppress(Exception):
                            self._bus.send(msg)
                        next_t += self._sync_period_s
                    time.sleep(min(0.001, max(0.0, next_t - time.time())))

            t = threading.Thread(target=loop, daemon=True)
            t.start()

        _run_sync() 

    def stop_stream(self):
        self._sync_running = False

    def disconnect(self):
        pass


if __name__ == "__main__":
    t = TransportMock()
    t.connect()

    t.start_stream()
    input("Press enter to stop stream")
    t.stop_stream()
    input("Press enter to exit")
