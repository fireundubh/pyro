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
        self.bsarch_path = self.ppj.options.bsarch_path
        self.output_path = self.ppj.options.output_path
        self.temp_path = self.ppj.options.temp_path
        self.game_type = self.ppj.options.game_type
        self.includes_root = ''

    def _copy_scripts_to_temp_path(self, script_paths: tuple, temp_scripts_path: str) -> None:
        output_path = self.output_path

        if any(dots in output_path.split(os.sep) for dots in ['.', '..']):
            output_path = os.path.normpath(os.path.join(os.path.dirname(self.ppj.options.input_path), output_path))

        pex_paths = [os.path.join(output_path, script_path.replace('.psc', '.pex')) for script_path in script_paths]

        if self.game_type != 'fo4':
            # removes parent namespace folder from paths because TESV and SSE do not support namespaces
            pex_paths = [os.path.join(output_path, os.path.basename(script_path)) for script_path in pex_paths]

        for pex_path in pex_paths:
            pex_path = os.path.abspath(pex_path)
            temp_file_path = os.path.join(temp_scripts_path, os.path.basename(pex_path))

            shutil.copy2(pex_path, temp_file_path)

    def _get_include_paths(self) -> tuple:
        # TODO: support includes for multiple archives
        includes = ElementHelper.get(self.ppj.root_node, 'Includes')
        if includes is None or len(list(includes)) == 0:
            return ()

        self.includes_root = includes.get('Root', default=os.path.dirname(self.ppj.options.input_path))

        # treat curdir the same as the project path
        if self.includes_root == os.curdir:
            self.includes_root = os.path.dirname(self.ppj.options.input_path)

        if self.includes_root == os.pardir:
            self.log.warn('Cannot use parent folder of project path as includes root')
            return ()

        # check if includes root path is relative to project folder
        if not os.path.abspath(self.includes_root):
            test_path = os.path.join(os.path.dirname(self.ppj.options.input_path), self.includes_root)
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

        arguments.append_quoted(self.bsarch_path)
        arguments.append('pack')
        arguments.append_quoted(script_folder)
        arguments.append_quoted(archive_path)

        if self.game_type == 'fo4':
            arguments.append('-fo4')
        elif self.game_type == 'sse':
            arguments.append('-sse')
        else:
            arguments.append('-tes5')

        return arguments.join()

    def create_archive(self) -> None:
        # create temporary folder
        temp_scripts_path = os.path.join(self.temp_path, 'Scripts')

        # clear temporary data
        if os.path.exists(self.temp_path):
            shutil.rmtree(self.temp_path, ignore_errors=True)

        os.makedirs(temp_scripts_path, exist_ok=True)

        script_paths = self.ppj.get_script_paths()
        self._copy_scripts_to_temp_path(script_paths, temp_scripts_path)

        # copy includes to archive
        include_paths = self._get_include_paths()

        self.log.pyro('Includes found:')
        for include_path in include_paths:
            self.log.pyro('- "%s"' % include_path)

        if include_paths:
            for include_path in include_paths:
                include_relpath = os.path.relpath(include_path, self.includes_root)
                target_path = os.path.join(self.temp_path, include_relpath)

                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                shutil.copy2(include_path, target_path)

        self.log.pyro('Copied includes to temporary folder.')

        archive_path = self.ppj.root_node.get('Archive', default='')
        if not archive_path:
            PapyrusProject.log.error('Cannot pack archive because Archive attribute not set')
            return

        commands = self.build_commands(*map(lambda x: os.path.normpath(x), [self.temp_path, archive_path]))
        ProcessManager.run(commands, use_bsarch=True)

        # clear temporary data
        if os.path.exists(self.temp_path):
            shutil.rmtree(self.temp_path, ignore_errors=True)
