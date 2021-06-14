from enum import Enum
from typing import Union


class BuildEvent(Enum):
    PRE = 0
    POST = 1


class ImportEvent(Enum):
    PRE = 0
    POST = 1


Event = Union[BuildEvent, ImportEvent]
