import fnmatch
import glob
import logging
import os
import shutil
import sys
import typing
import zipfile

from lxml import etree

from pyro.CommandArguments import CommandArguments
from pyro.Comparators import (endswith,
                              is_include_node,
                              is_package_node,
                              is_zipfile_node,
                              startswith)
from pyro.CaseInsensitiveList import CaseInsensitiveList
from pyro.Enums.ZipCompression import ZipCompression
from pyro.PapyrusProject import PapyrusProject
from pyro.PathHelper import PathHelper
from pyro.ProcessManager import ProcessManager
from pyro.ProjectOptions import ProjectOptions


class PackageManager:
    log: logging.Logger = logging.getLogger('pyro')

    ppj: PapyrusProject = None
    options: ProjectOptions = None
    pak_extension: str = ''
    zip_extension: str = ''

    def __init__(self, ppj: PapyrusProject) -> None:
        self.ppj = ppj
        self.options = ppj.options

        self.pak_extension = '.ba2' if self.options.game_type == 'fo4' else '.bsa'
        self.zip_extension = '.zip'

    @staticmethod
    def _check_write_permission(file_path: str) -> None:
        if os.path.isfile(file_path):
            try:
                open(file_path, 'a').close()
            except PermissionError:
                PackageManager.log.error(f'Cannot create file without write permission to: "{file_path}"')
                sys.exit(1)

    @staticmethod
    def _generate_include_paths(includes_node: etree.ElementBase, root_path: str) -> typing.Generator:
        for include_node in filter(is_include_node, includes_node):
            no_recurse: bool = include_node.get('NoRecurse') == 'True'
            wildcard_pattern: str = '*' if no_recurse else r'**\*'

            if include_node.text.startswith(os.pardir):
                PackageManager.log.warning(f'Include paths cannot start with "{os.pardir}"')
                continue

            if include_node.text == os.curdir or include_node.text.startswith(os.curdir):
                include_node.text = include_node.text.replace(os.curdir, root_path, 1)

            # normalize path
            path_or_pattern = os.path.normpath(include_node.text)

            # populate files list using simple glob patterns
            if '*' in path_or_pattern:
                if not os.path.isabs(path_or_pattern):
                    search_path = os.path.join(root_path, wildcard_pattern)
                elif root_path in path_or_pattern:
                    search_path = path_or_pattern
                else:
                    PackageManager.log.warning(f'Cannot include path outside RootDir: "{path_or_pattern}"')
                    continue

                for include_path in glob.iglob(search_path, recursive=not no_recurse):
                    if os.path.isfile(include_path) and fnmatch.fnmatch(include_path, path_or_pattern):
                        yield include_path

            # populate files list using absolute paths
            elif os.path.isabs(path_or_pattern):
                if root_path not in path_or_pattern:
                    PackageManager.log.warning(f'Cannot include path outside RootDir: "{path_or_pattern}"')
                    continue

                if os.path.isfile(path_or_pattern):
                    yield path_or_pattern
                else:
                    search_path = os.path.join(path_or_pattern, wildcard_pattern)
                    yield from PathHelper.find_include_paths(search_path, no_recurse)

            else:
                # populate files list using relative file path
                test_path = os.path.join(root_path, path_or_pattern)
                if not os.path.isdir(test_path):
                    yield test_path

                # populate files list using relative folder path
                else:
                    search_path = os.path.join(root_path, path_or_pattern, wildcard_pattern)
                    yield from PathHelper.find_include_paths(search_path, no_recurse)

    def _fix_package_extension(self, package_name: str) -> str:
        if not endswith(package_name, ('.ba2', '.bsa'), ignorecase=True):
            return f'{package_name}{self.pak_extension}'
        return f'{os.path.splitext(package_name)[0]}{self.pak_extension}'

    def _fix_zip_extension(self, zip_name: str) -> str:
        if not endswith(zip_name, '.zip', ignorecase=True):
            return f'{zip_name}{self.zip_extension}'
        return f'{os.path.splitext(zip_name)[0]}{self.zip_extension}'

    def _try_resolve_project_relative_path(self, path: str) -> str:
        if os.path.isabs(path):
            return path

        test_path: str = os.path.normpath(os.path.join(self.ppj.project_path, path))

        return test_path if os.path.isdir(test_path) else ''

    def build_commands(self, containing_folder: str, output_path: str) -> str:
        """
        Builds command for creating package with BSArch
        """
        arguments = CommandArguments()

        arguments.append(self.options.bsarch_path, enquote_value=True)
        arguments.append('pack')
        arguments.append(containing_folder, enquote_value=True)
        arguments.append(output_path, enquote_value=True)

        if self.options.game_type == 'fo4':
            arguments.append('-fo4')
        elif self.options.game_type == 'sse':
            arguments.append('-sse')

            # SSE has an ctd bug with uncompressed textures in a bsa that
            # has an Embed Filenames flag on it, so force it to false.
            has_textures = False
            
            for f in glob.iglob(os.path.join(containing_folder, r'**/*'), recursive=True):
                if not os.path.isfile(f):
                    continue
                if endswith(f, '.dds', ignorecase=True):
                    has_textures = True
                    break

            if has_textures:
                arguments.append('-af:0x3')
        else:
            arguments.append('-tes5')

        return arguments.join()

    def create_packages(self) -> None:
        # clear temporary data
        if os.path.isdir(self.options.temp_path):
            shutil.rmtree(self.options.temp_path, ignore_errors=True)

        # ensure package path exists
        if not os.path.isdir(self.options.package_path):
            os.makedirs(self.options.package_path, exist_ok=True)

        file_names = CaseInsensitiveList()

        for i, package_node in enumerate(filter(is_package_node, self.ppj.packages_node)):
            file_name: str = package_node.get('Name')

            # prevent clobbering files previously created in this session
            if file_name in file_names:
                file_name = f'{self.ppj.project_name} ({i})'

            if file_name not in file_names:
                file_names.append(file_name)

            file_name = self._fix_package_extension(file_name)

            file_path: str = os.path.join(self.options.package_path, file_name)

            self._check_write_permission(file_path)

            PackageManager.log.info(f'Creating "{file_name}"...')

            for source_path in self._generate_include_paths(package_node, package_node.get('RootDir')):
                PackageManager.log.info(f'+ "{source_path}"')

                relpath = os.path.relpath(source_path, package_node.get('RootDir'))
                target_path = os.path.join(self.options.temp_path, relpath)

                # fix target path if user passes a deeper package root (RootDir)
                if endswith(source_path, '.pex', ignorecase=True) and not startswith(relpath, 'scripts', ignorecase=True):
                    target_path = os.path.join(self.options.temp_path, 'Scripts', relpath)

                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                shutil.copy2(source_path, target_path)

            # run bsarch
            command: str = self.build_commands(self.options.temp_path, file_path)
            ProcessManager.run_bsarch(command)

            # clear temporary data
            if os.path.isdir(self.options.temp_path):
                shutil.rmtree(self.options.temp_path, ignore_errors=True)

    def create_zip(self) -> None:
        # ensure zip output path exists
        if not os.path.isdir(self.options.zip_output_path):
            os.makedirs(self.options.zip_output_path, exist_ok=True)

        file_names = CaseInsensitiveList()

        for i, zip_node in enumerate(filter(is_zipfile_node, self.ppj.zip_files_node)):
            file_name: str = zip_node.get('Name')

            # prevent clobbering files previously created in this session
            if file_name in file_names:
                file_name = f'{file_name} ({i})'

            if file_name not in file_names:
                file_names.append(file_name)

            file_name = self._fix_zip_extension(file_name)

            file_path: str = os.path.join(self.options.zip_output_path, file_name)

            self._check_write_permission(file_path)

            try:
                if self.options.zip_compression in ('store', 'deflate'):
                    compress_type = ZipCompression[self.options.zip_compression]
                else:
                    compress_type = ZipCompression[zip_node.get('Compression')]
            except KeyError:
                compress_type = ZipCompression.STORE

            root_dir: str = zip_node.get('RootDir')
            zip_root_path: str = self._try_resolve_project_relative_path(root_dir)

            if zip_root_path:
                PackageManager.log.info(f'Creating "{file_name}"...')

                try:
                    with zipfile.ZipFile(file_path, mode='w', compression=compress_type.value) as z:
                        for include_path in self._generate_include_paths(zip_node, zip_root_path):
                            PackageManager.log.info(f'+ "{include_path}"')

                            if zip_root_path not in include_path:
                                PackageManager.log.warning(f'Cannot add file to ZIP outside RootDir: "{include_path}"')
                                continue

                            arcname: str = os.path.relpath(include_path, zip_root_path)
                            z.write(include_path, arcname, compress_type=compress_type.value)

                    PackageManager.log.info(f'Wrote ZIP file: "{file_path}"')
                except PermissionError:
                    PackageManager.log.error(f'Cannot open ZIP file for writing: "{file_path}"')
                    sys.exit(1)
            else:
                PackageManager.log.error(f'Cannot resolve RootDir path to existing folder: "{root_dir}"')
                sys.exit(1)
