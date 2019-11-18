import glob
import os
import sys
from collections import OrderedDict

from lxml import etree

from pyro.CommandArguments import CommandArguments
from pyro.ElementHelper import ElementHelper
from pyro.PexReader import PexReader
from pyro.ProjectBase import ProjectBase
from pyro.ProjectOptions import ProjectOptions


class PapyrusProject(ProjectBase):
    def __init__(self, options: ProjectOptions) -> None:
        super().__init__(options)

        self.project_path = os.path.dirname(self.options.input_path)

        self.root_node = etree.parse(self.options.input_path, etree.XMLParser(remove_blank_text=True)).getroot()

        # allow xml to set game type but defer to passed argument
        if not self.options.game_type:
            game_type = self.root_node.get('Game', default='').casefold()
            if game_type:
                self.options.game_type = game_type

        # game type must be set before we call this
        self.options.game_path = self.get_game_path()

        self.options.archive_path = self.root_node.get('Archive', default='')
        self.options.output_path = self.root_node.get('Output', default='')
        self.options.flags_path = self.root_node.get('Flags', default='')
        self.options.no_bsarch = not self.root_node.get('CreateArchive', default='true').casefold() == 'true'
        self.options.no_anonymize = not self.root_node.get('Anonymize', default='true').casefold() == 'true'
        self.folders: list = []

        self.import_paths: list = self._get_imports()
        if not self.import_paths:
            sys.exit(self.log.error('Failed to build list of import paths using arguments or Papyrus Project'))

        self.psc_paths: list = self._get_psc_paths()
        if not self.psc_paths:
            sys.exit(self.log.error('Failed to build list of script paths using arguments or Papyrus Project'))

        # this adds implicit imports from script paths
        self.import_paths = self._get_implicit_script_imports()

        # get expected pex paths - these paths may not exist and that is okay!
        self.pex_paths: list = self._get_pex_paths()

        self.pex_reader = PexReader(self.options)

    @staticmethod
    def _unique_list(items: list) -> list:
        return list(OrderedDict.fromkeys(items))

    def _add_implicit_imports(self, implicit_paths: list, import_paths: list) -> None:
        def _get_ancestor_import_index(_import_paths: list, _implicit_path: str) -> int:
            for _i, _import_path in enumerate(_import_paths):
                if _import_path in _implicit_path:
                    return _i
            return -1

        implicit_paths.sort()

        for implicit_path in reversed(self._unique_list(implicit_paths)):
            # do not add import paths that are already declared
            if implicit_path in import_paths:
                continue

            self.log.warn('Using import path implicitly: "%s"' % implicit_path)

            # insert implicit path before ancestor import path, if ancestor exists
            i = _get_ancestor_import_index(import_paths, implicit_path)
            if i > -1:
                import_paths.insert(i, implicit_path)
                continue

            # insert orphan implicit path at the first position
            import_paths.insert(0, implicit_path)

    def _get_imports(self) -> list:
        """Returns absolute import paths from Papyrus Project"""
        import_paths: list = ElementHelper.get_child_values(self.root_node, 'Imports')

        # ensure that folder paths are implicitly imported
        folder_paths: list = self._get_implicit_folder_imports()
        self._add_implicit_imports(folder_paths, import_paths)

        results: list = []

        for import_path in import_paths:
            import_path = os.path.normpath(import_path)

            if import_path == os.curdir or import_path == os.pardir:
                import_path = os.path.abspath(import_path)
            elif not os.path.isabs(import_path):
                # relative import paths should be relative to the project
                import_path = os.path.join(os.path.join(self.project_path, import_path))

            if os.path.exists(import_path):
                results.append(import_path)

        return self._unique_list(results)

    def _get_implicit_folder_imports(self) -> list:
        implicit_paths: list = []

        folders = ElementHelper.get(self.root_node, 'Folders')
        if folders is None:
            return []

        folder_paths = ElementHelper.get_child_values(self.root_node, 'Folders')

        for folder_path in folder_paths:
            if not os.path.isabs(folder_path):
                test_path = os.path.join(self.project_path, folder_path)
                if os.path.exists(test_path) and test_path not in implicit_paths:
                    implicit_paths.append(test_path)
            else:
                if os.path.exists(folder_path) and folder_path not in implicit_paths:
                    implicit_paths.append(folder_path)

        return self._unique_list(implicit_paths)

    def _get_implicit_script_imports(self) -> list:
        """Returns absolute implicit import paths from Folders and Scripts paths"""
        results: list = self.import_paths

        implicit_paths: list = []

        for psc_path in self.psc_paths:
            namespace, file_name = map(lambda x: os.path.basename(x), [os.path.dirname(psc_path), psc_path])

            for import_path in self.import_paths:
                test_path = os.path.join(import_path, namespace)
                if os.path.exists(test_path) and test_path not in implicit_paths and test_path not in results:
                    implicit_paths.append(test_path)

        self._add_implicit_imports(implicit_paths, results)

        return self._unique_list(results)

    def _get_pex_paths(self) -> list:
        """Returns compiled script paths from output folder"""
        psc_paths = []
        pex_paths = []

        # build paths to source scripts
        for psc_path in self.psc_paths:
            psc_path = os.path.normpath(psc_path)

            # only fo4 supports namespaced script names
            if self.options.game_type == 'fo4':
                psc_paths.append(psc_path)
                continue

            psc_paths.append(os.path.basename(psc_path))

        # build paths to compiled scripts
        for psc_path in psc_paths:
            psc_path = os.path.normpath(psc_path)

            pex_path = os.path.join(self.options.output_path, psc_path).replace('.psc', '.pex')
            pex_paths.append(pex_path)

        return pex_paths

    def _get_psc_paths(self) -> list:
        """Returns script paths from Folders and Scripts nodes"""
        paths: list = []

        folders = ElementHelper.get(self.root_node, 'Folders')
        if folders is not None:
            folder_paths = self._get_script_paths_from_folders_node()
            if folder_paths:
                paths.extend(folder_paths)

        scripts = ElementHelper.get(self.root_node, 'Scripts')
        if scripts is not None:
            script_paths = self._get_script_paths_from_scripts_node()
            if script_paths:
                paths.extend(script_paths)

        results: list = []

        for path in paths:
            path = os.path.normpath(path)

            if os.path.isabs(path):
                results.append(path)
                continue

            test_path = os.path.join(self.project_path, path)
            if os.path.exists(test_path):
                results.append(test_path)
                continue

            for import_path in self.import_paths:
                if not os.path.isabs(import_path):
                    import_path = os.path.join(self.project_path, import_path)

                test_path = os.path.join(import_path, path)
                if os.path.exists(test_path):
                    results.append(test_path)
                    break

        return self._unique_list(results)

    def _get_script_paths_from_folders_node(self) -> list:
        """Returns script paths from the Folders element array"""
        paths = []

        folders_node = ElementHelper.get(self.root_node, 'Folders')

        if folders_node is None:
            return []

        # defaults to False if the attribute does not exist
        no_recurse = folders_node.get('NoRecurse', default='false').casefold() == 'true'

        for folder in ElementHelper.get_child_values(self.root_node, 'Folders'):
            folder = os.path.normpath(folder)

            if folder == os.curdir or folder == os.pardir:
                folder = os.path.abspath(folder)
            elif not os.path.isabs(folder):
                folder = self._try_find_folder(folder)

            self.folders.append(folder)

        for folder in self.folders:
            search_pattern = os.path.join(folder, '*.psc')
            script_paths = glob.glob(search_pattern, recursive=not no_recurse)

            # we need path parts, not absolute paths
            for script_path in script_paths:
                namespace, file_name = map(lambda x: os.path.basename(x), [os.path.dirname(script_path), script_path])

                path = file_name
                if self.options.game_type == 'fo4':
                    path = os.path.join(namespace, file_name)

                paths.append(path)

        return self._unique_list(paths)

    def _get_script_paths_from_scripts_node(self) -> list:
        """Retrieves script paths from the Scripts node"""
        script_paths = []

        scripts_node = ElementHelper.get(self.root_node, 'Scripts')
        if scripts_node is None:
            return []

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

    def _try_exclude_unmodified_scripts(self) -> list:
        scripts_to_compile: list = []

        if self.options.no_incremental_build:
            scripts_to_compile = self.psc_paths
        else:
            for psc_path in self.psc_paths:
                script_name, script_extension = os.path.splitext(os.path.basename(psc_path))

                # if pex exists, compare time_t in pex header with psc's last modified timestamp
                matching_path: str = ''
                for pex_path in self.pex_paths:
                    if pex_path.endswith('%s.%s' % (script_name, script_extension)):
                        matching_path = pex_path
                        break

                if not os.path.exists(matching_path):
                    continue

                compiled_time: int = self.pex_reader.get_compilation_time(matching_path)
                if os.path.getmtime(psc_path) < compiled_time:
                    continue

                scripts_to_compile.append(psc_path)

        return scripts_to_compile

    def _try_find_folder(self, folder: str) -> str:
        """Try to find folder relative to project, or in import paths"""
        test_path = os.path.join(os.path.join(self.project_path, folder))
        if os.path.exists(test_path):
            return test_path

        for import_path in ElementHelper.get_child_values(self.root_node, 'Imports'):
            import_path = os.path.normpath(import_path)

            test_path = os.path.abspath(os.path.join(import_path, folder))
            if os.path.exists(test_path):
                return test_path

        sys.exit(self.log.error('Cannot find folder relative to project or relative to any import paths: "%s"' % folder))

    def build_commands(self) -> list:
        commands = []

        compiler_path: str = self.options.compiler_path
        flags_path: str = self.options.flags_path
        output_path: str = self.options.output_path

        arguments: CommandArguments = CommandArguments()

        psc_paths = self._try_exclude_unmodified_scripts()

        for psc_path in psc_paths:
            if os.path.isabs(psc_path):
                namespace, file_name = map(lambda x: os.path.basename(x), [os.path.dirname(psc_path), psc_path])
                psc_path = os.path.join(namespace, file_name)

            arguments.clear()
            arguments.append_quoted(compiler_path)
            arguments.append_quoted(psc_path)
            arguments.append_quoted(output_path, 'o')
            arguments.append_quoted(';'.join(self.import_paths), 'i')
            arguments.append_quoted(flags_path, 'f')

            if self.options.game_type == 'fo4':
                release = self.root_node.get('Release', default='false').casefold() == 'true'
                if release:
                    arguments.append('-release')

                final = self.root_node.get('Final', default='false').casefold() == 'true'
                if final:
                    arguments.append('-final')

            optimize = self.root_node.get('Optimize', default='false').casefold() == 'true'
            if optimize:
                arguments.append('-op')

            commands.append(arguments.join())

        return commands
