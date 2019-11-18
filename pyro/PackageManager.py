import os
import shutil

from pyro.CommandArguments import CommandArguments
from pyro.ElementHelper import ElementHelper
from pyro.Logger import Logger
from pyro.PapyrusProject import PapyrusProject
from pyro.ProcessManager import ProcessManager


class PackageManager:
    log = Logger()

    def __init__(self, ppj: PapyrusProject) -> None:
        self.ppj = ppj
        self.includes_root = ''

    def _copy_scripts_to_temp_path(self, psc_paths: list, temp_path: str) -> None:
        output_path = self.ppj.options.output_path

        if any(dots in output_path.split(os.sep) for dots in ['.', '..']):
            output_path = os.path.normpath(os.path.join(self.ppj.project_path, output_path))

        pex_paths = [os.path.join(output_path, script_path.replace('.psc', '.pex')) for script_path in psc_paths]

        if self.ppj.options.game_type != 'fo4':
            # removes parent namespace folder from paths because TESV and SSE do not support namespaces
            pex_paths = [os.path.join(output_path, os.path.basename(script_path)) for script_path in pex_paths]

        for pex_path in pex_paths:
            if self.ppj.options.game_type == 'fo4':
                namespace, file_name = map(lambda x: os.path.basename(x), [os.path.dirname(pex_path), pex_path])
                target_path = os.path.join(self.ppj.options.output_path, namespace, file_name)
                temp_file_path = os.path.join(temp_path, namespace, file_name)
            else:
                target_path = os.path.abspath(pex_path)
                temp_file_path = os.path.join(temp_path, os.path.basename(pex_path))

            if not os.path.exists(target_path):
                self.log.error('Cannot locate file to copy: %s' % target_path)
                continue

            os.makedirs(os.path.dirname(temp_file_path), exist_ok=True)
            shutil.copy2(target_path, temp_file_path)

    def _get_include_paths(self) -> list:
        # TODO: support includes for multiple archives
        includes = ElementHelper.get(self.ppj.root_node, 'Includes')
        if includes is None or len(list(includes)) == 0:
            return []

        self.includes_root = includes.get('Root', default=self.ppj.project_path)

        # treat curdir the same as the project path
        if self.includes_root == os.curdir:
            self.includes_root = self.ppj.project_path

        if self.includes_root == os.pardir:
            self.log.warn('Cannot use parent folder of project path as includes root')
            return []

        # check if includes root path is relative to project folder
        if not os.path.isabs(self.includes_root):
            test_path = os.path.join(self.ppj.project_path, self.includes_root)
            if os.path.exists(test_path):
                self.includes_root = test_path

        include_paths = ElementHelper.get_child_values(self.ppj.root_node, 'Includes')

        results: list = []

        # remove absolute include paths because we don't know how to handle them
        for include_path in include_paths:
            if os.path.isabs(include_path):
                self.log.warn('Cannot include absolute path: "%s"' % include_path)
                continue
            full_path = os.path.join(self.includes_root, include_path)
            if os.path.exists(full_path):
                results.append(full_path)

        return self.ppj._unique_list(results)

    def build_commands(self, script_folder: str, archive_path: str) -> str:
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
        # create temporary folder
        temp_scripts_path = os.path.join(self.ppj.options.temp_path, 'Scripts')

        # clear temporary data
        if os.path.exists(self.ppj.options.temp_path):
            shutil.rmtree(self.ppj.options.temp_path, ignore_errors=True)

        os.makedirs(temp_scripts_path, exist_ok=True)

        self._copy_scripts_to_temp_path(self.ppj.psc_paths, temp_scripts_path)

        # copy includes to archive
        include_paths = self._get_include_paths()
        if include_paths:
            self.log.pyro('Includes found:')
            for include_path in include_paths:
                self.log.pyro('- "%s"' % include_path)

            for include_path in include_paths:
                include_relpath = os.path.relpath(include_path, self.includes_root)
                target_path = os.path.join(self.ppj.options.temp_path, include_relpath)

                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                shutil.copy2(include_path, target_path)

            self.log.pyro('Copied includes to temporary folder.')

        archive_path = self.ppj.options.archive_path

        # handle file paths
        if not archive_path.casefold().endswith(('.ba2', '.bsa')):
            archive_name, _ = os.path.splitext(os.path.basename(self.ppj.options.input_path))
            archive_path = os.path.join(archive_path, '%s%s' % (archive_name, '.ba2' if self.ppj.options.game_type == 'fo4' else '.bsa'))

        # create archive directory
        os.makedirs(os.path.dirname(archive_path), exist_ok=True)

        # run bsarch
        commands = self.build_commands(*map(lambda x: os.path.normpath(x), [self.ppj.options.temp_path, archive_path]))
        ProcessManager.run(commands, use_bsarch=True)

        # clear temporary data
        if os.path.exists(self.ppj.options.temp_path):
            shutil.rmtree(self.ppj.options.temp_path, ignore_errors=True)
