from enum import Enum
from typing import Union


class BuildEvent(Enum):
    PRE = 0
    POST = 1


class ImportEvent(Enum):
    PRE = 0
    POST = 1


class CompileEvent(Enum):
    PRE = 0
    POST = 1


class AnonymizeEvent(Enum):
    PRE = 0
    POST = 1


class PackageEvent(Enum):
    PRE = 0
    POST = 1


class ZipEvent(Enum):
    PRE = 0
    POST = 1


Event = Union[BuildEvent, ImportEvent, CompileEvent, AnonymizeEvent, PackageEvent, ZipEvent]
