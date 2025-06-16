from br_tester.report import ReportFormatter
from br_tester.br_types import SequenceResult
from pydantic import TypeAdapter

class JsonReportFormatter(ReportFormatter):
    @property
    def ext(self):
        return ".json"
    
    def format(self, data: SequenceResult):
        return TypeAdapter(SequenceResult).dump_json(data, indent=2).decode("utf-8")
