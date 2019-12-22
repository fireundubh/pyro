import os

from dataclasses import dataclass, field


@dataclass
class ProjectOptions:
    args: dict = field(repr=False, default_factory=dict)
    anonymize: bool = field(init=False, default_factory=bool)
    package: bool = field(init=False, default_factory=bool)
    zip: bool = field(init=False, default_factory=bool)

    # required arguments
    input_path: str = field(init=False, default_factory=str)

    # build arguments
    ignore_errors: bool = field(init=False, default_factory=bool)
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
    package_path: str = field(init=False, default_factory=str)
    temp_path: str = field(init=False, default_factory=str)

    # zip arguments
    zip_compression: str = field(init=False, default_factory=str)
    zip_output_path: str = field(init=False, default_factory=str)

    # remote arguments
    access_token: str = field(init=False, default_factory=str)
    remote_temp_path: str = field(init=False, default_factory=str)

    # program arguments
    log_path: str = field(init=False, default_factory=str)

    def __post_init__(self) -> None:
        for attr_key, attr_value in self.__dict__.items():
            if attr_key == 'args':
                continue
            try:
                arg_value = self.args.get(attr_key)
            except AttributeError:
                continue
            else:
                if arg_value and arg_value != attr_value:
                    setattr(self, attr_key, arg_value)

    def __setattr__(self, key: str, value: object) -> None:
        # sanitize paths
        if isinstance(value, str) and key.endswith('path'):
            value = os.path.normpath(value)
            # normpath converts empty paths to os.curdir which we don't want
            if value == '.':
                value = ''

        super(ProjectOptions, self).__setattr__(key, value)
