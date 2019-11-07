import enum


@enum.unique
class GameType(enum.Enum):
    none = 0
    Fallout4 = 1
    SkyrimSpecialEdition = 2
    SkyrimClassic = 3

    @staticmethod
    def from_str(alias: str) -> enum.Enum:
        if alias == 'fo4':
            return GameType.Fallout4
        if alias == 'sse':
            return GameType.SkyrimSpecialEdition
        if alias == 'tes5':
            return GameType.SkyrimClassic
        else:
            return GameType.none
