import os

from argparse import Namespace
from dataclasses import dataclass, field


@dataclass
class ProjectOptions:
    args: Namespace = field(repr=False, default_factory=Namespace)

    # required arguments
    input_path: str = field(init=False, default_factory=lambda: '')

    # optional arguments
    no_anonymize: bool = field(init=False, default_factory=bool)
    no_bsarch: bool = field(init=False, default_factory=bool)
    no_incremental_build: bool = field(init=False, default_factory=bool)
    no_parallel: bool = field(init=False, default_factory=bool)

    # compiler arguments
    compiler_path: str = field(init=False, default_factory=lambda: r'Papyrus Compiler\PapyrusCompiler.exe')
    flags_path: str = field(init=False, default_factory=lambda: '')
    source_path: str = field(init=False, default_factory=lambda: r'Data\Scripts\Source')
    base_path: str = field(init=False, default_factory=lambda: r'Data\Scripts\Source\Base')
    user_path: str = field(init=False, default_factory=lambda: r'Data\Scripts\Source\User')

    # game arguments
    game_path: str = field(init=False, default_factory=lambda: '')
    game_type: str = field(init=False, default_factory=lambda: '')
    registry_path: str = field(init=False, default_factory=lambda: '')

    # tool arguments
    bsarch_path: str = field(init=False, default_factory=lambda: '')

    # program arguments
    temp_path: str = field(init=False, default_factory=lambda: r'..\temp')

    def __post_init__(self) -> None:
        for key in self.__dict__:
            if key == 'args':
                continue
            try:
                user_value = getattr(self.args, key)
                if user_value and user_value != getattr(self, key):
                    setattr(self, key, user_value)
            except AttributeError:
                continue

    def __setattr__(self, key, value):
        # sanitize paths
        if key.endswith('path'):
            value = os.path.normpath(value)
            # normpath converts empty paths to os.curdir which we don't want
            if value == '.':
                value = ''

        if key == 'game_type':
            value = value.lower()

        super(ProjectOptions, self).__setattr__(key, value)
