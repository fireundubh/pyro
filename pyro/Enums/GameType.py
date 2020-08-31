from enum import Enum


class GameType(Enum):
    FO4 = 0
    SSE = 1
    TES5 = 2

    @classmethod
    def _missing_(cls, value):
        try:
            return cls[value.upper()]
        except KeyError:
            pass
        super(GameType, cls)._missing_(value)

    @classmethod
    def has_member(cls, member: str):
        return member.upper() in cls._member_names_
