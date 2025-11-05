from enum import IntEnum


class TenderProcessStatus(IntEnum):
    EXPORTED = 0
    EXTRACTED = 2
    FAILED = 3
    QUEUED = 1

    def __str__(self) -> str:
        return str(self.value)
