from pydantic import TypeAdapter

from br_sdk.br_types import SequenceResult
from br_sdk.report import ReportFormatter


class JsonReportFormatter(ReportFormatter):
    @property
    def ext(self):
        return ".json"
    
    def format(self, data: SequenceResult):
        return TypeAdapter(SequenceResult).dump_json(data, indent=2).decode("utf-8")
