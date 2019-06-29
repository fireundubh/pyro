import os
import posixpath


class PathHelper:
    @staticmethod
    def compare(source_path: str, target_path: str) -> bool:
        if source_path == target_path:
            return True
        if os.path.normpath(source_path) == os.path.normpath(target_path):
            return True
        if posixpath.normpath(source_path) == posixpath.normpath(target_path):
            return True
        if not os.path.isabs(target_path):
            if os.path.normpath(source_path).endswith(os.path.normpath(target_path)):
                return True
            if posixpath.normpath(source_path).endswith(posixpath.normpath(target_path)):
                return True
        return False

    @staticmethod
    def parse(ini_path: str, default_path: str = '') -> str:
        """Support absolute INI paths, relative local paths, and other paths"""
        if os.path.isabs(ini_path):
            return os.path.normpath(ini_path)

        # realpath supports curdir and pardir
        path = os.path.realpath(os.path.join(os.path.dirname(__file__), ini_path))

        if not os.path.exists(path) and default_path:
            path = os.path.join(default_path, ini_path)

        return os.path.normpath(path)
