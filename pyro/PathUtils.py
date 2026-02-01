"""Path utilities wrapping pathlib.Path for Pyro-specific operations.

This module provides a centralized abstraction layer for all path operations
in Pyro, replacing the scattered logic in PathHelper and magic __setattr__
overrides in ProjectBase and ProjectOptions.

All functions accept str | Path for compatibility but work with Path internally
and return Path objects for type safety. Convert to str only at external tool
boundaries (compiler, BSArch) using to_str().
"""

import os
from collections.abc import Generator, Iterable
from pathlib import Path
from urllib.parse import unquote_plus, urlparse

from wcmatch import wcmatch

from pyro.Comparators import endswith, startswith


def normalize_path(
    path: str | Path,
    *,
    base: str | Path | None = None,
    expand_vars: bool = True
) -> Path:
    """
    Normalize path with optional base resolution and variable expansion.

    Replaces PathHelper.normalize_relative_path with clearer semantics.

    Args:
        path: Path to normalize (can be relative or absolute)
        base: Base path for resolving relative paths
        expand_vars: Whether to expand environment variables and ~ (default: True)

    Returns:
        Normalized absolute Path object

    Examples:
        >>> normalize_path("~/project/scripts")
        Path("C:/Users/username/project/scripts")

        >>> normalize_path("./scripts", base="C:/project")
        Path("C:/project/scripts")

        >>> normalize_path("%USERPROFILE%/data")
        Path("C:/Users/username/data")
    """
    path_str = str(path)

    # Expand variables if requested
    if expand_vars:
        path_str = os.path.expanduser(os.path.expandvars(path_str))

    path_obj = Path(path_str)

    # Resolve relative paths against base
    if not path_obj.is_absolute() and base:
        path_obj = Path(base) / path_obj

    # Normalize using os.path.normpath for compatibility with old behavior
    # This just normalizes the string without checking if path exists
    # or resolving symlinks (unlike Path.resolve() which can behave unexpectedly)
    return Path(os.path.normpath(str(path_obj)))


def resolve_import_path(object_name: str, import_paths: list[Path]) -> Path | None:
    """
    Find script file in import paths.

    Replaces PathHelper.calculate_absolute_script_path.

    Args:
        object_name: Script name (with or without .psc extension)
        import_paths: List of import directories to search (in priority order)

    Returns:
        Path to script file if found, None otherwise

    Examples:
        >>> import_paths = [Path("C:/project/scripts"), Path("C:/common/scripts")]
        >>> resolve_import_path("MyScript", import_paths)
        Path("C:/project/scripts/MyScript.psc")
    """
    # Ensure .psc extension
    if not endswith(object_name, '.psc', ignorecase=True):
        object_name += '.psc'

    # Search in reverse order (last import path has highest priority)
    for import_path in reversed(uniqify(import_paths)):
        script_path = import_path / object_name
        if script_path.is_file():
            return script_path

    return None


def calculate_relative_name(script_path: Path, import_paths: list[Path]) -> str:
    """
    Calculate import-relative name for a script.

    Replaces PathHelper.calculate_relative_object_name.

    Args:
        script_path: Absolute path to script file
        import_paths: List of import directories (in priority order)

    Returns:
        Relative path string from best matching import path, or filename if no match

    Examples:
        >>> script = Path("C:/project/scripts/subdir/MyScript.psc")
        >>> imports = [Path("C:/project/scripts")]
        >>> calculate_relative_name(script, imports)
        "subdir/MyScript.psc"
    """
    # Search in reverse order (last import path has highest priority)
    for import_path in reversed(uniqify(import_paths)):
        try:
            # Try to calculate relative path from import path
            rel = script_path.relative_to(import_path)
            return str(rel).replace(os.sep, '/')  # Use forward slashes consistently
        except ValueError:
            # script_path is not relative to this import_path
            continue

    # No matching import path found, return just the filename
    return script_path.name


def find_script_paths_from_folder(
    root_dir: str | Path,
    *,
    no_recurse: bool,
    matcher: wcmatch.WcMatch[str] | None = None
) -> Generator[Path, None, None]:
    """
    Yield existing script paths starting from absolute folder path.

    Args:
        root_dir: Root directory to search
        no_recurse: If True, only search root_dir (not subdirectories)
        matcher: Optional wcmatch matcher (if None, creates default *.psc matcher)

    Yields:
        Path objects for each found .psc file
    """
    root_str = str(root_dir)

    if not matcher:
        user_flags = wcmatch.RECURSIVE if not no_recurse else 0x0
        matcher = wcmatch.WcMatch(root_str, '*.psc', flags=wcmatch.IGNORECASE | user_flags)

    for script_path in matcher.imatch():
        yield Path(script_path)


def url_to_path(url: str) -> Path:
    """
    Convert URL to filesystem path.

    Replaces PathHelper.url2pathname.

    Args:
        url: URL string (e.g., "file:///C:/project/scripts")

    Returns:
        Normalized Path object

    Examples:
        >>> url_to_path("file:///C:/Users/username/project")
        Path("C:/Users/username/project")
    """
    parsed = urlparse(url)

    netloc = parsed.netloc
    path_part = parsed.path

    # Strip leading slashes
    if netloc and startswith(netloc, '/'):
        netloc = netloc[1:]

    if path_part and startswith(path_part, '/'):
        path_part = path_part[1:]

    # Combine and unquote
    combined = os.path.join(netloc, path_part) if netloc else path_part
    return Path(os.path.normpath(unquote_plus(combined)))


def to_str(path: Path) -> str:
    """
    Convert Path to string for external tools.

    Use this at the boundary when passing paths to external tools like
    the Papyrus compiler or BSArch that expect string arguments.

    Args:
        path: Path object to convert

    Returns:
        String representation of path

    Examples:
        >>> p = Path("C:/project/scripts")
        >>> to_str(p)
        "C:\\project\\scripts"  # On Windows
    """
    return str(path)


def uniqify(items: Iterable[Path]) -> list[Path]:
    """
    Return ordered list of Paths without duplicates.

    Preserves order of first occurrence.

    Args:
        items: Iterable of Path objects

    Returns:
        List with duplicates removed

    Examples:
        >>> paths = [Path("C:/a"), Path("C:/b"), Path("C:/a")]
        >>> uniqify(paths)
        [Path("C:/a"), Path("C:/b")]
    """
    return list(dict.fromkeys(items))
