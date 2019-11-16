import glob
import os
import shutil
from collections import OrderedDict

from lxml import etree

from pyro.CommandArguments import CommandArguments
from pyro.ElementHelper import ElementHelper
from pyro.PexReader import PexReader
from pyro.ProcessManager import ProcessManager
from pyro.ProjectBase import ProjectBase
from pyro.ProjectOptions import ProjectOptions


class PapyrusProject(ProjectBase):
    def __init__(self, options: ProjectOptions) -> None:
        super().__init__(options)

        self.pex_reader = PexReader(self.options)

        self.root_node = etree.parse(self.options.input_path, etree.XMLParser(remove_blank_text=True)).getroot()
        self.options.output_path = self.root_node.get('Output')
        self.options.flags_path = self.root_node.get('Flags')
        self.use_bsarch = self.root_node.get('CreateArchive')
        self.use_anonymizer = self.root_node.get('Anonymize')

    @staticmethod
    def _unique_list(items: list) -> tuple:
        return tuple(OrderedDict.fromkeys(items))

    def build_commands(self) -> tuple:
        commands = []

        compiler_path: str = self.options.compiler_path
        flags_path: str = self.options.flags_path
        output_path: str = self.options.output_path

        unique_imports: tuple = self._get_imports_from_script_paths()
        real_psc_paths: tuple = self.get_script_paths(True)
        script_paths_compiled: tuple = self.get_script_paths_compiled()

        arguments: CommandArguments = CommandArguments()

        for real_psc_path in real_psc_paths:
            if not self.options.no_incremental_build:
                script_name, _ = os.path.splitext(os.path.basename(real_psc_path))

                # if pex exists, compare time_t in pex header with psc's last modified timestamp
                pex_path: str = [s for s in script_paths_compiled if s.endswith('%s.pex' % script_name)][0]
                if not os.path.exists(pex_path):
                    continue

                compiled_time: int = self.pex_reader.get_compilation_time(pex_path)
                if os.path.getmtime(real_psc_path) < compiled_time:
                    continue

            namespace, file_name = map(lambda x: os.path.basename(x), [os.path.dirname(real_psc_path), real_psc_path])
            ns_path = os.path.join(namespace, file_name)

            arguments.clear()
            arguments.append_quoted(compiler_path)
            arguments.append_quoted(ns_path)
            arguments.append_quoted(output_path, 'o')
            arguments.append_quoted(';'.join(unique_imports), 'i')
            arguments.append_quoted(flags_path, 'f')

            if self.options.game_type == 'fo4':
                release = self.root_node.get('Release')
                if release and release.casefold() == 'true':
                    arguments.append('-release')

                final = self.root_node.get('Final')
                if final and final.casefold() == 'true':
                    arguments.append('-final')

            optimize = self.root_node.get('Optimize')
            if optimize and optimize.casefold() == 'true':
                arguments.append('-op')

            commands.append(arguments.join())

        return tuple(commands)

    def _build_commands_bsarch(self, script_folder: str, archive_path: str) -> str:
        bsarch_path = self.options.bsarch_path

        arguments = CommandArguments()

        arguments.append_quoted(bsarch_path)
        arguments.append('pack')
        arguments.append_quoted(script_folder)
        arguments.append_quoted(archive_path)

        if self.options.game_type == 'fo4':
            arguments.append('-fo4')
        elif self.options.game_type == 'sse':
            arguments.append('-sse')
        else:
            arguments.append('-tes5')

        return arguments.join()

    def _get_imports_from_script_paths(self) -> tuple:
        """Generate list of unique import paths from script paths"""
        script_paths: tuple = self.get_script_paths()

        xml_import_paths: list = ElementHelper.get_child_values(self.root_node, 'Imports')

        psc_import_paths: list = []

        for script_path in script_paths:
            for xml_import_path in xml_import_paths:
                test_path = os.path.join(xml_import_path, os.path.dirname(script_path))

                if os.path.exists(test_path) and test_path not in psc_import_paths:
                    psc_import_paths.append(test_path)

        return self._unique_list(psc_import_paths + xml_import_paths)

    def _copy_scripts_to_temp_path(self, script_paths: tuple, tmp_scripts_path: str) -> None:
        output_path = self.options.output_path

        if any(dots in output_path.split(os.sep) for dots in ['.', '..']):
            output_path = os.path.normpath(os.path.join(os.path.dirname(self.options.input_path), output_path))

        pex_paths = [os.path.join(output_path, script_path.replace('.psc', '.pex')) for script_path in script_paths]

        if self.options.game_type != 'fo4':
            pex_paths = [os.path.join(output_path, os.path.basename(script_path)) for script_path in pex_paths]

        for pex_path in pex_paths:
            pex_path = os.path.abspath(pex_path)
            temp_file_path = os.path.join(tmp_scripts_path, os.path.basename(pex_path))

            shutil.copy2(pex_path, temp_file_path)

    def _get_script_paths_from_folders_node(self) -> tuple:
        """Retrieves script paths from the Folders node"""
        script_paths = []

        folders_node = ElementHelper.get(self.root_node, 'Folders')

        if not folders_node:
            return ()

        # defaults to False if the attribute does not exist
        no_recurse = bool(folders_node.get('NoRecurse'))

        for folder in ElementHelper.get_child_values(self.root_node, 'Folders'):
            # fix relative paths
            if folder == '.' or folder == '..':
                # TODO: may not have parity with how the Papyrus Compiler handles these paths
                folder = os.path.join(os.path.dirname(self.options.input_path), folder)
            elif not os.path.isabs(folder):
                folder = self._try_find_folder(folder)

            absolute_script_paths = glob.glob(os.path.join(os.path.abspath(folder), '*.psc'), recursive=not no_recurse)

            # we need path parts, not absolute paths - we're assuming namespaces though (critical flaw?)
            for script_path in absolute_script_paths:
                namespace, file_name = map(lambda x: os.path.basename(x), [os.path.dirname(script_path), script_path])
                script_paths.append(os.path.join(namespace, file_name))

        return self._unique_list(script_paths)

    def _try_find_folder(self, folder: str) -> str:
        """Try to find folder in import paths"""
        for import_path in ElementHelper.get_child_values(self.root_node, 'Imports'):
            test_path = os.path.join(import_path, folder)
            if os.path.exists(test_path):
                return test_path
        return folder

    def _get_script_paths_from_scripts_node(self) -> tuple:
        """Retrieves script paths from the Scripts node"""
        script_paths = []

        scripts_node = ElementHelper.get(self.root_node, 'Scripts')

        if scripts_node is None:
            return ()

        # "support" colons by replacing them with path separators so they're proper path parts
        # but watch out for absolute paths and use the path parts directly instead
        def fix_path(script_path: str) -> str:
            if os.path.isabs(script_path):
                namespace, file_name = map(lambda x: os.path.basename(x), [os.path.dirname(script_path), script_path])
                return os.path.join(namespace, file_name)
            return script_path.replace(':', os.sep)

        scripts = [fix_path(script_path) for script_path in ElementHelper.get_child_values(self.root_node, 'Scripts')]

        script_paths.extend(scripts)

        return self._unique_list(script_paths)

    def _get_include_paths_from_includes_node(self) -> tuple:
        # TODO: support includes for multiple archives

        include_paths: list = []

        includes = ElementHelper.get(self.root_node, 'Includes')
        if includes is None:
            return ()

        # test if Root attribute exists
        try:
            includes.get('Root')
        except AttributeError:
            return ()

        includes_root = includes.get('Root')

        if not os.path.exists(includes_root) or not os.path.isabs(includes_root):
            return ()

        if includes is not None:
            include_paths = ElementHelper.get_child_values(self.root_node, 'Includes')

        # ensure all include paths are relative
        # TODO: support absolute include paths, requires new XML attribute to specify destination path in archive
        relative_include_paths = [include_path for include_path in include_paths if not os.path.isabs(include_path)]
        if len(include_paths) != len(relative_include_paths):
            self.log.warn('Some include paths were removed. Reason: Only relative paths are supported.')

        include_paths = [os.path.join(includes_root, include_path) for include_path in include_paths]

        return self._unique_list(include_paths)

    def get_output_path(self) -> str:
        output_path = self.options.output_path

        if any(dots in output_path.split(os.sep) for dots in ['.', '..']):
            input_folder = os.path.dirname(self.options.input_path)
            output_path = os.path.join(input_folder, output_path)

        return output_path

    def get_script_paths(self, absolute_paths: bool = False) -> tuple:
        """Returns script paths from Folders and Scripts nodes"""
        paths: list = []

        folder_paths = self._get_script_paths_from_folders_node()
        if folder_paths and len(folder_paths) > 0:
            paths.extend(folder_paths)

        script_paths = self._get_script_paths_from_scripts_node()
        if script_paths and len(script_paths) > 0:
            paths.extend(script_paths)

        results = [os.path.normpath(path) for path in paths]

        if absolute_paths:
            # TODO: soooo many loops... :(
            xml_import_paths = ElementHelper.get_child_values(self.root_node, 'Imports')
            results = [os.path.join(xml_import_path, script_path) for script_path in results for xml_import_path in xml_import_paths]
            results = [absolute_script_path for absolute_script_path in results if os.path.exists(absolute_script_path)]

        return self._unique_list(results)

    def get_script_paths_compiled(self) -> tuple:
        output_path = self.options.output_path

        # only fo4 supports namespaced script names
        psc_paths = [script_path if self.options.game_type == 'fo4' else os.path.basename(script_path)
                     for script_path in self.get_script_paths()]

        # return paths to compiled scripts
        pex_paths = [os.path.join(output_path, script_path).replace('.psc', '.pex') for script_path in psc_paths]

        return tuple(os.path.normpath(pex_path) for pex_path in pex_paths if os.path.exists(pex_path))

    def pack_archive(self) -> None:
        if self.options.no_bsarch:
            self.log.warn('BSA/BA2 packing disabled by user.')
            return

        if not self.use_bsarch:
            self.log.warn('BSA/BA2 packing not enabled in PPJ.')
            return

        # create temporary folder
        temp_path = self.options.temp_path
        temp_scripts_path = os.path.join(temp_path, 'Scripts')

        # clear temporary data
        if os.path.exists(temp_path):
            shutil.rmtree(temp_path, ignore_errors=True)

        os.makedirs(temp_path, exist_ok=True)
        os.makedirs(temp_scripts_path, exist_ok=True)

        script_paths = self.get_script_paths()

        self._copy_scripts_to_temp_path(script_paths, temp_scripts_path)

        # copy includes to archive
        include_paths = self._get_include_paths_from_includes_node()

        if include_paths:
            output_path = self.options.output_path
            root_path = os.path.dirname(output_path)

            for include_path in include_paths:
                relative_include_path = os.path.relpath(include_path, root_path)
                target_path = os.path.join(temp_path, relative_include_path)

                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                shutil.copy2(include_path, target_path)

        archive_path = self.root_node.get('Archive')

        if not archive_path:
            PapyrusProject.log.error('Cannot pack archive because Archive attribute not set')
            return

        commands = self._build_commands_bsarch(*map(lambda x: os.path.normpath(x), [temp_path, archive_path]))
        ProcessManager.run(commands, use_bsarch=True)

        # clear temporary data
        if os.path.exists(temp_path):
            shutil.rmtree(temp_path, ignore_errors=True)
