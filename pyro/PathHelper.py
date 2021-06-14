import os
from typing import (Generator,
                    Iterable)
from urllib.parse import (unquote_plus,
                          urlparse)

from wcmatch import wcmatch

from pyro.Comparators import (endswith,
                              startswith)


class PathHelper:
    @staticmethod
    def calculate_relative_object_name(script_path: str, import_paths: list) -> str:
        """Returns import-relative path from absolute path (should be used only for Fallout 4 paths)"""
        # reverse the list to find the best import path
        file_name = os.path.basename(script_path)

        for import_path in reversed(PathHelper.uniqify(import_paths)):
            if not os.path.isabs(import_path):
                import_path = os.path.join(os.getcwd(), import_path)

            import_path = os.path.normpath(import_path)

            if len(script_path) > len(import_path) and startswith(script_path, import_path, ignorecase=True):
                file_name = script_path[len(import_path):]
                if file_name[0] == '\\' or file_name[0] == '/':
                    file_name = file_name[1:]
                break

        return file_name

    @staticmethod
    def find_script_paths_from_folder(root_dir: str, *, no_recurse: bool, matcher: wcmatch.WcMatch = None) -> Generator:
        """Yields existing script paths starting from absolute folder path"""
        if not matcher:
            user_flags = wcmatch.RECURSIVE if not no_recurse else 0x0
            matcher = wcmatch.WcMatch(root_dir, '*.psc', flags=wcmatch.IGNORECASE | user_flags)
        for script_path in matcher.imatch():
            yield script_path

    @staticmethod
    def uniqify(items: Iterable) -> list:
        """Returns ordered list without duplicates"""
        return list(dict.fromkeys(items))

    @staticmethod
    def find_index_of_ancestor_import_path(implicit_path: str, import_paths: list) -> int:
        """Returns index of ancestor of implicit path in import paths"""
        for i, import_path in enumerate(import_paths):
            if import_path.casefold() in implicit_path.casefold():
                return i
        return -1

    @staticmethod
    def merge_implicit_import_paths(implicit_paths: list, import_paths: list) -> None:
        """Inserts orphan and descendant implicit paths into list of import paths at correct positions"""
        if not implicit_paths:
            return

        implicit_paths.sort()

        for implicit_path in reversed(PathHelper.uniqify(implicit_paths)):
            implicit_path = os.path.normpath(implicit_path)

            # do not add import paths that are already declared
            if any(endswith(x, implicit_path, ignorecase=True) for x in import_paths):
                continue

            # insert implicit path before ancestor import path, if ancestor exists
            i = PathHelper.find_index_of_ancestor_import_path(implicit_path, import_paths)
            if i > -1:
                import_paths.insert(i, implicit_path)
                continue

            # insert orphan implicit path at the first position
            import_paths.insert(0, implicit_path)

    @staticmethod
    def url2pathname(url_path: str) -> str:
        """Returns normalized unquoted path from URL"""
        url = urlparse(url_path)

        netloc: str = url.netloc
        path: str = url.path

        if netloc and startswith(netloc, '/'):
            netloc = netloc[1:]

        if path and startswith(path, '/'):
            path = path[1:]

        return os.path.normpath(unquote_plus(os.path.join(netloc, path)))
