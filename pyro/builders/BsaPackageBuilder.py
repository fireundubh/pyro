"""Builder for creating BSA/BA2 archives using external BSArch tool."""
import concurrent.futures
import logging
import os
import shutil
from concurrent.futures import ThreadPoolExecutor

from wcmatch import wcmatch

from pyro.CaseInsensitiveList import CaseInsensitiveList
from pyro.CommandArguments import CommandArguments
from pyro.Comparators import endswith, is_package_node, startswith
from pyro.Constants import GameType, XmlAttributeName
from pyro.Exceptions import PackagingError
from pyro.PapyrusProject import PapyrusProject
from pyro.PathHelper import PathHelper
from pyro.ProcessManager import ProcessManager
from pyro.builders.utils import check_write_permission, generate_include_paths


class BsaPackageBuilder:
    """Creates BSA/BA2 archives using external BSArch tool."""

    log: logging.Logger = logging.getLogger('pyro')

    ppj: PapyrusProject
    pak_extension: str = ''
    includes: int = 0

    def __init__(self, ppj: PapyrusProject) -> None:
        self.ppj = ppj
        self.log.setLevel(self.ppj.log.level)
        self.pak_extension = '.ba2' if self.ppj.options.game_type == GameType.FO4 else '.bsa'

    @staticmethod
    def _can_compress_package(containing_folder: str) -> bool:
        """Check if package can be safely compressed (no voices, sounds, or strings)."""
        flags = wcmatch.RECURSIVE | wcmatch.IGNORECASE

        # voices bad because bethesda no likey
        for _ in wcmatch.WcMatch(containing_folder, '*.fuz', flags=flags).imatch():
            return False

        # sounds bad because bethesda no likey
        for _ in wcmatch.WcMatch(containing_folder, '*.wav|*.xwm', flags=flags).imatch():
            return False

        # strings bad because wrye bash no likey
        for _ in wcmatch.WcMatch(containing_folder, '*.*strings', flags=flags).imatch():
            return False

        return True

    def _fix_package_extension(self, package_name: str) -> str:
        """Ensure package name has correct .ba2 or .bsa extension."""
        if not endswith(package_name, ('.ba2', '.bsa'), ignorecase=True):
            return f'{package_name}{self.pak_extension}'
        return f'{os.path.splitext(package_name)[0]}{self.pak_extension}'

    def build_commands(self, containing_folder: str, output_path: str) -> list[str]:
        """Build BSArch command as list for subprocess."""
        arguments = CommandArguments()

        arguments.append(self.ppj.options.bsarch_path, enquote_value=True)
        arguments.append('pack')
        arguments.append(containing_folder, enquote_value=True)
        arguments.append(output_path, enquote_value=True)

        compressed_package = BsaPackageBuilder._can_compress_package(containing_folder)

        flags = wcmatch.RECURSIVE | wcmatch.IGNORECASE

        if self.ppj.options.game_type == GameType.FO4 or self.ppj.options.game_type == GameType.SF1:
            for _ in wcmatch.WcMatch(containing_folder, '!*.dds', flags=flags).imatch():
                arguments.append('-fo4')
                break
            else:
                arguments.append('-fo4dds')
        elif self.ppj.options.game_type == GameType.SSE:
            arguments.append('-sse')

            if not compressed_package:
                # SSE crashes when uncompressed BSA has Embed Filenames flag and contains textures
                for _ in wcmatch.WcMatch(containing_folder, '*.dds', flags=flags).imatch():
                    arguments.append('-af:0x3')
                    break
        else:
            arguments.append('-tes5')

        # binary identical files share same data to preserve space
        arguments.append('-share')

        if compressed_package:
            arguments.append('-z')

        return arguments.to_list()

    def create_packages(self) -> None:
        """Process all <Package> nodes from project XML."""
        # clear temporary data
        if os.path.isdir(self.ppj.options.temp_path):
            shutil.rmtree(self.ppj.options.temp_path, ignore_errors=True)

        # ensure package path exists
        if not os.path.isdir(self.ppj.options.package_path):
            os.makedirs(self.ppj.options.package_path, exist_ok=True)

        file_names = CaseInsensitiveList()

        for i, package_node in enumerate(filter(is_package_node, self.ppj.packages_node)):
            attr_file_name: str = package_node.get(XmlAttributeName.NAME)

            # noinspection PyProtectedMember
            root_dir: str = self.ppj._get_path(package_node.get(XmlAttributeName.ROOT_DIR),
                                               relative_root_path=self.ppj.project_path,
                                               fallback_path=[self.ppj.project_path, os.path.basename(attr_file_name)])

            root_dir = PathHelper.normalize_relative_path(root_dir, self.ppj.project_path) if root_dir else ''

            if root_dir and os.path.isdir(root_dir):
                # prevent clobbering files previously created in this session
                if attr_file_name in file_names:
                    attr_file_name = f'{self.ppj.project_name} ({i})'

                if attr_file_name not in file_names:
                    file_names.append(attr_file_name)

                attr_file_name = self._fix_package_extension(attr_file_name)

                file_path: str = os.path.join(self.ppj.options.package_path, attr_file_name)

                check_write_permission(file_path)

                BsaPackageBuilder.log.info(f'Creating "{attr_file_name}"...')

                tasks = []

                for source_path, raw_attr_path in generate_include_paths(package_node, root_dir):
                    # Normalize attr_path once (user-provided relative)
                    attr_path = PathHelper.normalize_relative_path(raw_attr_path, self.ppj.project_path) if raw_attr_path else ''

                    if os.path.isabs(source_path):
                        relpath: str = os.path.relpath(source_path, root_dir)
                    else:
                        relpath = source_path  # Already normalized upstream
                        source_path = os.path.join(self.ppj.project_path, relpath)  # But re-norm if needed

                    adj_relpath = os.path.normpath(os.path.join(attr_path, relpath))  # Keep for join safety

                    BsaPackageBuilder.log.info(f'+ "{adj_relpath.casefold()}"')

                    target_path: str = os.path.join(self.ppj.options.temp_path, adj_relpath)

                    # fix target path if user passes a deeper package root (RootDir)
                    if endswith(source_path, '.pex', ignorecase=True) and not startswith(relpath, 'scripts', ignorecase=True):
                        target_path = os.path.join(self.ppj.options.temp_path, 'Scripts', relpath)

                    tasks.append((source_path, target_path))

                self.includes = len(tasks)

                def copy_task_fn(s: str, t: str) -> None:
                    os.makedirs(os.path.dirname(t), exist_ok=True)
                    shutil.copy2(s, t)

                worker_limit = min(self.includes, self.ppj.options.worker_limit)
                with ThreadPoolExecutor(max_workers=worker_limit) as executor:
                    futures = [executor.submit(copy_task_fn, source_path, target_path)
                               for source_path, target_path in tasks]
                    concurrent.futures.wait(futures)

                # run bsarch
                command: list[str] = self.build_commands(self.ppj.options.temp_path, file_path)
                ProcessManager.run_bsarch(command)

                # clear temporary data
                if os.path.isdir(self.ppj.options.temp_path):
                    shutil.rmtree(self.ppj.options.temp_path, ignore_errors=True)
            else:
                error_msg = f'Cannot resolve RootDir path to existing folder: "{root_dir}"'
                BsaPackageBuilder.log.error(error_msg)
                raise PackagingError(error_msg)
