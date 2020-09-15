import glob
import os
from collections import OrderedDict
from typing import Generator, Iterable
from urllib.parse import unquote_plus, urlparse

from pyro.Comparators import endswith, startswith


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

            if len(script_path) > len(import_path):
                if startswith(script_path, import_path, ignorecase=True):
                    file_name = script_path[len(import_path):]
                    if file_name[0] == '\\' or file_name[0] == '/':
                        file_name = file_name[1:]
                    break

        return file_name

    @staticmethod
    def find_include_paths(search_path: str, no_recurse: bool) -> Generator:
        """Yields existing file paths from absolute search path"""
        for include_path in glob.iglob(search_path, recursive=not no_recurse):
            if os.path.isfile(include_path):
                yield include_path

    @staticmethod
    def find_script_paths_from_folder(folder_path: str, no_recurse: bool) -> Generator:
        """Yields existing script paths starting from absolute folder path"""
        search_path: str = os.path.join(folder_path, '*' if no_recurse else r'**\*')
        for script_path in glob.iglob(search_path, recursive=not no_recurse):
            if os.path.isfile(script_path) and endswith(script_path, '.psc', ignorecase=True):
                yield script_path

    @staticmethod
    def uniqify(items: Iterable) -> list:
        """Returns ordered list without duplicates"""
        return list(OrderedDict.fromkeys(items))

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
            if implicit_path in import_paths:
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

        if netloc and netloc.startswith('/'):
            netloc = netloc[1:]

        if path and path.startswith('/'):
            path = path[1:]

        return os.path.normpath(unquote_plus(os.path.join(netloc, path)))
