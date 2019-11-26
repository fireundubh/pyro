import glob
import io
import os
import re
import sys
import zipfile

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

        xml_parser: etree.XMLParser = etree.XMLParser(remove_blank_text=True, remove_comments=True)

        # strip comments from raw text because lxml.etree.XMLParser does not remove XML-unsupported comments
        # e.g., '<PapyrusProject <!-- xmlns="PapyrusProject.xsd" -->>'
        xml_document: io.StringIO = PapyrusProject._strip_xml_comments(self.options.input_path)

        project_xml: etree.ElementTree = etree.parse(xml_document, xml_parser)
        self.root_node: etree.ElementBase = project_xml.getroot()

        # TODO: validate earlier
        schema: etree.XMLSchema = ElementHelper.validate_schema(self.root_node, self.program_path)
        if schema:
            try:
                if schema.assertValid(project_xml) is None:
                    PapyrusProject.log.info('Successfully validated XML Schema.')
            except etree.DocumentInvalid as e:
                PapyrusProject.log.error('Failed to validate XML Schema.%s\t%s' % (os.linesep, e))
                sys.exit(1)

        variables_node = ElementHelper.get(self.root_node, 'Variables')
        if variables_node is not None:
            for variable_node in variables_node:
                if not variable_node.tag.endswith('Variable'):
                    continue

                var_key = variable_node.get('Name', default='')
                var_value = variable_node.get('Value', default='')

                if any([not var_key, not var_value]):
                    continue

                self.variables.update({var_key: var_value})

        # we need to parse all PapyrusProject attributes after validating and before we do anything else
        # options can be overridden by arguments when the BuildFacade is initialized
        self.options.output_path = self.parse(self.root_node.get('Output', default=''))
        self.options.flags_path = self.parse(self.root_node.get('Flags', default=''))

        self.optimize: bool = PapyrusProject._get_attr_as_bool(self.root_node, 'Optimize')
        self.release: bool = PapyrusProject._get_attr_as_bool(self.root_node, 'Release')
        self.final: bool = PapyrusProject._get_attr_as_bool(self.root_node, 'Final')

        self.options.anonymize = PapyrusProject._get_attr_as_bool(self.root_node, 'Anonymize')
        self.options.bsarch = PapyrusProject._get_attr_as_bool(self.root_node, 'Package')
        self.options.zip = PapyrusProject._get_attr_as_bool(self.root_node, 'Zip')

        self.packages_node = ElementHelper.get(self.root_node, 'Packages')

        if self.options.bsarch:
            if self.packages_node is None:
                PapyrusProject.log.error('Package is enabled but the Packages node is undefined. Setting Package to false.')
                self.options.bsarch = False
            else:
                self.options.package_path = self.parse(self.packages_node.get('Output', default=self.options.package_path))

        self.zipfile_node = ElementHelper.get(self.root_node, 'ZipFile')

        if self.options.zip:
            if self.zipfile_node is None:
                PapyrusProject.log.error('Zip is enabled but the ZipFile node is undefined. Setting Zip to false.')
                self.options.zip = False
            else:
                self._setup_zipfile_options()

        # we need to populate the list of import paths before we try to determine the game type
        # because the game type can be determined from import paths
        self.import_paths: list = self._get_import_paths()
        if not self.import_paths:
            PapyrusProject.log.error('Failed to build list of import paths')
            sys.exit(1)

        # ensure that folder paths are implicitly imported
        implicit_folder_paths: list = self._get_implicit_folder_imports()
        PathHelper.merge_implicit_import_paths(implicit_folder_paths, self.import_paths)

        for path in implicit_folder_paths:
            if path in self.import_paths:
                PapyrusProject.log.warning('Using import path implicitly: "%s"' % path)

        self.psc_paths: list = self._get_psc_paths()
        if not self.psc_paths:
            PapyrusProject.log.error('Failed to build list of script paths')
            sys.exit(1)

        # this adds implicit imports from script paths
        implicit_script_paths: list = self._get_implicit_script_imports()
        PathHelper.merge_implicit_import_paths(implicit_script_paths, self.import_paths)

        for path in implicit_script_paths:
            if path in self.import_paths:
                PapyrusProject.log.warning('Using import path implicitly: "%s"' % path)

        # we need to set the game type after imports are populated but before pex paths are populated
        # allow xml to set game type but defer to passed argument
        if not self.options.game_type:
            game_type: str = self.parse(self.root_node.get('Game', default='')).casefold()

            if game_type and game_type in self.game_types:
                PapyrusProject.log.warning('Using game type: %s (determined from Papyrus Project)' % self.game_types[game_type])
                self.options.game_type = game_type

        if not self.options.game_type:
            self.options.game_type = self.get_game_type()

        if not self.options.game_type:
            PapyrusProject.log.error('Cannot determine game type from arguments or Papyrus Project')
            sys.exit(1)

        # get expected pex paths - these paths may not exist and that is okay!
        self.pex_paths: list = self._get_pex_paths()

        # these are relative paths to psc scripts whose pex counterparts are missing
        self.missing_scripts: list = self._find_missing_script_paths()

        # game type must be set before we call this
        if not self.options.game_path:
            self.options.game_path = self.get_game_path()

    def _setup_zipfile_options(self) -> None:
        self.zip_root_path = self.parse(self.zipfile_node.get('RootDir', default=self.project_path))

        # zip - required attribute
        if not os.path.isabs(self.zip_root_path):
            test_path: str = os.path.normpath(os.path.join(self.project_path, self.zip_root_path))

            if os.path.isdir(test_path):
                self.zip_root_path = test_path
            else:
                PapyrusProject.log.error('Cannot resolve RootDir path to existing folder: "%s"' % self.zip_root_path)
                sys.exit(1)

        # zip - optional attributes
        self.zip_file_name: str = self.parse(self.zipfile_node.get('Name', default=self.project_name))
        if not self.zip_file_name.casefold().endswith('.zip'):
            self.zip_file_name = '%s.zip' % self.zip_file_name

        self.options.zip_output_path = self.parse(self.zipfile_node.get('Output', default=self.options.zip_output_path))

        if not self.options.zip_compression:
            self.options.zip_compression = self.parse(self.zipfile_node.get('Compression', default='deflate').casefold())

        if self.options.zip_compression not in ('store', 'deflate'):
            self.options.zip_compression = 'deflate'

        self.compress_type: int = zipfile.ZIP_STORED if self.options.zip_compression == 'store' else zipfile.ZIP_DEFLATED

    @staticmethod
    def _get_attr_as_bool(node: etree.ElementBase, attribute_name: str, default_value: str = 'false') -> bool:
        attr: str = node.get(attribute_name, default=default_value).casefold()
        return any([attr == 'true', attr == '1'])

    @staticmethod
    def _strip_xml_comments(path: str) -> io.StringIO:
        with open(path, mode='r', encoding='utf-8') as f:
            xml_document: str = f.read()
            comments_pattern = re.compile('(<!--.*?-->)', flags=re.DOTALL)
            xml_document = comments_pattern.sub('', xml_document)
        return io.StringIO(xml_document)

    def _find_missing_script_paths(self) -> list:
        """Returns list of script paths for compiled scripts that do not exist"""
        results: list = []

        for psc_path in self.psc_paths:
            if self.options.game_type == 'fo4':
                object_name = PathHelper.calculate_relative_object_name(psc_path, self.import_paths)
            else:
                object_name = os.path.basename(psc_path)

            pex_path: str = os.path.join(self.options.output_path, object_name.replace('.psc', '.pex'))
            if os.path.exists(pex_path):
                continue

            results.append(psc_path)

        return PathHelper.uniqify(results)

    def _get_import_paths(self) -> list:
        """Returns absolute import paths from Papyrus Project"""
        results: list = []

        import_nodes: etree.ElementBase = ElementHelper.get(self.root_node, 'Imports')
        if import_nodes is None:
            return []

        for import_node in import_nodes:
            if not import_node.tag.endswith('Import'):
                continue

            if not import_node.text:
                continue

            import_path: str = os.path.normpath(self.parse(import_node.text))

            if import_path == os.pardir:
                self.log.warning('Import paths cannot be equal to ".."')
                continue

            if import_path == os.curdir:
                import_path = self.project_path
            elif not os.path.isabs(import_path):
                # relative import paths should be relative to the project
                import_path = os.path.normpath(os.path.join(self.project_path, import_path))

            if os.path.exists(import_path):
                results.append(import_path)

        return PathHelper.uniqify(results)

    def _get_implicit_folder_imports(self) -> list:
        """Returns absolute implicit import paths from Folder node paths"""
        implicit_paths: list = []

        folder_nodes = ElementHelper.get(self.root_node, 'Folders')
        if folder_nodes is None:
            return []

        for folder_node in folder_nodes:
            if not folder_node.tag.endswith('Folder'):
                continue

            if not folder_node.text:
                continue

            folder_path: str = os.path.normpath(self.parse(folder_node.text))

            if os.path.isabs(folder_path):
                if os.path.exists(folder_path):
                    implicit_paths.append(folder_path)
            else:
                test_path = os.path.join(self.project_path, folder_path)
                if os.path.exists(test_path):
                    implicit_paths.append(test_path)

        return PathHelper.uniqify(implicit_paths)

    def _get_implicit_script_imports(self) -> list:
        """Returns absolute implicit import paths from Script node paths"""
        implicit_paths: list = []

        for psc_path in self.psc_paths:
            for import_path in self.import_paths:
                relpath = os.path.relpath(os.path.dirname(psc_path), import_path)
                test_path = os.path.normpath(os.path.join(import_path, relpath))
                if os.path.exists(test_path):
                    implicit_paths.append(test_path)

        return PathHelper.uniqify(implicit_paths)

    def _get_pex_paths(self) -> list:
        """
        Returns absolute paths to compiled scripts that may not exist yet in output folder
        """
        pex_paths: list = []

        for psc_path in self.psc_paths:
            if self.options.game_type == 'fo4':
                object_name = PathHelper.calculate_relative_object_name(psc_path, self.import_paths)
            else:
                object_name = os.path.basename(psc_path)

            pex_path = os.path.join(self.options.output_path, object_name.replace('.psc', '.pex'))

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
            PapyrusProject.log.info('%s script paths discovered from %s nodes.' % (len(node_paths), tag[:-1]))
            if node_paths:
                paths.extend(node_paths)

        results: list = []

        # convert user paths to absolute paths
        for path in paths:
            # try to add existing absolute paths
            if os.path.isabs(path) and os.path.exists(path):
                results.append(path)
                continue

            # try to add existing project-relative paths
            test_path = os.path.join(self.project_path, path)
            if os.path.exists(test_path):
                results.append(test_path)
                continue

            # try to add existing import-relative paths
            for import_path in self.import_paths:
                if not os.path.isabs(import_path):
                    import_path = os.path.join(self.project_path, import_path)

                test_path = os.path.join(import_path, path)
                if os.path.exists(test_path):
                    results.append(test_path)
                    break

        results = PathHelper.uniqify(results)

        PapyrusProject.log.info('%s unique script paths resolved to absolute paths.' % len(results))

        return results

    def _get_script_paths_from_folders_node(self) -> list:
        """Returns script paths from the Folders element array"""
        folder_nodes = ElementHelper.get(self.root_node, 'Folders')
        if folder_nodes is None:
            return []

        script_paths: list = []
        folder_paths: list = []

        for folder_node in folder_nodes:
            if not folder_node.tag.endswith('Folder'):
                continue

            folder_text: str = self.parse(folder_node.text)

            if folder_text == os.pardir:
                self.log.warning('Folder paths cannot be equal to ".."')
                continue

            no_recurse: bool = self._get_attr_as_bool(folder_node, 'NoRecurse')

            # try to add project path
            if folder_text == os.curdir:
                folder_paths.append((self.project_path, no_recurse))
                continue

            folder_path: str = os.path.normpath(folder_text)

            # try to add absolute path
            if os.path.isabs(folder_path) and os.path.isdir(folder_path):
                folder_paths.append((folder_path, no_recurse))
                continue

            # try to add project-relative folder path
            test_path = os.path.join(self.project_path, folder_path)
            if os.path.isdir(test_path):
                folder_paths.append((test_path, no_recurse))
                continue

            # try to add import-relative folder path
            for import_path in self.import_paths:
                test_path = os.path.join(import_path, folder_path)
                if os.path.isdir(test_path):
                    folder_paths.append((test_path, no_recurse))
                    continue

            PapyrusProject.log.warning('Cannot resolve folder path: "%s"' % folder_node.text)

        for folder_path, no_recurse in folder_paths:
            search_path: str = os.path.join(folder_path, '*' if no_recurse else '**\*')
            script_paths.extend([f for f in glob.iglob(search_path, recursive=not no_recurse) if os.path.isfile(f) and f.endswith('.psc')])

        return PathHelper.uniqify(script_paths)

    def _get_script_paths_from_scripts_node(self) -> list:
        """Returns script paths from the Scripts node"""
        paths: list = []

        script_nodes = ElementHelper.get(self.root_node, 'Scripts')
        if script_nodes is None:
            return []

        for script_node in script_nodes:
            if not script_node.tag.endswith('Script'):
                continue

            psc_path: str = self.parse(script_node.text)

            if ':' in psc_path:
                psc_path = psc_path.replace(':', os.sep)

            paths.append(os.path.normpath(psc_path))

        return PathHelper.uniqify(paths)

    def _try_exclude_unmodified_scripts(self) -> list:
        psc_paths: list = []

        for psc_path in self.psc_paths:
            script_name, _ = os.path.splitext(os.path.basename(psc_path))

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
                PapyrusProject.log.warning('Cannot determine compilation time from compiled script due to unknown file magic: "%s"' % matching_path)
                continue

            compiled_time: int = header.compilation_time.value
            if os.path.getmtime(psc_path) < compiled_time:
                continue

            psc_paths.append(psc_path)

        return PathHelper.uniqify(psc_paths)

    def build_commands(self) -> list:
        commands: list = []

        arguments: CommandArguments = CommandArguments()

        compiler_path: str = self.options.compiler_path
        flags_path: str = self.options.flags_path
        output_path: str = self.options.output_path
        import_paths: str = ';'.join(self.import_paths)

        if self.options.no_incremental_build:
            psc_paths = PathHelper.uniqify(self.psc_paths)
        else:
            psc_paths = self._try_exclude_unmodified_scripts()

        # add .psc scripts whose .pex counterparts do not exist
        for missing_psc_path in self.missing_scripts:
            psc_paths.append(missing_psc_path)

        # generate list of commands
        for psc_path in psc_paths:
            if self.options.game_type == 'fo4':
                psc_path = PathHelper.calculate_relative_object_name(psc_path, self.import_paths)

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
