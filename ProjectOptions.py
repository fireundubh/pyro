from enum import Enum

from GameType import GameType


class ProjectOptions:
    game_type: Enum = GameType.Fallout4
    input_path: str = ''
    disable_anonymizer: bool = False
    disable_bsarch: bool = False
    disable_indexer: bool = False
