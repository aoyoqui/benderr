from typing import Protocol

class Transport(Protocol):
    def connect(self):
        pass
    
    def execute(self, command, **kwargs):
        pass
    
    def start_stream(self):
        pass

    def stop_stream(self):
        pass

    def disconnect(self):
        pass


