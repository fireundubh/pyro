"""Builder for creating ZIP archives using Python's zipfile module."""
import concurrent.futures
import logging
import os
import threading
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from pyro.CaseInsensitiveList import CaseInsensitiveList
from pyro.Comparators import endswith, is_zipfile_node
from pyro.Constants import XmlAttributeName
from pyro.Exceptions import ZipError
from pyro.PapyrusProject import PapyrusProject
from pyro.PathHelper import PathHelper
from pyro.builders.utils import check_write_permission, generate_include_paths


class ZipArchiveBuilder:
    """Creates ZIP archives using Python's zipfile module."""

    log: logging.Logger = logging.getLogger('pyro')

    ppj: PapyrusProject
    zip_extension: str = '.zip'
    includes: int = 0

    COMPRESS_TYPE = {'store': 0, 'deflate': 8}

    def __init__(self, ppj: PapyrusProject) -> None:
        self.ppj = ppj
        self.log.setLevel(self.ppj.log.level)

    def _fix_zip_extension(self, zip_name: str) -> str:
        """Ensure ZIP name has correct .zip extension."""
        if not endswith(zip_name, '.zip', ignorecase=True):
            return f'{zip_name}{self.zip_extension}'
        return f'{os.path.splitext(zip_name)[0]}{self.zip_extension}'

    def create_zip(self) -> None:
        """Process all <ZipFile> nodes from project XML."""
        # ensure zip output path exists
        if not os.path.isdir(self.ppj.options.zip_output_path):
            os.makedirs(self.ppj.options.zip_output_path, exist_ok=True)

        file_names = CaseInsensitiveList()

        for i, zip_node in enumerate(filter(is_zipfile_node, self.ppj.zip_files_node)):
            attr_file_name: str = zip_node.get(XmlAttributeName.NAME)

            # prevent clobbering files previously created in this session
            if attr_file_name in file_names:
                attr_file_name = f'{attr_file_name} ({i})'

            if attr_file_name not in file_names:
                file_names.append(attr_file_name)

            attr_file_name = self._fix_zip_extension(attr_file_name)

            file_path: str = os.path.join(self.ppj.options.zip_output_path, attr_file_name)

            check_write_permission(file_path)

            compress_str: str = self.ppj.options.zip_compression or zip_node.get(XmlAttributeName.COMPRESSION)

            try:
                compress_type = self.COMPRESS_TYPE[compress_str.casefold()]
            except KeyError:
                ZipArchiveBuilder.log.error(f'"{compress_str}" is not a valid compression type, defaulting to STORE')
                compress_type = 0

            root_dir: str = self.ppj._get_path(zip_node.get(XmlAttributeName.ROOT_DIR),
                                               relative_root_path=self.ppj.project_path,
                                               fallback_path=self.ppj.project_path)

            root_dir = PathHelper.normalize_relative_path(root_dir, self.ppj.project_path)

            if root_dir and os.path.isdir(root_dir):
                ZipArchiveBuilder.log.info(f'Creating "{attr_file_name}"...')

                tasks = []

                root_p = Path(root_dir)  # Pre-compute for reuse

                for ip, ap in generate_include_paths(zip_node, root_dir, True):
                    attr_path = PathHelper.normalize_relative_path(ap, self.ppj.project_path) if ap else ''

                    # FIX: Resolve ip to absolute if relative (handles yields from _match as rel to root_dir)
                    if os.path.isabs(ip):
                        include_path_abs = ip
                    else:
                        include_path_abs = os.path.normpath(os.path.join(root_dir, ip))

                    include_path = Path(include_path_abs)

                    if not attr_path:
                        try:
                            rel_to_root = include_path.relative_to(root_p)
                            arcname = str(rel_to_root)  # POSIX '/' for ZIP
                            if ZipArchiveBuilder.log.level > logging.INFO:
                                ZipArchiveBuilder.log.warning(f'Relative arcname from "{include_path}" (resolved from rel "{ip}") to "{root_p}": {arcname}')
                        except ValueError:
                            # TRUE drive mismatch or invalid subpath: log with details
                            if ZipArchiveBuilder.log.level > logging.INFO:
                                root_drive = root_p.drive or 'N/A (relative)'
                                include_drive = include_path.drive or 'N/A (relative)'
                                if root_drive != include_drive and root_drive != 'N/A (relative)':
                                    ZipArchiveBuilder.log.warning(f'True drive mismatch: root={root_drive}, include={include_drive} for resolved "{include_path}"; using basename: {include_path.name}')
                                else:
                                    ZipArchiveBuilder.log.warning(f'Same drive ({root_drive}) but resolved "{include_path}" not under "{root_p}"; using basename: {include_path.name}')

                            arcname = include_path.name
                    else:
                        try:
                            rel_to_root = include_path.relative_to(root_p)
                            arcname = str(rel_to_root) if attr_path == os.curdir else os.path.join(attr_path, str(rel_to_root))
                            if ZipArchiveBuilder.log.level > logging.INFO:
                                ZipArchiveBuilder.log.warning(f'Relative arcname under {attr_path} from "{include_path}" (resolved from rel "{ip}") to "{root_p}": {arcname}')
                        except ValueError:
                            # TRUE drive mismatch or invalid subpath: log with details
                            fallback_arc = include_path.name if attr_path == os.curdir else os.path.join(attr_path, include_path.name)

                            if ZipArchiveBuilder.log.level > logging.INFO:
                                root_drive = root_p.drive or 'N/A (relative)'
                                include_drive = include_path.drive or 'N/A (relative)'

                                if root_drive != include_drive and root_drive != 'N/A (relative)':
                                    ZipArchiveBuilder.log.warning(f'True drive mismatch under {attr_path}: root={root_drive}, include={include_drive} for resolved "{include_path}"; flattening to {fallback_arc}')
                                else:
                                    ZipArchiveBuilder.log.warning(f'Same drive ({root_drive}) under {attr_path} but resolved "{include_path}" not under "{root_p}"; flattening to {fallback_arc}')

                            arcname = fallback_arc

                    tasks.append((include_path_abs, arcname))
                    ZipArchiveBuilder.log.info(f'+ "{arcname}"')

                self.includes = len(tasks)

                if self.includes > 0:
                    def add_to_zip(zf: zipfile.ZipFile, fn: str, an: str, lk: threading.Lock) -> None:
                        with lk:
                            zf.write(fn, an)

                    lock = threading.Lock()
                    worker_limit = min(self.includes, self.ppj.options.worker_limit)
                    with zipfile.ZipFile(file_path, mode='w', compression=compress_type) as z:
                        with ThreadPoolExecutor(max_workers=worker_limit) as executor:
                            futures = []
                            for include_path_abs, arcname in tasks:
                                future = executor.submit(add_to_zip, z, include_path_abs, arcname, lock)
                                futures.append(future)
                            concurrent.futures.wait(futures)

                    ZipArchiveBuilder.log.info(f'Wrote ZIP file: "{file_path}"')
            else:
                error_msg = f'Cannot resolve RootDir path to existing folder: "{root_dir}"'
                ZipArchiveBuilder.log.error(error_msg)
                raise ZipError(error_msg)
