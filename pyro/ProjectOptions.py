from enum import Enum

from pyro.enums import GameType


class ProjectOptions:
    pyro_cfg_path: str = ''
    game_type: Enum = GameType.Unknown
    input_path: str = ''
    disable_anonymizer: bool = False
    disable_bsarch: bool = False
    disable_indexer: bool = False
    disable_parallel: bool = False

    def __init__(self, options: dict = None):
        if not options:
            return

        for key in options:
            if key in options:
                setattr(self, key, options[key])
