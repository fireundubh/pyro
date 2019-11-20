import os
from collections import OrderedDict


class PathHelper:
    @staticmethod
    def try_append_existing(a: str, b: list) -> bool:
        if a not in b and os.path.exists(a):
            b.append(a)
            return True
        return False

    @staticmethod
    def try_append_abspath(a: str, b: list) -> bool:
        if a not in b and os.path.isabs(a) and os.path.exists(a):
            b.append(a)
            return True
        return False

    @staticmethod
    def nsify(path: str) -> tuple:
        """Returns tuple(parent folder, file name) from absolute path"""
        parent_folder, file_name = map(lambda x: os.path.basename(x), [os.path.dirname(path), path])
        return parent_folder, file_name

    @staticmethod
    def uniqify(items: list) -> list:
        """Returns ordered list without duplicates"""
        return list(OrderedDict.fromkeys(items))
