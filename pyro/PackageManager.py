import logging
import os
import shutil
import sys
import typing
import zipfile

from lxml import etree
from wcmatch import (glob,
                     wcmatch)

from pyro.CommandArguments import CommandArguments
from pyro.Comparators import (endswith,
                              is_include_node,
                              is_match_node,
                              is_package_node,
                              is_zipfile_node,
                              startswith)
from pyro.CaseInsensitiveList import CaseInsensitiveList
from pyro.Constants import (GameType,
                            XmlAttributeName)
from pyro.Enums.ZipCompression import ZipCompression
from pyro.PapyrusProject import PapyrusProject
from pyro.ProcessManager import ProcessManager
from pyro.ProjectOptions import ProjectOptions


class PackageManager:
    log: logging.Logger = logging.getLogger('pyro')

    ppj: PapyrusProject = None
    options: ProjectOptions = None
    pak_extension: str = ''
    zip_extension: str = ''

    DEFAULT_GLFLAGS = glob.NODIR | glob.MATCHBASE | glob.SPLIT | glob.REALPATH | glob.GLOBSTAR | glob.FOLLOW | glob.IGNORECASE | glob.MINUSNEGATE
    DEFAULT_WCFLAGS = wcmatch.SYMLINKS | wcmatch.IGNORECASE | wcmatch.MINUSNEGATE

    def __init__(self, ppj: PapyrusProject) -> None:
        self.ppj = ppj
        self.options = ppj.options

        self.pak_extension = '.ba2' if self.options.game_type == GameType.FO4 else '.bsa'
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
    def _generate_include_paths(includes_node: etree.ElementBase, root_path: str, zip_mode: bool = False) -> typing.Generator:
        for include_node in filter(is_include_node, includes_node):
            attr_no_recurse: bool = include_node.get(XmlAttributeName.NO_RECURSE) == 'True'
            attr_path: str = (include_node.get(XmlAttributeName.PATH) or '').strip()
            search_path: str = include_node.text.strip()

            if not search_path:
                PackageManager.log.error(f'Include path at line {include_node.sourceline} in project file is empty')
                sys.exit(1)

            if not zip_mode and startswith(search_path, os.pardir):
                PackageManager.log.error(f'Include paths cannot start with "{os.pardir}"')
                sys.exit(1)

            if startswith(search_path, os.curdir):
                search_path = search_path.replace(os.curdir, root_path, 1)

            # fix invalid pattern with leading separator
            if not zip_mode and startswith(search_path, (os.path.sep, os.path.altsep)):
                search_path = '**' + search_path

            if '\\' in search_path:
                search_path = search_path.replace('\\', '/')

            # populate files list using glob patterns or relative paths
            if '*' in search_path:
                for include_path in glob.iglob(search_path,
                                               root_dir=root_path,
                                               flags=PackageManager.DEFAULT_GLFLAGS):
                    yield include_path, attr_path

            elif not os.path.isabs(search_path):
                test_path = os.path.normpath(os.path.join(root_path, search_path))
                if os.path.isfile(test_path):
                    yield test_path, attr_path
                elif os.path.isdir(test_path):
                    user_flags = wcmatch.RECURSIVE if not attr_no_recurse else 0x0
                    matcher = wcmatch.WcMatch(test_path, '*.*', flags=wcmatch.IGNORECASE | user_flags)

                    matcher.on_reset()
                    matcher._skipped = 0
                    for f in matcher._walk():
                        yield f, attr_path
                else:
                    for include_path in glob.iglob(search_path,
                                                   root_dir=root_path,
                                                   flags=PackageManager.DEFAULT_GLFLAGS):
                        yield include_path, attr_path

            # populate files list using absolute paths
            else:
                if not zip_mode and root_path not in search_path:
                    PackageManager.log.error(f'Cannot include path outside RootDir: "{search_path}"')
                    sys.exit(1)

                search_path = os.path.abspath(os.path.normpath(search_path))

                if os.path.isfile(search_path):
                    yield search_path, attr_path
                else:
                    user_flags = wcmatch.RECURSIVE if not attr_no_recurse else 0x0

                    matcher = wcmatch.WcMatch(search_path, '*.*',
                                              flags=PackageManager.DEFAULT_WCFLAGS | user_flags)

                    matcher.on_reset()
                    matcher._skipped = 0
                    for f in matcher._walk():
                        yield f, attr_path

        for match_node in filter(is_match_node, includes_node):
            attr_in: str = match_node.get(XmlAttributeName.IN).strip()
            attr_no_recurse: bool = match_node.get(XmlAttributeName.NO_RECURSE) == 'True'
            attr_exclude: str = (match_node.get(XmlAttributeName.EXCLUDE) or '').strip()

            if not attr_in:
                PackageManager.log.error(f'Include path at line {match_node.sourceline} in project file is empty')
                sys.exit(1)

            in_path: str = os.path.normpath(attr_in)

            if in_path == os.curdir:
                in_path = in_path.replace(os.curdir, root_path, 1)
            elif in_path == os.pardir:
                in_path = in_path.replace(os.pardir, os.path.normpath(os.path.join(root_path, os.pardir)), 1)
            elif os.path.sep in os.path.normpath(in_path):
                if startswith(in_path, os.pardir):
                    in_path = in_path.replace(os.pardir, os.path.normpath(os.path.join(root_path, os.pardir)), 1)
                elif startswith(in_path, os.curdir):
                    in_path = in_path.replace(os.curdir, root_path, 1)

            if not os.path.isabs(in_path):
                in_path = os.path.join(root_path, in_path)
            elif zip_mode and root_path not in in_path:
                PackageManager.log.error(f'Cannot match path outside RootDir: "{in_path}"')
                sys.exit(1)

            if not os.path.isdir(in_path):
                PackageManager.log.error(f'Cannot match path that does not exist or is not a directory: "{in_path}"')
                sys.exit(1)

            user_flags = wcmatch.RECURSIVE if not attr_no_recurse else 0x0

            matcher = wcmatch.WcMatch(in_path, match_node.text,
                                      exclude_pattern=attr_exclude,
                                      flags=PackageManager.DEFAULT_WCFLAGS | user_flags)

            matcher.on_reset()
            matcher._skipped = 0
            for f in matcher._walk():
                yield f, attr_in

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

        if self.options.game_type == GameType.FO4:
            arguments.append('-fo4')
        elif self.options.game_type == GameType.SSE:
            arguments.append('-sse')

            # SSE has an ctd bug with uncompressed textures in a bsa that
            # has an Embed Filenames flag on it, so force it to false.
            for _ in wcmatch.WcMatch(containing_folder, '*.dds',
                                     flags=wcmatch.RECURSIVE | wcmatch.IGNORECASE).imatch():
                arguments.append('-af:0x3')
                break
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
            attr_file_name: str = package_node.get(XmlAttributeName.NAME)

            # noinspection PyProtectedMember
            root_dir = self.ppj._get_path(package_node.get(XmlAttributeName.ROOT_DIR),
                                          relative_root_path=self.ppj.project_path,
                                          fallback_path=[self.ppj.project_path, os.path.basename(attr_file_name)])

            # prevent clobbering files previously created in this session
            if attr_file_name in file_names:
                attr_file_name = f'{self.ppj.project_name} ({i})'

            if attr_file_name not in file_names:
                file_names.append(attr_file_name)

            attr_file_name = self._fix_package_extension(attr_file_name)

            file_path: str = os.path.join(self.options.package_path, attr_file_name)

            self._check_write_permission(file_path)

            PackageManager.log.info(f'Creating "{attr_file_name}"...')

            for source_path, _ in self._generate_include_paths(package_node, root_dir):
                if os.path.isabs(source_path):
                    relpath = os.path.relpath(source_path, root_dir)
                else:
                    relpath = source_path
                    source_path = os.path.join(self.ppj.project_path, source_path)

                target_path = os.path.join(self.options.temp_path, relpath)

                PackageManager.log.info(f'+ "{relpath.casefold()}"')

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
            attr_file_name: str = zip_node.get(XmlAttributeName.NAME)

            # prevent clobbering files previously created in this session
            if attr_file_name in file_names:
                attr_file_name = f'{attr_file_name} ({i})'

            if attr_file_name not in file_names:
                file_names.append(attr_file_name)

            attr_file_name = self._fix_zip_extension(attr_file_name)

            file_path: str = os.path.join(self.options.zip_output_path, attr_file_name)

            self._check_write_permission(file_path)

            try:
                if self.options.zip_compression in ('store', 'deflate'):
                    compress_type = ZipCompression[self.options.zip_compression]
                else:
                    compress_type = ZipCompression[zip_node.get(XmlAttributeName.COMPRESSION)]
            except KeyError:
                compress_type = ZipCompression.STORE

            attr_root_dir: str = zip_node.get(XmlAttributeName.ROOT_DIR)
            zip_root_path: str = self._try_resolve_project_relative_path(attr_root_dir)

            if zip_root_path:
                PackageManager.log.info(f'Creating "{attr_file_name}"...')

                try:
                    with zipfile.ZipFile(file_path, mode='w', compression=compress_type.value) as z:
                        for include_path, user_path in self._generate_include_paths(zip_node, zip_root_path, True):
                            if not user_path:
                                if zip_root_path in include_path:
                                    arcname = os.path.relpath(include_path, zip_root_path)
                                else:
                                    # just add file to zip root
                                    arcname = os.path.basename(include_path)
                            else:
                                _, attr_file_name = os.path.split(include_path)
                                arcname = attr_file_name if user_path == os.curdir else os.path.join(user_path, attr_file_name)

                            PackageManager.log.info('+ "{}"'.format(arcname))
                            z.write(include_path, arcname, compress_type=compress_type.value)

                    PackageManager.log.info(f'Wrote ZIP file: "{file_path}"')
                except PermissionError:
                    PackageManager.log.error(f'Cannot open ZIP file for writing: "{file_path}"')
                    sys.exit(1)
            else:
                PackageManager.log.error(f'Cannot resolve RootDir path to existing folder: "{attr_root_dir}"')
                sys.exit(1)
