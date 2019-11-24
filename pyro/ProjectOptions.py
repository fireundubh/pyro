import os

from dataclasses import dataclass, field


@dataclass
class ProjectOptions:
    args: dict = field(repr=False, default_factory=dict)

    # required arguments
    input_path: str = field(init=False, default_factory=str)

    # build arguments
    anonymize: bool = field(init=False, default_factory=bool)
    bsarch: bool = field(init=False, default_factory=bool)
    no_incremental_build: bool = field(init=False, default_factory=bool)
    no_parallel: bool = field(init=False, default_factory=bool)
    worker_limit: int = field(init=False, default_factory=int)

    # game arguments
    game_type: str = field(init=False, default_factory=str)
    game_path: str = field(init=False, default_factory=str)
    registry_path: str = field(init=False, default_factory=str)

    # compiler arguments
    compiler_path: str = field(init=False, default_factory=str)
    flags_path: str = field(init=False, default_factory=str)
    output_path: str = field(init=False, default_factory=str)

    # bsarch arguments
    bsarch_path: str = field(init=False, default_factory=str)
    archive_path: str = field(init=False, default_factory=str)
    temp_path: str = field(init=False, default_factory=str)

    # program arguments
    log_path: str = field(init=False, default_factory=str)

    def __post_init__(self) -> None:
        for key in self.__dict__:
            if key == 'args':
                continue
            try:
                value = self.args.get(key)
                if value and value != getattr(self, key):
                    setattr(self, key, value)
            except AttributeError:
                continue

    def __setattr__(self, key: str, value: object) -> None:
        # sanitize paths
        if isinstance(value, str) and key.endswith('path'):
            value = os.path.normpath(value)
            # normpath converts empty paths to os.curdir which we don't want
            if value == '.':
                value = ''

        super(ProjectOptions, self).__setattr__(key, value)
