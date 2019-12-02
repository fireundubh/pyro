import fnmatch
import glob
import os
import shutil
import sys
import zipfile

from lxml import etree

from pyro.CommandArguments import CommandArguments
from pyro.ElementHelper import ElementHelper
from pyro.Logger import Logger
from pyro.PapyrusProject import PapyrusProject
from pyro.PathHelper import PathHelper
from pyro.ProcessManager import ProcessManager


class PackageManager(Logger):
    def __init__(self, ppj: PapyrusProject) -> None:
        self.ppj = ppj
        self.options = ppj.options

        self.extension: str = '.ba2' if self.options.game_type == 'fo4' else '.bsa'

        self.package_paths: list = []

    def _fix_package_extension(self, package_name: str) -> str:
        if not package_name.casefold().endswith(('.ba2', '.bsa')):
            return '%s%s' % (package_name, self.extension)
        return '%s%s' % (os.path.splitext(package_name)[0], self.extension)

    def _populate_include_paths(self, parent_node: etree.ElementBase, root_path: str) -> list:
        include_paths: list = []

        for include_node in parent_node:
            if not include_node.tag.endswith('Include'):
                continue

            no_recurse: bool = self.ppj.get_attr_as_bool(include_node, 'NoRecurse')
            wildcard_pattern: str = '*' if no_recurse else r'**\*'

            include_text: str = self.ppj.parse(include_node.text)

            if include_text.startswith(os.pardir):
                PackageManager.log.warning('Include paths cannot start with ".."')
                continue

            if include_text == os.curdir or include_text.startswith(os.curdir):
                include_text = include_text.replace(os.curdir, root_path, 1)

            # normalize path
            include_path: str = os.path.normpath(include_text)

            # populate files list using simple glob patterns
            if '*' in include_path:
                if not os.path.isabs(include_path):
                    search_path: str = os.path.join(root_path, wildcard_pattern)
                elif root_path in include_path:
                    # pass include path as pattern
                    search_path = include_path
                else:
                    PackageManager.log.warning('Cannot include path outside RootDir: "%s"' % include_path)
                    continue

                search_path = os.path.normpath(search_path)
                files: list = [f for f in glob.iglob(search_path, recursive=not no_recurse) if os.path.isfile(f)]

                matches: list = fnmatch.filter(files, include_path)
                if not matches:
                    PackageManager.log.warning('No files in "%s" matched glob pattern: %s' % (search_path, include_text))
                    continue

                include_paths.extend(matches)
                continue

            # populate files list using absolute paths
            if os.path.isabs(include_path):
                if root_path not in include_path:
                    PackageManager.log.warning('Cannot include path outside RootDir: "%s"' % include_path)
                    continue
                if os.path.isfile(include_path):
                    include_paths.append(include_path)
                    continue
                else:
                    search_path = os.path.join(include_path, wildcard_pattern)
                    for f in glob.iglob(search_path, recursive=not no_recurse):
                        if os.path.isfile(f):
                            include_paths.append(f)
                    continue

            # populate files list using relative file path
            test_path = os.path.join(root_path, include_path)
            if not os.path.isdir(test_path):
                include_paths.append(test_path)
                continue

            # populate files list using relative folder path
            search_path = os.path.join(root_path, include_path, wildcard_pattern)
            include_paths.extend([f for f in glob.iglob(search_path, recursive=not no_recurse) if os.path.isfile(f)])

        return PathHelper.uniqify(include_paths)

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
        if self.ppj.packages_node is None:
            return

        # clear temporary data
        if os.path.isdir(self.options.temp_path):
            shutil.rmtree(self.options.temp_path, ignore_errors=True)

        # ensure package path exists
        if not os.path.isdir(self.options.package_path):
            os.makedirs(self.options.package_path, exist_ok=True)

        for i, package_node in enumerate(self.ppj.packages_node):
            if not package_node.tag.endswith('Package'):
                continue

            default_name: str = self.ppj.project_name if i == 0 else '%s (%s)' % (self.ppj.project_name, i)
            package_name: str = self.ppj.parse(package_node.get('Name', default=default_name))
            package_name = self._fix_package_extension(package_name)

            package_root: str = self.ppj.parse(package_node.get('RootDir', default=self.ppj.project_path))

            PackageManager.log.info('Creating "%s"...' % package_name)

            package_data: list = self._populate_include_paths(package_node, package_root)

            if not package_data:
                PackageManager.log.info('No includes found for package: "%s"' % package_name)
                continue

            PackageManager.print_list('Includes found:', package_data)

            for source_path in package_data:
                relpath = os.path.relpath(source_path, package_root)
                target_path = os.path.join(self.options.temp_path, relpath)

                # fix target path if user passes a deeper package root (RootDir)
                if source_path.casefold().endswith('.pex') and not relpath.casefold().startswith('scripts'):
                    target_path = os.path.join(self.options.temp_path, 'Scripts', relpath)

                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                shutil.copy2(source_path, target_path)

            package_path: str = os.path.join(self.options.package_path, package_name)
            self.package_paths.append(package_path)

            # run bsarch
            commands: str = self.build_commands(self.options.temp_path, package_path)
            ProcessManager.run(commands, use_bsarch=True)

            # clear temporary data
            if os.path.isdir(self.options.temp_path):
                shutil.rmtree(self.options.temp_path, ignore_errors=True)

    def create_zip(self) -> None:
        if self.ppj.zipfile_node is None:
            return

        zip_data: list = self._populate_include_paths(self.ppj.zipfile_node, self.ppj.zip_root_path)
        if not zip_data:
            PackageManager.log.error('No includes found for ZIP file: "%s"' % self.ppj.zip_file_name)
            return

        PackageManager.log.info('Creating "%s"...' % self.ppj.zip_file_name)

        PackageManager.print_list('Includes found:', zip_data)

        # ensure that zip output folder exists
        zip_output_path: str = os.path.join(self.options.zip_output_path, self.ppj.zip_file_name)
        os.makedirs(os.path.dirname(zip_output_path), exist_ok=True)

        try:
            with zipfile.ZipFile(zip_output_path, mode='w', compression=self.ppj.compress_type) as z:
                for include_path in zip_data:
                    if self.ppj.zip_root_path not in include_path:
                        PackageManager.log.warning('Cannot zip file outside RootDir: "%s"' % include_path)
                        continue
                    arcname: str = os.path.relpath(include_path, self.ppj.zip_root_path)
                    z.write(include_path, arcname, compress_type=self.ppj.compress_type)

            PackageManager.log.info('Wrote ZIP file to: "%s"' % zip_output_path)
        except PermissionError:
            PackageManager.log.error('Cannot open ZIP file for writing: "%s"' % zip_output_path)
            sys.exit(1)
