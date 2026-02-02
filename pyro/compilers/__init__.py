"""
Compiler abstraction layer for Papyrus compilation.

Provides a clean Strategy pattern interface for different compiler implementations
(Standard Papyrus Compiler and Caprica).
"""
from pathlib import Path

from pyro.compilers.protocol import Compiler, CompilationContext, CompilationResult

# Import concrete implementations
from pyro.compilers.standard import StandardCompiler
from pyro.compilers.caprica import CapricaCompiler


def create_compiler(compiler_path: str, config_path: str = '') -> Compiler:
    """
    Create appropriate compiler instance based on compiler path.

    Uses exact filename match for robustness (not endswith check).

    Args:
        compiler_path: Path to compiler executable
        config_path: Path to compiler config file (Caprica only)

    Returns:
        Compiler instance (StandardCompiler or CapricaCompiler)

    Examples:
        >>> compiler = create_compiler('/path/to/Caprica.exe', '/path/to/caprica.cfg')
        >>> isinstance(compiler, CapricaCompiler)
        True

        >>> compiler = create_compiler('/path/to/PapyrusCompiler.exe')
        >>> isinstance(compiler, StandardCompiler)
        True
    """
    compiler_name = Path(compiler_path).name.lower()
    if compiler_name == 'caprica.exe':
        return CapricaCompiler(compiler_path, config_path)
    else:
        return StandardCompiler(compiler_path)


__all__ = [
    'Compiler',
    'CompilationContext',
    'CompilationResult',
    'StandardCompiler',
    'CapricaCompiler',
    'create_compiler',
]
