"""Shared utilities for archive builders."""
import logging
import os
from collections.abc import Generator
from pathlib import Path

from lxml import etree
from wcmatch import glob, wcmatch

from pyro.Comparators import is_include_node, is_match_node, startswith
from pyro.Constants import XmlAttributeName
from pyro.Exceptions import PackagingError, ZipError
from pyro.PathUtils import normalize_path

log: logging.Logger = logging.getLogger('pyro')

DEFAULT_GLFLAGS = glob.NODIR | glob.MATCHBASE | glob.SPLIT | glob.REALPATH | glob.FOLLOW | glob.IGNORECASE | glob.MINUSNEGATE
DEFAULT_WCFLAGS = wcmatch.SYMLINKS | wcmatch.IGNORECASE | wcmatch.MINUSNEGATE


def check_write_permission(file_path: str | Path) -> None:
    """Check if we have write permission for the given file path.

    Args:
        file_path: Path to check (str or Path object)

    Raises:
        PackagingError: If write permission is denied
    """
    path = Path(file_path)
    if path.is_file():
        try:
            path.open('a').close()
        except PermissionError:
            log.error(f'Cannot create file without write permission to: "{path}"')
            raise PackagingError(f'Cannot create file without write permission to: "{path}"')


def match_files(root_dir: str | Path, file_pattern: str, *, exclude_pattern: str = '', user_path: str = '', no_recurse: bool = False) -> Generator[tuple[str, str], None, None]:
    """Match files in root_dir using wcmatch patterns.

    Args:
        root_dir: Root directory to search (str or Path object)
        file_pattern: File pattern to match
        exclude_pattern: Pattern to exclude
        user_path: User-provided path attribute
        no_recurse: If True, don't recurse into subdirectories

    Yields:
        Tuples of (matched_file_path, user_path)
    """
    # Convert to str for wcmatch (requires string paths)
    root_str = str(root_dir)
    user_flags = wcmatch.RECURSIVE if not no_recurse else 0x0
    matcher = wcmatch.WcMatch(root_str, file_pattern,
                              exclude_pattern=exclude_pattern,
                              flags=DEFAULT_WCFLAGS | user_flags)

    matcher.on_reset()
    matcher._skipped = 0
    for file_path in matcher._walk():
        yield file_path, user_path


def generate_include_paths(includes_node: etree.ElementBase, root_path: str | Path, zip_mode: bool = False) -> Generator[tuple[str, str], None, None]:
    """
    Generate file paths from <Include> and <Match> nodes in project XML.

    Args:
        includes_node: Parent XML node containing Include/Match elements
        root_path: Root directory for resolving relative paths (str or Path)
        zip_mode: If True, allows paths outside RootDir (for ZIP archives)

    Yields:
        Tuples of (absolute_file_path, user_provided_path_attribute)

    Raises:
        PackagingError: For BSA/BA2 validation errors
        ZipError: For ZIP validation errors
    """
    # Convert root_path to Path for internal operations
    root_p = Path(root_path)
    root_str = str(root_p)
    for include_node in filter(is_include_node, includes_node):
        attr_no_recurse: bool = include_node.get(XmlAttributeName.NO_RECURSE) == 'True'
        attr_path: str = include_node.get(XmlAttributeName.PATH).strip()
        search_path: str = include_node.text

        if not search_path:
            error_msg = f'Include path at line {include_node.sourceline} in project file is empty'
            log.error(error_msg)
            if zip_mode:
                raise ZipError(error_msg)
            else:
                raise PackagingError(error_msg)

        # normalize early; pardir check remains for validation
        search_p = normalize_path(search_path, base=root_p)
        search_str = str(search_p)

        if not zip_mode and startswith(search_str, os.pardir):
            error_msg = f'Include paths cannot start with "{os.pardir}"'
            log.error(error_msg)
            raise PackagingError(error_msg)

        # fix invalid pattern with leading separator (post-norm; assumes normpath handles seps)
        if not zip_mode and startswith(search_str, (os.path.sep, os.path.altsep)):
            search_str = '**' + search_str

        if '\\' in search_str:
            search_str = search_str.replace('\\', '/')

        # populate files list using glob patterns or relative paths
        if '*' in search_str:
            for include_path in glob.iglob(search_str,
                                           root_dir=root_str,
                                           flags=DEFAULT_GLFLAGS | glob.GLOBSTAR if not attr_no_recurse else 0x0):
                yield str(root_p / include_path), attr_path

        elif not search_p.is_absolute():
            test_p = (root_p / search_str).resolve()
            if test_p.is_file():
                yield str(test_p), attr_path
            elif test_p.is_dir():
                yield from match_files(test_p, '*.*',
                                                 user_path=attr_path,
                                                 no_recurse=attr_no_recurse)
            else:
                for include_path in glob.iglob(search_str,
                                               root_dir=root_str,
                                               flags=DEFAULT_GLFLAGS | glob.GLOBSTAR if not attr_no_recurse else 0x0):
                    yield str(root_p / include_path), attr_path

        # populate files list using absolute paths
        else:
            if not zip_mode and root_str not in search_str:
                error_msg = f'Cannot include path outside RootDir: "{search_str}"'
                log.error(error_msg)
                raise PackagingError(error_msg)

            search_p = search_p.resolve()

            if search_p.is_file():
                yield str(search_p), attr_path
            else:
                yield from match_files(search_p, '*.*',
                                                 user_path=attr_path,
                                                 no_recurse=attr_no_recurse)

    for match_node in filter(is_match_node, includes_node):
        attr_in: str = match_node.get(XmlAttributeName.IN).strip()
        attr_no_recurse: bool = match_node.get(XmlAttributeName.NO_RECURSE) == 'True'  # type: ignore
        attr_exclude: str = match_node.get(XmlAttributeName.EXCLUDE).strip()
        attr_path: str = match_node.get(XmlAttributeName.PATH).strip()  # type: ignore

        in_p = normalize_path(attr_in, base=root_p)
        in_str = str(in_p)

        if zip_mode and not (root_p / in_str).exists():
            error_msg = f'Cannot match path outside RootDir: "{root_str}" not in "{in_str}"'
            log.error(error_msg)
            raise ZipError(error_msg)

        if not in_p.is_dir():
            error_msg = f'Cannot match path that does not exist or is not a directory: "{in_str}"'
            log.error(error_msg)
            if zip_mode:
                raise ZipError(error_msg)
            else:
                raise PackagingError(error_msg)

        match_text: str = match_node.text

        if startswith(match_text, '.'):
            error_msg = f'Match pattern at line {match_node.sourceline} in project file is not a valid wildcard pattern'
            log.error(error_msg)
            if zip_mode:
                raise ZipError(error_msg)
            else:
                raise PackagingError(error_msg)

        yield from match_files(in_p, match_text,
                                         exclude_pattern=attr_exclude,
                                         user_path=attr_path,
                                         no_recurse=attr_no_recurse)
