"""
Core compiler protocol and data structures.

Defines the interface that all compiler implementations must follow.
"""
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass
class CompilationContext:
    """
    Input data for compilation.

    Contains all information needed to build compiler commands.
    """
    # Script information
    psc_paths: dict[str, str]  # object_name → script_path
    import_paths: list[str]
    flags_path: str
    output_path: str
    game_type: str

    # Compiler flags
    release: bool
    final: bool
    optimize: bool
    debug: bool
    quiet: bool
    asm: str  # 'none', 'keep', 'only', 'discard'

    # Execution options
    no_parallel: bool
    worker_limit: int


@dataclass
class CompilationResult:
    """
    Output metadata from command building.

    Describes the commands generated and how they should be executed.
    """
    command_count: int  # Number of scripts to compile
    commands: list[list[str]]  # Command lists for subprocess
    is_batch: bool  # True for Caprica (batch), False for Standard (per-script)


@runtime_checkable
class Compiler(Protocol):
    """
    Protocol for compiler implementations.

    Uses structural subtyping (Protocol) rather than ABC for flexibility.
    """

    def build_commands(self, context: CompilationContext) -> CompilationResult:
        """
        Build compilation commands from context.

        Args:
            context: Compilation context with all necessary information

        Returns:
            CompilationResult with commands and metadata

        Raises:
            OSError: Config file I/O errors (Caprica)
            ValueError: Invalid paths or parameters
        """
        ...

    def supports_parallel_execution(self, context: CompilationContext) -> bool:
        """
        Check if compiler supports parallel execution.

        Args:
            context: Compilation context

        Returns:
            True if parallel execution is supported and not disabled
        """
        ...

    def get_success_model(self) -> str:
        """
        Return success tracking model.

        Returns:
            'per-script' for Standard compiler (track each script)
            'batch' for Caprica compiler (all-or-nothing)
        """
        ...
