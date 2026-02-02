"""
StandardCompiler - Standard Papyrus compiler implementation.

Creates one command per script. Supports all game types (FO4, SF1, SSE, TES5).
"""
from pyro.CommandArguments import CommandArguments
from pyro.Constants import GameType
from pyro.compilers.protocol import CompilationContext, CompilationResult


class StandardCompiler:
    """
    Standard Papyrus compiler implementation.

    Characteristics:
    - One command per script
    - Per-script success tracking
    - Game-specific script formatting (FO4/SF1 use colons, TES5/SSE use paths)
    - Supports parallel execution
    """

    def __init__(self, compiler_path: str) -> None:
        """
        Initialize standard compiler.

        Args:
            compiler_path: Path to compiler executable
        """
        self.compiler_path = compiler_path

    def _format_object_name(self, object_name: str, game_type: str) -> str:
        """
        Format object name according to game-specific compiler requirements.

        Converts from Pyro's internal format (forward slashes, may include .psc)
        to compiler-expected format (colons for FO4/SF1, no extension).

        Args:
            object_name: Internal object name (e.g., "Scripts/MyMod/Player.psc")
            game_type: Game type constant

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
        if game_type in [GameType.FO4, GameType.SF1]:
            # Replace forward slashes with colons
            object_name = object_name.replace('/', ':')
            # Also handle backslashes (shouldn't exist, but be defensive)
            object_name = object_name.replace('\\', ':')

        return object_name

    def build_commands(self, context: CompilationContext) -> CompilationResult:
        """
        Build commands for standard Papyrus compiler.

        Creates one command per script.

        Args:
            context: Compilation context

        Returns:
            CompilationResult with per-script commands
        """
        # Handle empty script list
        if not context.psc_paths:
            return CompilationResult(
                command_count=0,
                commands=[],
                is_batch=False
            )

        commands: list[list[str]] = []
        arguments = CommandArguments()

        for object_name, script_path in context.psc_paths.items():
            arguments.clear()
            arguments.append(self.compiler_path, enquote_value=True)

            # Modern compilers (FO4, SF1) use formatted object names with colons
            # Legacy compilers (TES5, SSE) use absolute script paths
            if context.game_type in [GameType.FO4, GameType.SF1]:
                # Format: strip extension, convert / to :
                formatted_name = self._format_object_name(object_name, context.game_type)
                arguments.append(formatted_name, enquote_value=True)
            else:
                # TES5/SSE can use absolute paths directly
                arguments.append(script_path, enquote_value=True)

            arguments.append(context.flags_path, key='f', enquote_value=True)
            arguments.append(';'.join(context.import_paths), key='i', enquote_value=True)
            arguments.append(context.output_path, key='o', enquote_value=True)

            # FO4/SF1 specific flags
            if context.game_type in [GameType.FO4, GameType.SF1]:
                if context.release:
                    arguments.append('-release')
                if context.final:
                    arguments.append('-final')

            # Optimize flag (all games)
            if context.optimize:
                arguments.append('-op')

            # Debug and quiet flags (supported by both FO4 and SSE compilers)
            if context.debug:
                arguments.append('-debug')

            if context.quiet:
                arguments.append('-quiet')

            # Assembly output control (all compilers)
            if context.asm == 'keep':
                arguments.append('-keepasm')
            elif context.asm == 'only':
                arguments.append('-asmonly')
            elif context.asm == 'discard':
                arguments.append('-noasm')
            # 'none' = default compiler behavior (no flag needed)

            commands.append(arguments.to_list())

        return CompilationResult(
            command_count=len(context.psc_paths),
            commands=commands,
            is_batch=False
        )

    def supports_parallel_execution(self, context: CompilationContext) -> bool:
        """
        Check if compiler supports parallel execution.

        Standard compiler supports parallel execution unless disabled by user.

        Args:
            context: Compilation context

        Returns:
            True if parallel execution is not disabled
        """
        return not context.no_parallel

    def get_success_model(self) -> str:
        """
        Return success tracking model.

        Returns:
            'per-script' - each script is tracked individually
        """
        return 'per-script'
