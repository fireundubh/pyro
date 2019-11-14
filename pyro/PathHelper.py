import os


class PathHelper:
    @staticmethod
    def nsify(path: str) -> str:
        """Converts absolute paths to relative namespace paths"""
        namespace, file_name = map(lambda x: os.path.basename(x), [os.path.dirname(path), path])
        return os.path.join(namespace, file_name)

    @staticmethod
    def parse(path: str, default_path: str = '') -> str:
        """Support absolute paths, relative paths, and other paths"""
        if os.path.isabs(path):
            return os.path.normpath(path)

        # realpath supports curdir and pardir
        path = os.path.realpath(os.path.join(os.path.dirname(__file__), path))

        if not os.path.exists(path) and default_path:
            path = os.path.join(default_path, path)

        return os.path.normpath(path)
