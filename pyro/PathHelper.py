import os
from collections import OrderedDict


class PathHelper:
    @staticmethod
    def calculate_relative_object_name(path: str, import_paths: list) -> str:
        """Returns import-relative path from absolute path (should be used only for Fallout 4 paths)"""
        # reverse the list to find the best import path
        for import_path in reversed(import_paths):
            import_path = os.path.normpath(import_path)
            if len(path) > len(import_path) and import_path in path:
                relative_path = os.path.relpath(path, import_path)
                return relative_path
        raise ValueError('Cannot build import-relative path from absolute path: "%s"' % path)

    @staticmethod
    def uniqify(items: list) -> list:
        """Returns ordered list without duplicates"""
        return list(OrderedDict.fromkeys(items))

    @staticmethod
    def find_index_of_ancestor_import_path(implicit_path: str, import_paths: list) -> int:
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
