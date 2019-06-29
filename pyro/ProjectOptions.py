from enum import Enum

from pyro.enums import GameType


class ProjectOptions:
    pyro_cfg_path: str = ''
    game_type: Enum = GameType.Fallout4
    input_path: str = ''
    disable_anonymizer: bool = False
    disable_bsarch: bool = False
    disable_indexer: bool = False
