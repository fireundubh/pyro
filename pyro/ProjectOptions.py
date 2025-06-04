import os

from dataclasses import dataclass, field

from pyro.Comparators import endswith


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
    no_implicit_imports: bool = field(init=False, default_factory=bool)
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
    compiler_config_path: str = field(init=False, default_factory=str)
    no_caprica_language_extensions: bool=field(init=True, default_factory=bool)

    # bsarch arguments
    bsarch_path: str = field(init=False, default_factory=str)
    package_path: str = field(init=False, default_factory=str)
    temp_path: str = field(init=False, default_factory=str)

    # zip arguments
    zip_compression: str = field(init=False, default_factory=str)
    zip_output_path: str = field(init=False, default_factory=str)

    # remote arguments
    access_token: str = field(init=False, default_factory=str)
    force_overwrite: bool = field(init=False, default_factory=bool)
    remote_temp_path: str = field(init=False, default_factory=str)

    # program arguments
    log_path: str = field(init=False, default_factory=str)
    create_project: bool = field(init=False, default_factory=bool)
    resolve_project: bool = field(init=False, default_factory=bool)

    def __post_init__(self) -> None:
        for attr_key, attr_value in self.__dict__.items():
            if attr_key == 'args':
                continue
            arg_value = self.args.get(attr_key)
            if arg_value and arg_value != attr_value:
                setattr(self, attr_key, arg_value)

    def __setattr__(self, key: str, value: object) -> None:
        if value and isinstance(value, str):
            # sanitize paths
            if endswith(key, 'path', ignorecase=True) and os.altsep in value:
                value = os.path.normpath(value)
            if key in ('game_type', 'zip_compression'):
                value = value.casefold()

        super(ProjectOptions, self).__setattr__(key, value)
