import os
from collections import OrderedDict


class PathHelper:
    @staticmethod
    def try_append_existing(path: str, paths: list) -> bool:
        path = os.path.normpath(path)
        if path not in paths and os.path.exists(path):
            paths.append(path)
            return True
        return False

    @staticmethod
    def try_append_abspath(path: str, paths: list) -> bool:
        path = os.path.normpath(path)
        if path not in paths and os.path.isabs(path) and os.path.exists(path):
            paths.append(path)
            return True
        return False

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
