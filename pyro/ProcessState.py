from enum import Enum


class ProcessState(Enum):
    SUCCESS = 0
    FAILURE = 1
    INTERRUPTED = 2
    ERRORS = 3
