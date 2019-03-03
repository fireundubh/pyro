from enum import Enum


class ValidationState(Enum):
    FILE_MODIFIED = 0
    FILE_NOT_EXIST = 1
    FILE_NOT_MODIFIED = 2
