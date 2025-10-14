from enum import StrEnum

class Command(StrEnum):
    GET_DEVICE_ID = "id"
    ABSOLUTE_POSITION = "pos"
    RUN_DIAGNOSTICS = "diag"
