class Bus:
    def send(self, msg):
        print(msg)

class TransportCanOpen:
    def connect(self):
        return False
    
    def execute(self, command, **kwargs):
        print(f"Executing {command} with {self.__class__.__name__}")

    def start_stream(self):
        print(f"Start stream with {self.__class__.__name__}")
        print()

    def stop_stream(self):
        print(f"Start stream with {self.__class__.__name__}")

    def disconnect(self):
        pass

