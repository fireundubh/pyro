"""
CompilerCommandBuilder - Handles building compiler command lines.

Extracted from PapyrusProject.build_commands().
Supports both standard Papyrus compiler and Caprica compiler.
"""
import logging
import os
import time
from pathlib import Path
from typing import TYPE_CHECKING

from pyro.CommandArguments import CommandArguments
from pyro.Comparators import endswith, startswith
from pyro.Constants import GameType

if TYPE_CHECKING:
    from pyro.PapyrusProject import PapyrusProject


class CompilerCommandBuilder:
    """
    Builds command lines for Papyrus compilation.

    Supports:
    - Standard Papyrus Compiler (per-script commands)
    - Caprica compiler (batch compilation with config file)
    """

    log: logging.Logger = logging.getLogger('pyro')

    def __init__(self, ppj: 'PapyrusProject') -> None:
        """
        Initialize the command builder.

        Args:
            ppj: The PapyrusProject instance containing project configuration
        """
        self.ppj = ppj

    def is_using_caprica(self) -> bool:
        """Check if the project is configured to use Caprica compiler."""
        return endswith(self.ppj.get_compiler_path(), 'Caprica.exe', ignorecase=True)

    def get_game_name_for_caprica(self) -> str:
        """
        Get the game name parameter for Caprica compiler.

        Returns:
            Game name string: 'starfield', 'fallout4', or 'skyrim'
        """
        if self.ppj.options.game_type == GameType.FO4:
            return 'fallout4'
        elif self.ppj.options.game_type in [GameType.TES5, GameType.SSE]:
            return 'skyrim'
        else:
            return 'starfield'

    def format_object_name_for_compiler(self, object_name: str) -> str:
        """
        Format object name according to game-specific compiler requirements.

        Converts from Pyro's internal format (forward slashes, may include .psc)
        to compiler-expected format (colons for FO4/SF1, no extension).

        Args:
            object_name: Internal object name (e.g., "Scripts/MyMod/Player.psc")

        Returns:
            Compiler-ready object name:
            - FO4/SF1: "Scripts:MyMod:Player" (colons, no extension)
            - TES5/SSE: "Scripts/MyMod/Player" (slashes, no extension)

        Examples:
            FO4:  "Scripts/MyMod/Player.psc" → "Scripts:MyMod:Player"
            SSE:  "Scripts/MyMod/Player.psc" → "Scripts/MyMod/Player"
        """
        # Strip .psc extension if present
        if object_name.endswith('.psc'):
            object_name = object_name[:-4]

        # Convert separators for FO4/SF1
        if self.ppj.options.game_type in [GameType.FO4, GameType.SF1]:
            # Replace forward slashes with colons
            object_name = object_name.replace('/', ':')
            # Also handle backslashes (shouldn't exist, but be defensive)
            object_name = object_name.replace('\\', ':')

        return object_name

    def build_caprica_commands(self, psc_paths: dict[str, str]) -> tuple[int, list[list[str]]]:
        """
        Build commands for Caprica compiler.

        Caprica compiles all scripts in a single batch operation.

        Args:
            psc_paths: Dictionary of object_name -> script_path

        Returns:
            Tuple of (script count, list of command lists)
        """
        commands: list[list[str]] = []
        arguments = CommandArguments()

        arguments.append(self.ppj.get_compiler_path(), enquote_value=True)

        object_names = ';'.join(psc_paths.keys())

        # Read and potentially modify config file
        with open(self.ppj.get_compiler_config_path(), encoding='utf-8') as f:
            options = f.read().splitlines()

        # Disable parallel compilation if the user overrides the default
        if self.ppj.options.no_parallel and 'parallel-compile=1' in options:
            for i, option in enumerate(options):
                if startswith(option, 'parallel-compile', ignorecase=True):
                    options.pop(i)
                    break

        use_config_file_for_input_paths = False

        # Check if object names exceed command line limit
        if len(object_names) > 32486:  # 32766 total - 280 chars for all arguments
            use_config_file_for_input_paths = True
            options.append(f'input-file={object_names.strip()}\n')

        # Write modified config file
        config_dir = Path(self.ppj.get_compiler_config_path()).parent
        config_file = config_dir / f'caprica_{int(time.time())}.cfg'

        config_file.write_text('\n'.join(options), encoding='utf-8')

        # Convert Path to str for external tool (compiler)
        arguments.append(str(config_file), key='-config-file', enquote_value=True)

        # Add game name
        game_name = self.get_game_name_for_caprica()
        arguments.append(game_name, key='g', enquote_value=True)

        # Add standard arguments
        arguments.append(self.ppj.get_flags_path(), key='f', enquote_value=True)
        arguments.append(';'.join(self.ppj.import_paths), key='i', enquote_value=True)
        arguments.append(self.ppj.get_output_path(), key='o', enquote_value=True)

        if not use_config_file_for_input_paths:
            arguments.append(object_names, enquote_value=True)

        commands.append(arguments.to_list())

        return len(psc_paths.keys()), commands

    def build_standard_commands(self, psc_paths: dict[str, str]) -> tuple[int, list[list[str]]]:
        """
        Build commands for standard Papyrus compiler.

        Creates one command per script.

        Args:
            psc_paths: Dictionary of object_name -> script_path

        Returns:
            Tuple of (script count, list of command lists)
        """
        commands: list[list[str]] = []
        arguments = CommandArguments()

        for object_name, script_path in psc_paths.items():
            arguments.clear()
            arguments.append(self.ppj.get_compiler_path(), enquote_value=True)

            # Modern compilers (FO4, SF1) use formatted object names with colons
            # Legacy compilers (TES5, SSE) use absolute script paths
            if self.ppj.options.game_type in [GameType.FO4, GameType.SF1]:
                # Format: strip extension, convert / to :
                formatted_name = self.format_object_name_for_compiler(object_name)
                arguments.append(formatted_name, enquote_value=True)
            else:
                # TES5/SSE can use absolute paths directly
                arguments.append(script_path, enquote_value=True)

            arguments.append(self.ppj.get_flags_path(), key='f', enquote_value=True)
            arguments.append(';'.join(self.ppj.import_paths), key='i', enquote_value=True)
            arguments.append(self.ppj.get_output_path(), key='o', enquote_value=True)

            # FO4/SF1 specific flags
            if self.ppj.options.game_type in [GameType.FO4, GameType.SF1]:
                if self.ppj.release:
                    arguments.append('-release')
                if self.ppj.final:
                    arguments.append('-final')

            # Optimize flag (all games)
            if self.ppj.optimize:
                arguments.append('-op')

            # Debug and quiet flags (supported by both FO4 and SSE compilers)
            if self.ppj.debug:
                arguments.append('-debug')

            if self.ppj.quiet:
                arguments.append('-quiet')

            # Assembly output control (all compilers)
            if self.ppj.asm == 'keep':
                arguments.append('-keepasm')
            elif self.ppj.asm == 'only':
                arguments.append('-asmonly')
            elif self.ppj.asm == 'discard':
                arguments.append('-noasm')
            # 'none' = default compiler behavior (no flag needed)

            commands.append(arguments.to_list())

        return len(psc_paths.keys()), commands

    def get_scripts_to_compile(self) -> dict[str, str]:
        """
        Get the dictionary of scripts that need to be compiled.

        Handles incremental builds and missing scripts.

        Returns:
            Dictionary of object_name -> script_path
        """
        if self.ppj.options.no_incremental_build:
            psc_paths = self.ppj.psc_paths.copy()
        else:
            psc_paths = self.ppj.script_handler.try_exclude_unmodified_scripts()

        # Add scripts whose PEX counterparts are missing
        for object_name, script_path in self.ppj.missing_scripts.items():
            if object_name not in psc_paths.keys():
                psc_paths[object_name] = script_path

        return psc_paths

    def build_commands(self) -> tuple[int, list[list[str]]]:
        """
        Build the list of commands for compiling scripts.

        This is the main entry point, matching the original PapyrusProject.build_commands() API.

        Returns:
            Tuple of (script count, list of command lists)
        """
        psc_paths = self.get_scripts_to_compile()

        # Do not try to compile nothing
        if not psc_paths:
            return 0, []

        if self.is_using_caprica():
            return self.build_caprica_commands(psc_paths)
        else:
            return self.build_standard_commands(psc_paths)
