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
        self.options.package_path = self._get_output_path() if not self.options.package_path else self.ppj.project_path

        if not os.path.exists(self.options.package_path):
            os.makedirs(self.options.package_path, exist_ok=True)

        self.extension: str = '.ba2' if self.options.game_type == 'fo4' else '.bsa'

        self.package_paths: list = []

    def _get_output_path(self) -> str:
        # use package output path if set in ppj, otherwise use default path
        packages_node = ElementHelper.get(self.ppj.root_node, 'Packages')

        if packages_node is None:
            return self.options.package_path

        output_path: str = self.ppj.parse(packages_node.get('Output', default=self.options.package_path))

        if output_path == os.curdir:
            output_path = self.ppj.project_path
        elif output_path == os.pardir or not os.path.isabs(output_path):
            output_path = os.path.join(self.ppj.project_path, output_path)

        return os.path.normpath(output_path)

    def _fix_package_extension(self, package_name: str) -> str:
        if not package_name.casefold().endswith(('.ba2', '.bsa')):
            return '%s%s' % (package_name, self.extension)
        return '%s%s' % (os.path.splitext(package_name)[0], self.extension)

    def _populate_include_paths(self, parent_node: etree.ElementBase, root_path: str) -> list:
        include_paths: list = []

        for include_node in parent_node:
            if not include_node.tag.endswith('Include'):
                continue

            no_recurse: bool = self.ppj._get_attr_as_bool(include_node, 'NoRecurse')
            wildcard_pattern: str = '*' if no_recurse else '**\*'

            include_text: str = self.ppj.parse(include_node.text)

            if include_text == os.curdir or include_text == os.pardir:
                PackageManager.log.warning('Include paths cannot be equal to "." or ".."')
                continue

            if include_text.startswith('.'):
                PackageManager.log.warning('Include paths cannot start with "."')
                continue

            # populate files list using simple glob patterns
            if '*' in include_text:
                search_path: str = os.path.join(root_path, wildcard_pattern)
                files: list = [f for f in glob.iglob(search_path, recursive=not no_recurse) if os.path.isfile(f)]
                matches: list = fnmatch.filter(files, include_text)
                if not matches:
                    PackageManager.log.warning('No files in "%s" matched glob pattern: %s' % (search_path, include_text))
                include_paths.extend(matches)
                continue

            include_path: str = os.path.normpath(include_text)

            # populate files list using absolute paths
            if os.path.isabs(include_path) and os.path.exists(include_path):
                if root_path not in include_path:
                    PackageManager.log.warning('Cannot include path outside RootDir: "%s"' % include_path)
                    continue
                include_paths.append(include_path)
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
            PackageManager.log.warning('Package is enabled but the Packages node is undefined. No package will be created.')
            return

        # clear temporary data
        if os.path.exists(self.options.temp_path):
            shutil.rmtree(self.options.temp_path, ignore_errors=True)

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
                target_path: str = os.path.join(self.options.temp_path, os.path.relpath(source_path, package_root))

                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                shutil.copy2(source_path, target_path)

            package_path: str = os.path.join(self.options.package_path, package_name)
            self.package_paths.append(package_path)

            # run bsarch
            commands: str = self.build_commands(self.options.temp_path, package_path)
            ProcessManager.run(commands, use_bsarch=True)

            # clear temporary data
            if os.path.exists(self.options.temp_path):
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
                    arcname: str = os.path.relpath(include_path, self.ppj.zip_root_path)
                    z.write(include_path, arcname, compress_type=self.ppj.compress_type)

            PackageManager.log.info('Wrote ZIP file to: "%s"' % zip_output_path)
        except PermissionError:
            PackageManager.log.error('Cannot open ZIP file for writing: "%s"' % zip_output_path)
            sys.exit(1)
