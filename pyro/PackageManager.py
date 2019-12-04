import fnmatch
import glob
import os
import shutil
import sys
import typing
import zipfile

from lxml import etree

from pyro.CommandArguments import CommandArguments
from pyro.Logger import Logger
from pyro.PapyrusProject import PapyrusProject
from pyro.ProcessManager import ProcessManager


class PackageManager(Logger):
    def __init__(self, ppj: PapyrusProject) -> None:
        self.ppj = ppj
        self.options = ppj.options

        self.extension: str = '.ba2' if self.options.game_type == 'fo4' else '.bsa'

    @staticmethod
    def _find_include_paths(search_path: str, no_recurse: bool) -> typing.Generator:
        for include_path in glob.iglob(search_path, recursive=not no_recurse):
            if os.path.isfile(include_path):
                yield include_path

    def _fix_package_extension(self, package_name: str) -> str:
        if not package_name.casefold().endswith(('.ba2', '.bsa')):
            return '%s%s' % (package_name, self.extension)
        return '%s%s' % (os.path.splitext(package_name)[0], self.extension)

    def _generate_include_paths(self, parent_node: etree.ElementBase, root_path: str) -> typing.Generator:
        for include_node in parent_node:
            if not include_node.tag.endswith('Include'):
                continue

            no_recurse: bool = include_node.get('NoRecurse') == 'True'
            wildcard_pattern: str = '*' if no_recurse else r'**\*'

            if include_node.text.startswith(os.pardir):
                PackageManager.log.warning('Include paths cannot start with ".."')
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
                    PackageManager.log.warning('Cannot include path outside RootDir: "%s"' % path_or_pattern)
                    continue

                for include_path in glob.iglob(search_path, recursive=not no_recurse):
                    if os.path.isfile(include_path) and fnmatch.fnmatch(include_path, path_or_pattern):
                        yield include_path

            # populate files list using absolute paths
            elif os.path.isabs(path_or_pattern):
                if root_path not in path_or_pattern:
                    PackageManager.log.warning('Cannot include path outside RootDir: "%s"' % path_or_pattern)
                    continue

                if os.path.isfile(path_or_pattern):
                    yield path_or_pattern
                else:
                    search_path = os.path.join(path_or_pattern, wildcard_pattern)
                    yield from self._find_include_paths(search_path, no_recurse)

            else:
                # populate files list using relative file path
                test_path = os.path.join(root_path, path_or_pattern)
                if not os.path.isdir(test_path):
                    yield test_path

                # populate files list using relative folder path
                else:
                    search_path = os.path.join(root_path, path_or_pattern, wildcard_pattern)
                    yield from self._find_include_paths(search_path, no_recurse)

    def build_commands(self, containing_folder: str, output_path: str) -> str:
        """Returns arguments for BSArch as a string"""
        arguments = CommandArguments()

        arguments.append_quoted(self.options.bsarch_path)
        arguments.append('pack')
        arguments.append_quoted(containing_folder)
        arguments.append_quoted(output_path)

        if self.options.game_type == 'fo4':
            arguments.append('-fo4')
        elif self.options.game_type == 'sse':
            arguments.append('-sse')
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

        package_names: list = []

        for i, package_node in enumerate(self.ppj.packages_node):
            if not package_node.tag.endswith('Package'):
                continue

            package_name: str = package_node.get('Name')

            # ensure successive package names do not conflict if project name is used
            if i > 0 and (package_name == self.ppj.project_name or package_name in package_names):
                package_name = '%s (%s)' % (self.ppj.project_name, i)

            if package_name.casefold() not in package_names:
                package_names.append(package_name.casefold())

            package_name = self._fix_package_extension(package_name)

            package_path: str = os.path.join(self.options.package_path, package_name)

            if os.path.isfile(package_path):
                try:
                    open(package_path, 'a').close()
                except PermissionError:
                    PackageManager.log.error('Cannot create package without write permission to file: "%s"' % package_path)
                    sys.exit(1)

            PackageManager.log.info('Creating "%s"...' % package_name)

            for source_path in self._generate_include_paths(package_node, package_node.get('RootDir')):
                PackageManager.log.info('+ "%s"' % source_path)

                relpath = os.path.relpath(source_path, package_node.get('RootDir'))
                target_path = os.path.join(self.options.temp_path, relpath)

                # fix target path if user passes a deeper package root (RootDir)
                if source_path.casefold().endswith('.pex') and not relpath.casefold().startswith('scripts'):
                    target_path = os.path.join(self.options.temp_path, 'Scripts', relpath)

                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                shutil.copy2(source_path, target_path)

            # run bsarch
            commands: str = self.build_commands(self.options.temp_path, package_path)
            ProcessManager.run(commands, use_bsarch=True)

            # clear temporary data
            if os.path.isdir(self.options.temp_path):
                shutil.rmtree(self.options.temp_path, ignore_errors=True)

    def create_zip(self) -> None:
        PackageManager.log.info('Creating "%s"...' % self.ppj.zip_file_name)

        # ensure that zip output folder exists
        zip_output_path: str = os.path.join(self.options.zip_output_path, self.ppj.zip_file_name)
        os.makedirs(os.path.dirname(zip_output_path), exist_ok=True)

        try:
            with zipfile.ZipFile(zip_output_path, mode='w', compression=self.ppj.compress_type) as z:
                for include_path in self._generate_include_paths(self.ppj.zip_file_node, self.ppj.zip_root_path):
                    PackageManager.log.info('+ "%s"' % include_path)

                    if self.ppj.zip_root_path not in include_path:
                        PackageManager.log.warning('Cannot add file to ZIP outside RootDir: "%s"' % include_path)
                        continue

                    arcname: str = os.path.relpath(include_path, self.ppj.zip_root_path)
                    z.write(include_path, arcname, compress_type=self.ppj.compress_type)

            PackageManager.log.info('Wrote ZIP file: "%s"' % zip_output_path)
        except PermissionError:
            PackageManager.log.error('Cannot open ZIP file for writing: "%s"' % zip_output_path)
            sys.exit(1)
