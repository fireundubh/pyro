import os

from dataclasses import dataclass, field
from pathlib import Path

from pyro.Comparators import endswith
from pyro.PathUtils import normalize_path


@dataclass
class ProjectOptions:
    """
    Defines the ProjectOptions class to manage configuration options for a project.

    This class represents a collection of configuration options for various aspects
    of a project, such as build settings, game-specific arguments, compiler settings,
    and others. The class allows easy initialization and updating of these options
    based on a dictionary of provided arguments. The options are categorized into
    different groupings, like build arguments, zip arguments, and remote arguments,
    for improved organization.

    :ivar args: A dictionary containing arguments to update the respective attributes.
    :type args: dict
    :ivar anonymize: Whether to enable anonymization for certain operations.
    :type anonymize: bool
    :ivar package: Whether to enable packaging functionality for the project.
    :type package: bool
    :ivar zip: Whether to enable zip functionality for packaging.
    :type zip: bool
    :ivar input_path: File path specifying the input source for the project.
    :type input_path: str
    :ivar ignore_errors: Whether to ignore errors during the build process.
    :type ignore_errors: bool
    :ivar no_incremental_build: Whether to disable incremental builds.
    :type no_incremental_build: bool
    :ivar no_parallel: Whether to disable parallel operations.
    :type no_parallel: bool
    :ivar worker_limit: Maximum number of worker threads for parallel operations.
    :type worker_limit: int
    :ivar game_type: The type of the game being managed (e.g., configuration type).
    :type game_type: str
    :ivar game_path: The file path to the game files.
    :type game_path: str
    :ivar registry_path: The file path to the game registry.
    :type registry_path: str
    :ivar compiler_path: The file path to the compiler binary.
    :type compiler_path: str
    :ivar compiler_config_path: The file path to the compiler configuration.
    :type compiler_config_path: str
    :ivar flags_path: The file path to the compiler flags file.
    :type flags_path: str
    :ivar output_path: The file path for the compiler's output directory.
    :type output_path: str
    :ivar bsarch_path: The path to the BSArch executable.
    :type bsarch_path: str
    :ivar package_path: The file path for the project's package directory.
    :type package_path: str
    :ivar temp_path: The file path to a temporary directory.
    :type temp_path: str
    :ivar zip_compression: The compression level or type for zip files.
    :type zip_compression: str
    :ivar zip_output_path: The file path for the output zip file.
    :type zip_output_path: str
    :ivar access_token: The access token for remote operations.
    :type access_token: str
    :ivar force_overwrite: Whether to force overwriting during remote operations.
    :type force_overwrite: bool
    :ivar remote_temp_path: The temporary directory path for remote operations.
    :type remote_temp_path: str
    :ivar log_path: The file path to the log file.
    :type log_path: str
    :ivar create_project: Whether to enable project creation functionality.
    :type create_project: bool
    :ivar resolve_project: Whether to enable resolving project dependencies.
    :type resolve_project: bool
    """
    args: dict[str, object] = field(repr=False, default_factory=dict)
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
    compiler_config_path: str = field(init=False, default_factory=str)
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
    force_overwrite: bool = field(init=False, default_factory=bool)
    remote_temp_path: str = field(init=False, default_factory=str)

    # program arguments
    log_path: str = field(init=False, default_factory=str)
    create_project: bool = field(init=False, default_factory=bool)
    resolve_project: bool = field(init=False, default_factory=bool)

    def __post_init__(self) -> None:
        """Initialize fields from args dictionary with explicit normalization."""
        for attr_key in self.__dict__:
            if attr_key == 'args':
                continue
            arg_value = self.args.get(attr_key)
            if arg_value and arg_value != getattr(self, attr_key):
                # Use object.__setattr__ to bypass any setattr magic during init
                object.__setattr__(self, attr_key, self._normalize_field(attr_key, arg_value))

    def _normalize_field(self, key: str, value: object) -> object:
        """
        Explicitly normalize field values based on field type.

        No more magic __setattr__ - this method is called explicitly during initialization.

        Args:
            key: Field name
            value: Field value to normalize

        Returns:
            Normalized value
        """
        if not value or not isinstance(value, str):
            return value

        # Normalize path fields
        if endswith(key, 'path', ignorecase=True):
            # Convert to Path and back to str for compatibility
            # (Full Path migration happens in later tasks)
            return str(normalize_path(value, expand_vars=True))

        # Normalize enum-like fields to lowercase
        if key in ('game_type', 'zip_compression'):
            return value.casefold()

        return value
