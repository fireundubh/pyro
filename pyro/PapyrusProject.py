import glob
import os
import sys
from collections import OrderedDict

from lxml import etree

from pyro.CommandArguments import CommandArguments
from pyro.ElementHelper import ElementHelper
from pyro.PathHelper import PathHelper
from pyro.PexReader import PexReader
from pyro.ProjectBase import ProjectBase
from pyro.ProjectOptions import ProjectOptions


class PapyrusProject(ProjectBase):
    def __init__(self, options: ProjectOptions) -> None:
        super().__init__(options)

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

        bsarch = self.root_node.get('CreateArchive', default='true').casefold()
        self.options.no_bsarch = not bsarch == 'true' or not bsarch == '1'

        anonymize = self.root_node.get('Anonymize', default='true').casefold()
        self.options.no_anonymize = not anonymize == 'true' or not anonymize == '1'

        self.release: bool = False
        self.final: bool = False

        if self.options.game_type == 'fo4':
            release = self.root_node.get('Release', default='false').casefold()
            self.release = release == 'true' or release == '1'

            final = self.root_node.get('Final', default='false').casefold()
            self.final = final == 'true' or final == '1'

        optimize = self.root_node.get('Optimize', default='false').casefold()
        self.optimize: bool = optimize == 'true' or optimize == '1'

        self.folder_paths: list = []

        self.import_paths: list = self._get_import_paths()
        if not self.import_paths:
            self.log.error('Failed to build list of import paths using arguments or Papyrus Project')
            sys.exit(1)

        self.psc_paths: list = self._get_psc_paths()
        if not self.psc_paths:
            self.log.error('Failed to build list of script paths using arguments or Papyrus Project')
            sys.exit(1)

        # this adds implicit imports from script paths
        self.import_paths = self._get_implicit_script_imports()

        # get expected pex paths - these paths may not exist and that is okay!
        self.pex_paths: list = self._get_pex_paths()

        # these are file names
        self.missing_script_names: list = self._find_missing_script_names()

    def _find_missing_script_names(self) -> list:
        """Returns list of script names for compiled scripts that do not exist"""
        script_names: list = []

        for pex_path in self.pex_paths:
            # skip existing pex file paths
            if os.path.exists(pex_path):
                continue

            pex_basename = os.path.basename(pex_path)
            file_name, _ = os.path.splitext(pex_basename)

            if file_name not in script_names:
                script_names.append(file_name)

        return script_names

    @staticmethod
    def _merge_implicit_import_paths(implicit_paths: list, import_paths: list) -> None:
        """Inserts orphan and descendant implicit paths into list of import paths at correct positions"""
        if not implicit_paths:
            return

        def _get_ancestor_import_index(_import_paths: list, _implicit_path: str) -> int:
            for _i, _import_path in enumerate(_import_paths):
                if _import_path in _implicit_path:
                    return _i
            return -1

        implicit_paths.sort()

        for implicit_path in reversed(PathHelper.uniqify(implicit_paths)):
            # do not add import paths that are already declared
            if implicit_path in import_paths:
                continue

            PapyrusProject.log.warn('Using import path implicitly: "%s"' % implicit_path)

            # insert implicit path before ancestor import path, if ancestor exists
            i = _get_ancestor_import_index(import_paths, implicit_path)
            if i > -1:
                import_paths.insert(i, implicit_path)
                continue

            # insert orphan implicit path at the first position
            import_paths.insert(0, implicit_path)

    def _get_import_paths(self) -> list:
        """Returns absolute import paths from Papyrus Project"""
        import_paths: list = [os.path.normpath(path) for path in ElementHelper.get_child_values(self.root_node, 'Imports')]

        # ensure that folder paths are implicitly imported
        folder_paths: list = self._get_implicit_folder_imports()
        self._merge_implicit_import_paths(folder_paths, import_paths)

        results: list = []

        for import_path in import_paths:
            if import_path == os.curdir:
                import_path = self.project_path
            elif import_path == os.pardir:
                self.log.warn('Cannot use ".." as import path')
                continue
            elif not os.path.isabs(import_path):
                # relative import paths should be relative to the project
                import_path = os.path.join(self.project_path, import_path)

            PathHelper.try_append_existing(import_path, results)

        return PathHelper.uniqify(results)

    def _get_implicit_folder_imports(self) -> list:
        implicit_paths: list = []

        folders = ElementHelper.get(self.root_node, 'Folders')
        if folders is None:
            return []

        folder_paths = ElementHelper.get_child_values(self.root_node, 'Folders')

        for folder_path in folder_paths:
            if PathHelper.try_append_abspath(folder_path, implicit_paths):
                continue

            test_path = os.path.join(self.project_path, folder_path)
            PathHelper.try_append_existing(test_path, implicit_paths)

        return PathHelper.uniqify(implicit_paths)

    def _get_implicit_script_imports(self) -> list:
        """Returns absolute implicit import paths from Folders and Scripts paths"""
        results: list = self.import_paths

        implicit_paths: list = []

        for psc_path in self.psc_paths:
            namespace, file_name = PathHelper.nsify(psc_path)

            for import_path in self.import_paths:
                test_path = os.path.join(import_path, namespace)
                PathHelper.try_append_existing(test_path, implicit_paths)

        self._merge_implicit_import_paths(implicit_paths, results)

        return PathHelper.uniqify(results)

    def _get_pex_paths(self) -> list:
        """Returns compiled script paths from output folder"""
        psc_paths: list = []
        pex_paths: list = []

        # build paths to source scripts
        for psc_path in self.psc_paths:
            # fo4 supports namespaced script names
            if self.options.game_type == 'fo4':
                psc_paths.append(psc_path)
                continue

            psc_paths.append(os.path.basename(psc_path))

        # build paths to compiled scripts
        for psc_path in psc_paths:
            pex_path = os.path.join(self.options.output_path, psc_path.replace('.psc', '.pex'))
            pex_paths.append(pex_path)

        return PathHelper.uniqify(pex_paths)

    def _get_psc_paths(self) -> list:
        """Returns script paths from Folders and Scripts nodes"""
        paths: list = []

        # try to populate paths with scripts from Folders and Scripts nodes
        for tag in ('Folders', 'Scripts'):
            node = ElementHelper.get(self.root_node, tag)
            if node is None:
                continue
            node_paths = getattr(self, '_get_script_paths_from_%s_node' % tag.casefold())()
            if node_paths:
                paths.extend(node_paths)

        results: list = []

        # convert user paths to absolute paths
        for path in paths:
            # try to add existing absolute paths
            if PathHelper.try_append_abspath(path, results):
                continue

            # try to add existing project-relative paths
            test_path = os.path.join(self.project_path, path)
            if PathHelper.try_append_existing(test_path, results):
                continue

            # try to add existing import-relative paths
            for import_path in self.import_paths:
                if not os.path.isabs(import_path):
                    import_path = os.path.join(self.project_path, import_path)

                test_path = os.path.join(import_path, path)
                if PathHelper.try_append_existing(test_path, results):
                    break

        return PathHelper.uniqify(results)

    def _get_script_paths_from_folders_node(self) -> list:
        """Returns script paths from the Folders element array"""
        paths: list = []

        folders_node = ElementHelper.get(self.root_node, 'Folders')
        if folders_node is None:
            return []

        # defaults to False if the attribute does not exist
        no_recurse = folders_node.get('NoRecurse', default='false').casefold() == 'true'

        for folder in ElementHelper.get_child_values(self.root_node, 'Folders'):
            folder = os.path.normpath(folder)

            if folder == os.curdir:
                folder = self.project_path
            elif folder == os.pardir:
                self.log.warn('Cannot use ".." as folder path')
                continue
            elif not os.path.isabs(folder):
                folder = self._try_find_folder(folder)

            self.folder_paths.append(folder)

        for folder in self.folder_paths:
            search_pattern = os.path.join(folder, '*.psc')
            psc_paths = glob.glob(search_pattern, recursive=not no_recurse)

            # we need path parts, not absolute paths
            for psc_path in psc_paths:
                namespace, file_name = PathHelper.nsify(psc_path)
                path = os.path.join(namespace, file_name) if self.options.game_type == 'fo4' else file_name
                paths.append(path)

        return PathHelper.uniqify(paths)

    def _get_script_paths_from_scripts_node(self) -> list:
        """Returns script paths from the Scripts node"""
        psc_paths: list = []

        scripts_node = ElementHelper.get(self.root_node, 'Scripts')
        if scripts_node is None:
            return []

        for psc_path in ElementHelper.get_child_values(self.root_node, 'Scripts'):
            if os.path.isabs(psc_path):
                namespace, file_name = PathHelper.nsify(psc_path)
                path = os.path.join(namespace, file_name)
            else:
                path = psc_path.replace(':', os.sep)

            psc_paths.append(path)

        return PathHelper.uniqify(psc_paths)

    def _try_exclude_unmodified_scripts(self) -> list:
        if self.options.no_incremental_build:
            return PathHelper.uniqify(self.psc_paths)

        psc_paths: list = []

        for psc_path in self.psc_paths:
            script_name, script_extension = os.path.splitext(os.path.basename(psc_path))

            # if pex exists, compare time_t in pex header with psc's last modified timestamp
            matching_path: str = ''
            for pex_path in self.pex_paths:
                if pex_path.endswith('%s.pex' % script_name):
                    matching_path = pex_path
                    break

            if not os.path.exists(matching_path):
                continue

            try:
                header = PexReader.get_header(matching_path)
            except ValueError:
                PapyrusProject.log.warn('Cannot determine compilation time from compiled script due to unknown file magic: "%s"' % matching_path)
                continue

            compiled_time: int = header.compilation_time.value
            if os.path.getmtime(psc_path) < compiled_time:
                continue

            psc_paths.append(psc_path)

        return PathHelper.uniqify(psc_paths)

    def _try_find_folder(self, folder: str) -> str:
        """Try to find folder relative to project, or in import paths"""
        test_path = os.path.join(self.project_path, folder)
        if os.path.exists(test_path):
            return test_path

        # when this runs, import_paths isn't populated with implicit paths from scripts yet.
        # just something to keep in mind if there's trouble down the road.
        for import_path in self.import_paths:
            test_path = os.path.join(import_path, folder)
            if os.path.exists(test_path):
                return test_path

        PapyrusProject.log.error('Cannot find folder relative to project or any import paths: "%s"' % folder)
        sys.exit(1)

    def build_commands(self) -> list:
        commands: list = []

        arguments: CommandArguments = CommandArguments()

        compiler_path: str = self.options.compiler_path
        flags_path: str = self.options.flags_path
        output_path: str = self.options.output_path
        import_paths: str = ';'.join(self.import_paths)

        psc_paths: list = self._try_exclude_unmodified_scripts()

        # add .psc scripts whose .pex counterparts do not exist
        for script_name in self.missing_script_names:
            for psc_path in self.psc_paths:
                if psc_path.endswith('%s.psc' % script_name):
                    psc_paths.append(psc_path)
                    break

        # generate list of commands
        for psc_path in psc_paths:
            if os.path.isabs(psc_path):
                namespace, file_name = PathHelper.nsify(psc_path)
                psc_path = os.path.join(namespace, file_name)

            arguments.clear()
            arguments.append_quoted(compiler_path)
            arguments.append_quoted(psc_path)
            arguments.append_quoted(output_path, 'o')
            arguments.append_quoted(import_paths, 'i')
            arguments.append_quoted(flags_path, 'f')

            if self.options.game_type == 'fo4':
                # noinspection PyUnboundLocalVariable
                if self.release:
                    arguments.append('-release')

                # noinspection PyUnboundLocalVariable
                if self.final:
                    arguments.append('-final')

            if self.optimize:
                arguments.append('-op')

            commands.append(arguments.join())

        return commands
