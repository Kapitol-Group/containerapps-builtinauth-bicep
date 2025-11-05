from enum import IntEnum


class ProjectContractType(IntEnum):
    CONSTRUCT_ONLY = 1
    DESIGN_CONSTRUCT = 4
    ECI = 0
    GMP = 3
    MANAGING_CONTRACTOR = 2

    def __str__(self) -> str:
        return str(self.value)
