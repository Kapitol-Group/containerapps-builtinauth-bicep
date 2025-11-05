from enum import IntEnum


class ProjectRoleCapability(IntEnum):
    PC_COMPLETION = 10
    DEFECTS = 12
    DOESNOTAPPLY = 13
    PC_EARLYWORKS = 7
    PC_FACADE = 1
    PC_FINISHES = 4
    OTHER = 11
    PC_SERVICES = 6
    PC_STRUCTURES = 2

    def __str__(self) -> str:
        return str(self.value)
