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
        self.includes_root = ''

    def _copy_includes_to_temp_path(self) -> None:
        # copy includes to archive
        include_paths: list = self._get_include_paths()
        if not include_paths:
            return

        PackageManager.log.info('Includes found:')

        for include_path in include_paths:
            PackageManager.log.info('- "%s"' % include_path)

            include_relpath: str = os.path.relpath(include_path, self.includes_root)
            target_path: str = os.path.join(self.ppj.options.temp_path, include_relpath)
            target_folder: str = os.path.dirname(target_path)

            os.makedirs(target_folder, exist_ok=True)
            shutil.copy2(include_path, target_path)

        PackageManager.log.info('Copied includes to temporary folder.')

    def _copy_scripts_to_temp_path(self, psc_paths: list, temp_path: str) -> None:
        """Copies compiled scripts to temporary folder"""
        pex_paths = [os.path.join(self.ppj.options.output_path, psc_path.replace('.psc', '.pex')) for psc_path in psc_paths]

        if self.ppj.options.game_type != 'fo4':
            # removes parent and ancestor folders from paths
            pex_paths = [os.path.join(self.ppj.options.output_path, os.path.basename(pex_path)) for pex_path in pex_paths]

        for pex_path in pex_paths:
            if self.ppj.options.game_type == 'fo4':
                rel_object_name = PathHelper.calculate_relative_object_name(pex_path, self.ppj.import_paths)
                target_path = os.path.join(self.ppj.options.output_path, rel_object_name)
                temp_file_path = os.path.join(temp_path, rel_object_name)
            else:
                target_path = os.path.abspath(pex_path)
                temp_file_path = os.path.join(temp_path, os.path.basename(pex_path))

            if not os.path.exists(target_path):
                self.log.error('Cannot locate file to copy: %s' % target_path)
                continue

            os.makedirs(os.path.dirname(temp_file_path), exist_ok=True)
            shutil.copy2(target_path, temp_file_path)

    def _get_include_paths(self) -> list:
        """Returns list of absolute include paths"""
        include_nodes = ElementHelper.get(self.ppj.root_node, 'Includes')
        if include_nodes is None or len(list(include_nodes)) == 0:
            return []

        self.includes_root = include_nodes.get('Root', default=self.ppj.project_path)

        # treat curdir the same as the project path
        if self.includes_root == os.curdir:
            self.includes_root = self.ppj.project_path

        if self.includes_root == os.pardir:
            PackageManager.log.warning('Cannot use parent folder of project path as includes root')
            return []

        # check if includes root path is relative to project folder
        if not os.path.isabs(self.includes_root):
            test_path = os.path.join(self.ppj.project_path, self.includes_root)
            if os.path.exists(test_path):
                self.includes_root = test_path

        results: list = []

        for include_node in include_nodes:
            include_path = os.path.normpath(include_node.text)

            if os.path.isabs(include_path):
                PackageManager.log.warning('Cannot include absolute path: "%s"' % include_path)
                continue

            if include_path == os.pardir:
                PackageManager.log.warning('Cannot use ".." as include path')
                continue

            full_path: str = self.includes_root if include_path == os.curdir else os.path.join(self.includes_root, include_path)

            if not os.path.exists(full_path):
                PackageManager.log.warning('Cannot use include because path does not exist: "%s"' % full_path)
                continue

            if os.path.isfile(full_path):
                results.append(full_path)
            else:
                no_recurse: bool = any([include_node.get('NoRecurse', default='false').casefold() == value for value in ('true', '1')])

                search_path: str = os.path.join(full_path, '*') if no_recurse else os.path.join(full_path, '**\*')
                files = [f for f in glob.glob(search_path, recursive=not no_recurse) if os.path.isfile(f)]

                for f in files:
                    results.append(f)

        return PathHelper.uniqify(results)

    def build_commands(self, script_folder: str, archive_path: str) -> str:
        """Returns arguments for BSArch as a string"""
        arguments = CommandArguments()

        arguments.append_quoted(self.ppj.options.bsarch_path)
        arguments.append('pack')
        arguments.append_quoted(script_folder)
        arguments.append_quoted(archive_path)

        if self.ppj.options.game_type == 'fo4':
            arguments.append('-fo4')
        elif self.ppj.options.game_type == 'sse':
            arguments.append('-sse')
        else:
            arguments.append('-tes5')

        return arguments.join()

    def create_archive(self) -> None:
        # clear temporary data
        if os.path.exists(self.ppj.options.temp_path):
            shutil.rmtree(self.ppj.options.temp_path, ignore_errors=True)

        # create temporary folder for compiled scripts
        temp_scripts_path: str = os.path.join(self.ppj.options.temp_path, 'Scripts')
        os.makedirs(temp_scripts_path, exist_ok=True)

        self._copy_scripts_to_temp_path(self.ppj.psc_paths, temp_scripts_path)

        self._copy_includes_to_temp_path()

        archive_path: str = self.ppj.options.archive_path

        # if the archive path is a folder, use the project name as the package name
        if not archive_path.casefold().endswith(('.ba2', '.bsa')):
            archive_name, _ = os.path.splitext(os.path.basename(self.ppj.options.input_path))
            archive_path = os.path.join(archive_path, '%s%s' % (archive_name, '.ba2' if self.ppj.options.game_type == 'fo4' else '.bsa'))

        # create archive directory
        archive_folder: str = os.path.dirname(archive_path)
        os.makedirs(archive_folder, exist_ok=True)

        # run bsarch
        commands: str = self.build_commands(*map(lambda x: os.path.normpath(x), [self.ppj.options.temp_path, archive_path]))
        ProcessManager.run(commands, use_bsarch=True)

        # clear temporary data
        if os.path.exists(self.ppj.options.temp_path):
            shutil.rmtree(self.ppj.options.temp_path, ignore_errors=True)
