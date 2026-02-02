"""
CapricaCompiler - Caprica compiler implementation.

Creates a single batch command for all scripts. Uses config file for configuration.
"""
import time
from pathlib import Path

from pyro.CommandArguments import CommandArguments
from pyro.Comparators import startswith
from pyro.Constants import GameType
from pyro.compilers.protocol import CompilationContext, CompilationResult


class CapricaCompiler:
    """
    Caprica compiler implementation.

    Characteristics:
    - Single batch command for all scripts
    - All-or-nothing success model
    - Config file based configuration
    - Handles command line length limits (>32K chars)
    - Always sequential execution
    """

    def __init__(self, compiler_path: str, config_path: str) -> None:
        """
        Initialize Caprica compiler.

        Args:
            compiler_path: Path to Caprica.exe
            config_path: Path to caprica.cfg
        """
        self.compiler_path = compiler_path
        self.config_path = config_path

    def _get_game_name(self, game_type: str) -> str:
        """
        Get the game name parameter for Caprica compiler.

        Args:
            game_type: Game type constant

        Returns:
            Game name string: 'starfield', 'fallout4', or 'skyrim'
        """
        if game_type == GameType.FO4:
            return 'fallout4'
        elif game_type in [GameType.TES5, GameType.SSE]:
            return 'skyrim'
        else:
            return 'starfield'

    def build_commands(self, context: CompilationContext) -> CompilationResult:
        """
        Build commands for Caprica compiler.

        Caprica compiles all scripts in a single batch operation.

        Args:
            context: Compilation context

        Returns:
            CompilationResult with single batch command

        Raises:
            OSError: Config file I/O errors
            PermissionError: Config file permission errors
        """
        # Handle empty script list
        if not context.psc_paths:
            return CompilationResult(
                command_count=0,
                commands=[],
                is_batch=True
            )

        arguments = CommandArguments()
        arguments.append(self.compiler_path, enquote_value=True)

        object_names = ';'.join(context.psc_paths.keys())

        # Read and potentially modify config file
        with open(self.config_path, encoding='utf-8') as f:
            options = f.read().splitlines()

        # Disable parallel compilation if the user overrides the default
        if context.no_parallel and 'parallel-compile=1' in options:
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
        config_dir = Path(self.config_path).parent
        config_file = config_dir / f'caprica_{int(time.time())}.cfg'

        config_file.write_text('\n'.join(options), encoding='utf-8')

        # Convert Path to str for external tool (compiler)
        arguments.append(str(config_file), key='-config-file', enquote_value=True)

        # Add game name
        game_name = self._get_game_name(context.game_type)
        arguments.append(game_name, key='g', enquote_value=True)

        # Add standard arguments
        arguments.append(context.flags_path, key='f', enquote_value=True)
        arguments.append(';'.join(context.import_paths), key='i', enquote_value=True)
        arguments.append(context.output_path, key='o', enquote_value=True)

        if not use_config_file_for_input_paths:
            arguments.append(object_names, enquote_value=True)

        commands = [arguments.to_list()]

        return CompilationResult(
            command_count=len(context.psc_paths),
            commands=commands,
            is_batch=True
        )

    def supports_parallel_execution(self, context: CompilationContext) -> bool:
        """
        Check if compiler supports parallel execution.

        Caprica always runs as a single batch, so parallel execution at the
        command level is not applicable.

        Args:
            context: Compilation context

        Returns:
            False - Caprica uses single batch command
        """
        return False

    def get_success_model(self) -> str:
        """
        Return success tracking model.

        Returns:
            'batch' - all scripts compile together (all-or-nothing)
        """
        return 'batch'
