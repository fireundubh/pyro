"""Shared utilities for archive builders."""
import logging
import os
from collections.abc import Generator

from lxml import etree
from wcmatch import glob, wcmatch

from pyro.Comparators import is_include_node, is_match_node, startswith
from pyro.Constants import XmlAttributeName
from pyro.Exceptions import PackagingError, ZipError
from pyro.PathUtils import normalize_path

log: logging.Logger = logging.getLogger('pyro')

DEFAULT_GLFLAGS = glob.NODIR | glob.MATCHBASE | glob.SPLIT | glob.REALPATH | glob.FOLLOW | glob.IGNORECASE | glob.MINUSNEGATE
DEFAULT_WCFLAGS = wcmatch.SYMLINKS | wcmatch.IGNORECASE | wcmatch.MINUSNEGATE


def check_write_permission(file_path: str) -> None:
    """Check if we have write permission for the given file path."""
    if os.path.isfile(file_path):
        try:
            open(file_path, 'a').close()
        except PermissionError:
            log.error(f'Cannot create file without write permission to: "{file_path}"')
            raise PackagingError(f'Cannot create file without write permission to: "{file_path}"')


def match_files(root_dir: str, file_pattern: str, *, exclude_pattern: str = '', user_path: str = '', no_recurse: bool = False) -> Generator[tuple[str, str], None, None]:
    """Match files in root_dir using wcmatch patterns."""
    user_flags = wcmatch.RECURSIVE if not no_recurse else 0x0
    matcher = wcmatch.WcMatch(root_dir, file_pattern,
                              exclude_pattern=exclude_pattern,
                              flags=DEFAULT_WCFLAGS | user_flags)

    matcher.on_reset()
    matcher._skipped = 0
    for file_path in matcher._walk():
        yield file_path, user_path


def generate_include_paths(includes_node: etree.ElementBase, root_path: str, zip_mode: bool = False) -> Generator[tuple[str, str], None, None]:
    """
    Generate file paths from <Include> and <Match> nodes in project XML.

    Args:
        includes_node: Parent XML node containing Include/Match elements
        root_path: Root directory for resolving relative paths
        zip_mode: If True, allows paths outside RootDir (for ZIP archives)

    Yields:
        Tuples of (absolute_file_path, user_provided_path_attribute)

    Raises:
        PackagingError: For BSA/BA2 validation errors
        ZipError: For ZIP validation errors
    """
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
        search_path = str(normalize_path(search_path, base=root_path))

        if not zip_mode and startswith(search_path, os.pardir):
            error_msg = f'Include paths cannot start with "{os.pardir}"'
            log.error(error_msg)
            raise PackagingError(error_msg)

        # fix invalid pattern with leading separator (post-norm; assumes normpath handles seps)
        if not zip_mode and startswith(search_path, (os.path.sep, os.path.altsep)):
            search_path = '**' + search_path

        if '\\' in search_path:
            search_path = search_path.replace('\\', '/')

        # populate files list using glob patterns or relative paths
        if '*' in search_path:
            for include_path in glob.iglob(search_path,
                                           root_dir=root_path,
                                           flags=DEFAULT_GLFLAGS | glob.GLOBSTAR if not attr_no_recurse else 0x0):
                yield os.path.join(root_path, include_path), attr_path

        elif not os.path.isabs(search_path):
            test_path = os.path.normpath(os.path.join(root_path, search_path))
            if os.path.isfile(test_path):
                yield test_path, attr_path
            elif os.path.isdir(test_path):
                yield from match_files(test_path, '*.*',
                                                 user_path=attr_path,
                                                 no_recurse=attr_no_recurse)
            else:
                for include_path in glob.iglob(search_path,
                                               root_dir=root_path,
                                               flags=DEFAULT_GLFLAGS | glob.GLOBSTAR if not attr_no_recurse else 0x0):
                    yield os.path.join(root_path, include_path), attr_path

        # populate files list using absolute paths
        else:
            if not zip_mode and root_path not in search_path:
                error_msg = f'Cannot include path outside RootDir: "{search_path}"'
                log.error(error_msg)
                raise PackagingError(error_msg)

            search_path = os.path.abspath(os.path.normpath(search_path))

            if os.path.isfile(search_path):
                yield search_path, attr_path
            else:
                yield from match_files(search_path, '*.*',
                                                 user_path=attr_path,
                                                 no_recurse=attr_no_recurse)

    for match_node in filter(is_match_node, includes_node):
        attr_in: str = match_node.get(XmlAttributeName.IN).strip()
        attr_no_recurse: bool = match_node.get(XmlAttributeName.NO_RECURSE) == 'True'  # type: ignore
        attr_exclude: str = match_node.get(XmlAttributeName.EXCLUDE).strip()
        attr_path: str = match_node.get(XmlAttributeName.PATH).strip()  # type: ignore

        in_path: str = str(normalize_path(attr_in, base=root_path))

        if zip_mode and not os.path.exists(os.path.join(root_path, in_path)):
            error_msg = f'Cannot match path outside RootDir: "{root_path}" not in "{in_path}"'
            log.error(error_msg)
            raise ZipError(error_msg)

        if not os.path.isdir(in_path):
            error_msg = f'Cannot match path that does not exist or is not a directory: "{in_path}"'
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

        yield from match_files(in_path, match_text,
                                         exclude_pattern=attr_exclude,
                                         user_path=attr_path,
                                         no_recurse=attr_no_recurse)
