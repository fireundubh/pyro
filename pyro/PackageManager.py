import fnmatch
import glob
import os
import shutil

from pyro.CommandArguments import CommandArguments
from pyro.ElementHelper import ElementHelper
from pyro.Logger import Logger
from pyro.PapyrusProject import PapyrusProject
from pyro.PathHelper import PathHelper
from pyro.ProcessManager import ProcessManager


class PackageManager(Logger):
    def __init__(self, ppj: PapyrusProject) -> None:
        self.ppj = ppj
        self.ppj.options.package_path = self._get_output_path()

        if not os.path.exists(self.ppj.options.package_path):
            os.makedirs(self.ppj.options.package_path, exist_ok=True)

        self.extension: str = '.ba2' if self.ppj.options.game_type == 'fo4' else '.bsa'

    def _get_output_path(self) -> str:
        # use package output path if set in ppj, otherwise use default path
        packages_node = ElementHelper.get(self.ppj.root_node, 'Packages')

        if packages_node is None:
            return self.ppj.options.package_path

        output_path: str = packages_node.get('Output', default='')

        if not output_path:
            return self.ppj.options.package_path

        if output_path == os.curdir:
            output_path = self.ppj.project_path
        elif output_path == os.pardir or not os.path.isabs(output_path):
            output_path = os.path.join(self.ppj.project_path, output_path)

        return os.path.normpath(output_path)

    def _fix_package_extension(self, package_name: str) -> str:
        if not package_name.casefold().endswith(('.ba2', '.bsa')):
            return '%s%s' % (package_name, self.extension)
        return '%s%s' % (os.path.splitext(package_name)[0], self.extension)

    def build_commands(self, containing_folder: str, output_path: str) -> str:
        """Returns arguments for BSArch as a string"""
        arguments = CommandArguments()

        arguments.append_quoted(self.ppj.options.bsarch_path)
        arguments.append('pack')
        arguments.append_quoted(containing_folder)
        arguments.append_quoted(output_path)

        if self.ppj.options.game_type == 'fo4':
            arguments.append('-fo4')
        elif self.ppj.options.game_type == 'sse':
            arguments.append('-sse')
        else:
            arguments.append('-tes5')

        return arguments.join()

    def create_archive(self) -> None:
        package_nodes = ElementHelper.get(self.ppj.root_node, 'Packages')
        if package_nodes is None:
            PackageManager.log.warning('Cannot create package because no packages are defined')
            return

        # clear temporary data
        if os.path.exists(self.ppj.options.temp_path):
            shutil.rmtree(self.ppj.options.temp_path, ignore_errors=True)

        for i, package_node in enumerate(package_nodes):
            package_name: str = package_node.get('Name', default=self.ppj.project_name if i == 0 else '%s (%s)' % (self.ppj.project_name, i))
            package_name = self._fix_package_extension(package_name)

            package_root: str = package_node.get('RootDir', default='')
            if not package_root:
                PackageManager.log.error('Cannot create package "%s" because RootDir attribute has no value' % package_name)
                continue

            PackageManager.log.info('Creating "%s"...' % package_name)

            package_data: list = []

            for include_node in package_node:
                no_recurse: bool = self.ppj._get_attr_as_bool(include_node, 'NoRecurse')
                wildcard_pattern: str = '*' if no_recurse else '**\*'

                if include_node.text == os.curdir or include_node.text == os.pardir:
                    PackageManager.log.warning('Include paths cannot be equal to "." or ".."')
                    continue

                if include_node.text.startswith('.'):
                    PackageManager.log.warning('Include paths cannot start with "."')
                    continue

                # populate files list using simple glob patterns
                if '*' in include_node.text:
                    search_path: str = os.path.join(package_root, wildcard_pattern)
                    files: list = [f for f in glob.iglob(search_path, recursive=not no_recurse) if os.path.isfile(f)]
                    matches: list = fnmatch.filter(files, include_node.text)
                    if not matches:
                        PackageManager.log.warning('No files in "%s" matched glob pattern: %s' % (search_path, include_node.text))
                    package_data.extend(matches)
                    continue

                include_path: str = os.path.normpath(include_node.text)

                # populate files list using absolute paths
                if os.path.isabs(include_path) and os.path.exists(include_path):
                    package_data.append(include_path)
                    continue

                # populate files list using relative file path
                test_path = os.path.join(package_root, include_path)
                if not os.path.isdir(test_path):
                    package_data.append(test_path)
                    continue

                # populate files list using relative folder path
                package_data.extend([f for f in glob.iglob(os.path.join(package_root, include_path, wildcard_pattern), recursive=not no_recurse) if os.path.isfile(f)])

            if package_data:
                PackageManager.log.info('Includes found:')

                for source_path in PathHelper.uniqify(package_data):
                    PackageManager.log.info('+ "%s"' % source_path)
                    target_path: str = os.path.join(self.ppj.options.temp_path, os.path.relpath(source_path, package_root))

                    os.makedirs(os.path.dirname(target_path), exist_ok=True)
                    shutil.copy2(source_path, target_path)

                # run bsarch
                commands: str = self.build_commands(self.ppj.options.temp_path, os.path.join(self.ppj.options.package_path, package_name))
                ProcessManager.run(commands, use_bsarch=True)
            else:
                PackageManager.log.info('No includes found for package: "%s"' % package_name)

            # clear temporary data
            if os.path.exists(self.ppj.options.temp_path):
                shutil.rmtree(self.ppj.options.temp_path, ignore_errors=True)
