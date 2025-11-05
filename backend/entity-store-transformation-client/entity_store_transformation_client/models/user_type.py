from enum import IntEnum


class UserType(IntEnum):
    APPLICATION = 3
    GROUP = 1
    ROBOT = 2
    USER = 0

    def __str__(self) -> str:
        return str(self.value)
