"""
VariableResolver - Handles variable parsing, validation, and resolution.

Extracted from PapyrusProject._parse_variables() and ProjectBase.parse().
"""
import logging
import os
import time
from typing import TYPE_CHECKING

from lxml import etree

from pyro.Comparators import is_variable_node
from pyro.Constants import XmlAttributeName
from pyro.Exceptions import VariableError
from pyro.StringTemplate import StringTemplate

if TYPE_CHECKING:
    from pyro.ProjectOptions import ProjectOptions


class VariableResolver:
    """
    Handles parsing and resolution of project variables.

    Variables are defined in the PPJ file's <Variables> section and can reference
    each other using @name syntax. Built-in variables (UNIXTIME, PROGRAM_PATH, etc.)
    are also available.
    """

    log: logging.Logger = logging.getLogger('pyro')

    RESERVED_CHARACTERS: tuple[str, ...] = ('!', '#', '^', '&', '*')

    def __init__(self, program_path: str, project_path: str, options: 'ProjectOptions') -> None:
        """
        Initialize the variable resolver.

        Args:
            program_path: Path to the Pyro program directory
            project_path: Path to the project directory
            options: Project options containing command-line and config values
        """
        self.program_path = program_path
        self.project_path = project_path
        self.options = options
        self.variables: dict[str, str] = {}

    def parse_variables_from_xml(self, variables_node: etree.ElementBase) -> dict[str, str]:
        """
        Parse user-defined variables from an XML Variables node.

        Args:
            variables_node: The <Variables> element from the PPJ file

        Returns:
            Dictionary of variable name -> value mappings

        Raises:
            VariableError: If a variable name is not alphanumeric or value contains reserved characters
        """
        user_vars: dict[str, str] = {}

        for node in filter(is_variable_node, variables_node):
            key = node.get(XmlAttributeName.NAME, default='')
            value = node.get(XmlAttributeName.VALUE, default='')

            if not key or not value:
                continue

            if not key.isalnum():
                raise VariableError(f'The name of the variable "{key}" must be an alphanumeric string.')

            if any(c in self.RESERVED_CHARACTERS for c in value):
                raise VariableError(f'The value of the variable "{key}" contains a reserved character.')

            user_vars[key] = value

        return user_vars

    def get_builtin_variables(self) -> dict[str, str]:
        """
        Get built-in variables that are always available.

        Returns:
            Dictionary of built-in variable name -> value mappings
        """
        return {
            'UNIXTIME': str(int(time.time())),
            'PROGRAM_PATH': self.program_path,
            'PROJECT_PATH': self.project_path,
            'O_BSARCH_PATH': self.options.bsarch_path or '',
            'O_COMPILER_PATH': self.options.compiler_path or '',
            'O_COMPILER_CONFIG_PATH': self.options.compiler_config_path or '',
            'O_FLAGS_PATH': self.options.flags_path or '',
            'O_GAME_PATH': self.options.game_path or '',
            'O_LOG_PATH': self.options.log_path or '',
            'O_OUTPUT_PATH': self.options.output_path or '',
            'O_PACKAGE_PATH': self.options.package_path or '',
            'O_REGISTRY_PATH': self.options.registry_path or '',
            'O_REMOTE_TEMP_PATH': self.options.remote_temp_path or '',
            'O_TEMP_PATH': self.options.temp_path or '',
            'O_ZIP_OUTPUT_PATH': self.options.zip_output_path or '',
        }

    def resolve_value(self, value: str) -> str:
        """
        Resolve a single value by expanding variables and environment variables.

        Args:
            value: The string value to resolve

        Returns:
            The resolved string with all variables expanded

        Raises:
            VariableError: If a referenced variable is not defined
        """
        t = StringTemplate(value)
        try:
            result = os.path.expanduser(os.path.expandvars(t.substitute(self.variables)))
            if os.path.isabs(result):
                result = os.path.normpath(result)
            return result
        except KeyError as e:
            raise VariableError(f'Failed to parse variable "{e.args[0]}" in "{value}". Is the variable name correct?') from e

    def resolve_all(self, variables_node: etree.ElementBase | None = None) -> dict[str, str]:
        """
        Parse and resolve all variables, performing a two-pass resolution.

        The two-pass approach allows variables to reference each other regardless
        of definition order. For example:
        - @ModsPath = "C:\\Mods"
        - @OutputPath = "@ModsPath\\@ModName"
        - @ModName = "MyMod"

        After resolution: @OutputPath = "C:\\Mods\\MyMod"

        Args:
            variables_node: Optional <Variables> element from the PPJ file

        Returns:
            Dictionary of fully resolved variable name -> value mappings

        Raises:
            VariableError: If variable parsing or resolution fails
        """
        # Start with user-defined variables
        if variables_node is not None:
            user_vars = self.parse_variables_from_xml(variables_node)
            self.variables.update(user_vars)

        # Add built-in variables
        self.variables.update(self.get_builtin_variables())

        # First pass: resolve variables in order
        for key, value in list(self.variables.items()):
            self.variables[key] = self.resolve_value(value)

        # Second pass: resolve in reverse order to handle forward references
        for key in reversed(list(self.variables.keys())):
            value = self.variables[key]
            self.variables[key] = self.resolve_value(value)

        return self.variables
