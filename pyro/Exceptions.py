"""
Custom exceptions for Pyro build system.
These replace sys.exit(1) calls to allow proper error handling.
"""


class PyroException(Exception):
    """Base exception for all Pyro errors."""
    pass


class AnonymizationError(PyroException):
    """Raised when script anonymization fails."""
    pass


class PexReadError(PyroException):
    """Raised when reading a PEX file fails."""
    pass


class CompilationError(PyroException):
    """Raised when script compilation fails."""
    pass


class PackagingError(PyroException):
    """Raised when BSA/BA2 packaging fails."""
    pass


class ZipError(PyroException):
    """Raised when ZIP creation fails."""
    pass


class VariableError(PyroException):
    """Raised when variable parsing or resolution fails."""
    pass


class GameTypeError(PyroException):
    """Raised when game type detection fails."""
    pass


class ProjectError(PyroException):
    """Raised when project loading or validation fails."""
    pass
