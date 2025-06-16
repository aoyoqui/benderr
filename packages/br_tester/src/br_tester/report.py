class ReportFormatter:
    @property
    def ext(self):
        raise NotImplementedError

    def format(self, data):
        raise NotImplementedError
    