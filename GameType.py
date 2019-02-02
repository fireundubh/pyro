import enum


@enum.unique
class GameType(enum.Enum):
    Fallout4 = 0
    SkyrimSpecialEdition = 1
    SkyrimClassic = 2

    @staticmethod
    def from_str(alias):
        if alias == 'fo4':
            return GameType.Fallout4
        if alias == 'sse':
            return GameType.SkyrimSpecialEdition
        if alias == 'tes5':
            return GameType.SkyrimClassic
