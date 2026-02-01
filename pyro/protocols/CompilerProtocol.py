"""
Compiler detection and path resolution protocol.

This protocol defines the interface for compiler detection services.
Currently, compiler detection logic is duplicated in:
- CompilerCommandBuilder
- CompilationService

TODO: Task 3 will unify this into a single CompilerDetector implementing this protocol.
"""

from typing import Protocol


class CompilerProtocol(Protocol):
    """
    Protocol for compiler detection and path resolution.

    Implementations should provide methods to:
    1. Detect which compiler is being used (PapyrusCompiler vs Caprica)
    2. Resolve the compiler executable path
    """

    def is_using_caprica(self) -> bool:
        """
        Determines whether the Caprica compiler is being used.

        Returns:
            True if using Caprica compiler, False if using PapyrusCompiler
        """
        ...

    def get_compiler_path(self) -> str:
        """
        Gets the path to the compiler executable.

        Returns:
            Absolute path to the compiler executable
        """
        ...
