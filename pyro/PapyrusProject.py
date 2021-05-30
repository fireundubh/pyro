import configparser
import glob
import hashlib
import io
import os
import sys
import typing
from copy import deepcopy

from lxml import etree

from pyro.CommandArguments import CommandArguments
from pyro.Comparators import (endswith,
                              is_folder_node,
                              is_import_node,
                              is_script_node,
                              is_variable_node,
                              startswith)
from pyro.Constants import (GameName,
                            GameType,
                            XmlAttributeName,
                            XmlTagName)
from pyro.PathHelper import PathHelper
from pyro.PexReader import PexReader
from pyro.ProjectBase import ProjectBase
from pyro.ProjectOptions import ProjectOptions
from pyro.Remotes import (GenericRemote,
                          RemoteBase)
from pyro.XmlHelper import XmlHelper
from pyro.XmlRoot import XmlRoot


class PapyrusProject(ProjectBase):
    ppj_root: XmlRoot = None
    folders_node: etree.ElementBase = None
    imports_node: etree.ElementBase = None
    packages_node: etree.ElementBase = None
    scripts_node: etree.ElementBase = None
    zip_files_node: etree.ElementBase = None
    pre_build_node: etree.ElementBase = None
    post_build_node: etree.ElementBase = None

    has_folders_node: bool = False
    has_imports_node: bool = False
    has_packages_node: bool = False
    has_scripts_node: bool = False
    has_zip_files_node: bool = False
    has_pre_build_node: bool = False
    has_post_build_node: bool = False

    remote: RemoteBase = None
    remote_schemas: tuple = ('https:', 'http:')

    zip_file_name: str = ''
    zip_root_path: str = ''

    missing_scripts: dict = {}
    pex_paths: list = []
    psc_paths: dict = {}

    def __init__(self, options: ProjectOptions) -> None:
        super(PapyrusProject, self).__init__(options)

        xml_parser: etree.XMLParser = etree.XMLParser(remove_blank_text=True, remove_comments=True)

        # strip comments from raw text because lxml.etree.XMLParser does not remove XML-unsupported comments
        # e.g., '<PapyrusProject <!-- xmlns="PapyrusProject.xsd" -->>'
        xml_document: io.StringIO = XmlHelper.strip_xml_comments(self.options.input_path)

        project_xml: etree.ElementTree = etree.parse(xml_document, xml_parser)

        self.ppj_root = XmlRoot(project_xml)

        schema: etree.XMLSchema = XmlHelper.validate_schema(self.ppj_root.ns, self.program_path)

        if schema:
            try:
                schema.assertValid(project_xml)
            except etree.DocumentInvalid as e:
                PapyrusProject.log.error(f'Failed to validate XML Schema.{os.linesep}\t{e}')
                sys.exit(1)
            else:
                PapyrusProject.log.info('Successfully validated XML Schema.')

        # variables need to be parsed before nodes are updated
        variables_node = self.ppj_root.find(XmlTagName.VARIABLES)
        if variables_node is not None:
            self._parse_variables(variables_node)

        # we need to parse all attributes after validating and before we do anything else
        # options can be overridden by arguments when the BuildFacade is initialized
        self._update_attributes(self.ppj_root.node)

        if self.options.resolve_ppj:
            xml_output = etree.tostring(self.ppj_root.node, encoding='utf-8', xml_declaration=True, pretty_print=True)
            PapyrusProject.log.debug(f'Resolved PPJ. Text output:{os.linesep * 2}{xml_output.decode()}')
            sys.exit(1)

        self.options.flags_path = self.ppj_root.get(XmlAttributeName.FLAGS)
        self.options.output_path = self.ppj_root.get(XmlAttributeName.OUTPUT)

        if self.options.output_path and not os.path.isabs(self.options.output_path):
            self.options.output_path = self.get_output_path()

        self.optimize = self.ppj_root.get(XmlAttributeName.OPTIMIZE) == 'True'
        self.release = self.ppj_root.get(XmlAttributeName.RELEASE) == 'True'
        self.final = self.ppj_root.get(XmlAttributeName.FINAL) == 'True'

        self.options.anonymize = self.ppj_root.get(XmlAttributeName.ANONYMIZE) == 'True'
        self.options.package = self.ppj_root.get(XmlAttributeName.PACKAGE) == 'True'
        self.options.zip = self.ppj_root.get(XmlAttributeName.ZIP) == 'True'

        self.imports_node = self.ppj_root.find(XmlTagName.IMPORTS)
        self.has_imports_node = self.imports_node is not None

        self.scripts_node = self.ppj_root.find(XmlTagName.SCRIPTS)
        self.has_scripts_node = self.scripts_node is not None

        self.folders_node = self.ppj_root.find(XmlTagName.FOLDERS)
        self.has_folders_node = self.folders_node is not None

        self.packages_node = self.ppj_root.find(XmlTagName.PACKAGES)
        self.has_packages_node = self.packages_node is not None

        self.zip_files_node = self.ppj_root.find(XmlTagName.ZIP_FILES)
        self.has_zip_files_node = self.zip_files_node is not None

        self.pre_build_node = self.ppj_root.find(XmlTagName.PRE_BUILD_EVENT)
        self.has_pre_build_node = self.pre_build_node is not None

        self.post_build_node = self.ppj_root.find(XmlTagName.POST_BUILD_EVENT)
        self.has_post_build_node = self.post_build_node is not None

        if self.options.package and self.has_packages_node:
            if not self.options.package_path:
                self.options.package_path = self.packages_node.get(XmlAttributeName.OUTPUT)

        if self.options.zip and self.has_zip_files_node:
            if not self.options.zip_output_path:
                self.options.zip_output_path = self.zip_files_node.get(XmlAttributeName.OUTPUT)

        # initialize remote if needed
        if self.remote_paths:
            if not self.options.remote_temp_path:
                self.options.remote_temp_path = self.get_remote_temp_path()

            if self.options.worker_limit == 0:
                self.options.worker_limit = self.get_worker_limit()

            if not self.options.access_token:
                cfg_parser = configparser.ConfigParser()
                cfg_path = os.path.join(self.program_path, '.secrets')

                try:
                    parsed_files = cfg_parser.read(cfg_path)
                except configparser.DuplicateSectionError:
                    PapyrusProject.log.error('Cannot proceed while ".secrets" contains duplicate sections')
                    sys.exit(1)
                except configparser.MissingSectionHeaderError:
                    PapyrusProject.log.error('Cannot proceed while ".secrets" contains no sections')
                    sys.exit(1)

                if cfg_path in parsed_files:
                    self.remote = GenericRemote(config=cfg_parser,
                                                worker_limit=self.options.worker_limit)
            else:
                self.remote = GenericRemote(access_token=self.options.access_token,
                                            worker_limit=self.options.worker_limit)

            # validate remote paths
            for path in self.remote_paths:
                if not self.remote.validate_url(path):
                    PapyrusProject.log.error(f'Cannot proceed while node contains invalid URL: "{path}"')
                    sys.exit(1)

        # we need to populate the list of import paths before we try to determine the game type
        # because the game type can be determined from import paths
        self.import_paths = self._get_import_paths()
        if not self.import_paths:
            PapyrusProject.log.error('Failed to build list of import paths')
            sys.exit(1)

        if not self.options.no_implicit_imports:
            # ensure that folder paths are implicitly imported
            implicit_folder_paths: list = self._get_implicit_folder_imports()

            if len(implicit_folder_paths) > 0:
                PapyrusProject.log.info('Implicitly imported folder paths found:')
                for path in implicit_folder_paths:
                    PapyrusProject.log.info(f'+ "{path}"')

                PathHelper.merge_implicit_import_paths(implicit_folder_paths, self.import_paths)

        # we need to populate psc paths after explicit and implicit import paths are populated
        # this also needs to be set before we populate implicit import paths from psc paths
        # not sure if this must run again after populating implicit import paths from psc paths
        self.psc_paths = self._get_psc_paths()
        if not self.psc_paths:
            PapyrusProject.log.error('Failed to build list of script paths')
            sys.exit(1)

        if not self.options.no_implicit_imports:
            # this adds implicit imports from script paths
            implicit_script_paths: list = self._get_implicit_script_imports()

            if len(implicit_script_paths) > 0:
                PapyrusProject.log.info('Implicitly imported script paths found:')
                for path in implicit_script_paths:
                    PapyrusProject.log.info(f'+ "{path}"')

                PathHelper.merge_implicit_import_paths(implicit_script_paths, self.import_paths)

        # we need to set the game type after imports are populated but before pex paths are populated
        # allow xml to set game type but defer to passed argument
        if self.options.game_type not in GameType.values():
            game_type: str = self.ppj_root.get(XmlAttributeName.GAME, default='')
            self.options.game_type = GameType.get(game_type)

            if self.options.game_type:
                PapyrusProject.log.warning(f'Using game type: {GameName.get(game_type)} (determined from Papyrus Project)')

        if not self.options.game_type:
            self.options.game_type = self.get_game_type()

        if not self.options.game_type:
            PapyrusProject.log.error('Cannot determine game type from arguments or Papyrus Project')
            sys.exit(1)

        # get expected pex paths - these paths may not exist and that is okay!
        self.pex_paths = self._get_pex_paths()

        # these are relative paths to psc scripts whose pex counterparts are missing
        self.missing_scripts: dict = self._find_missing_script_paths()

        # game type must be set before we call this
        if not self.options.game_path:
            self.options.game_path = self.get_game_path(self.options.game_type)

    @property
    def remote_paths(self) -> list:
        """
        Collects list of remote paths from Import and Folder nodes
        """
        results: list = []

        if self.has_imports_node:
            results.extend([node.text for node in filter(is_import_node, self.imports_node)
                            if startswith(node.text, self.remote_schemas, ignorecase=True)])

        if self.has_folders_node:
            results.extend([node.text for node in filter(is_folder_node, self.folders_node)
                            if startswith(node.text, self.remote_schemas, ignorecase=True)])

        return results

    def _parse_variables(self, variables_node: etree.ElementBase) -> None:
        reserved_characters: tuple = ('!', '#', '^', '&', '*')

        for node in filter(is_variable_node, variables_node):
            key, value = node.get(XmlAttributeName.NAME, default=''), node.get(XmlAttributeName.VALUE, default='')

            if any([not key, not value]):
                continue

            if not key.isalnum():
                PapyrusProject.log.error(f'The name of the variable "{key}" must be an alphanumeric string.')
                sys.exit(1)

            if any(c in reserved_characters for c in value):
                PapyrusProject.log.error(f'The value of the variable "{key}" contains a reserved character.')
                sys.exit(1)

            self.variables.update({key: value})

        # handle . and ..
        for key, value in self.variables.items():
            if value == os.pardir:
                value = os.path.normpath(os.path.join(self.project_path, os.pardir))
            elif value == os.curdir:
                value = self.project_path
            elif startswith(value, os.pardir) and os.path.sep in os.path.normpath(value):
                value = value.replace(os.pardir, os.path.normpath(os.path.join(self.project_path, os.pardir)), 1)
            elif startswith(value, os.curdir) and os.path.sep in os.path.normpath(value):
                value = value.replace(os.curdir, self.project_path, 1)

            self.variables.update({key: value})

        # allow variables to reference other variables
        for key, value in self.variables.items():
            self.variables.update({key: self.parse(value)})

        # complete round trip so that order does not matter
        for key in reversed(self.variables.keys()):
            value = self.variables[key]
            self.variables.update({key: self.parse(value)})

    def _update_attributes(self, parent_node: etree.ElementBase) -> None:
        """Updates attributes of element tree with missing attributes and default values"""
        ppj_bool_keys = [
            XmlAttributeName.OPTIMIZE,
            XmlAttributeName.RELEASE,
            XmlAttributeName.FINAL,
            XmlAttributeName.ANONYMIZE,
            XmlAttributeName.PACKAGE,
            XmlAttributeName.ZIP
        ]

        other_bool_keys = [
            XmlAttributeName.NO_RECURSE,
            XmlAttributeName.USE_IN_BUILD
        ]

        for node in parent_node.getiterator():
            if node.text:
                node.text = self.parse(node.text.strip())

            if not node.attrib:
                continue

            tag = node.tag.replace('{%s}' % self.ppj_root.ns, '')

            if tag == XmlTagName.PAPYRUS_PROJECT:
                if XmlAttributeName.GAME not in node.attrib:
                    node.set(XmlAttributeName.GAME, '')
                if XmlAttributeName.FLAGS not in node.attrib:
                    node.set(XmlAttributeName.FLAGS, self.options.flags_path)
                if XmlAttributeName.OUTPUT not in node.attrib:
                    node.set(XmlAttributeName.OUTPUT, self.options.output_path)
                for key in ppj_bool_keys:
                    if key not in node.attrib:
                        node.set(key, 'False')

            elif tag == XmlTagName.PACKAGES:
                if XmlAttributeName.OUTPUT not in node.attrib:
                    node.set(XmlAttributeName.OUTPUT, self.options.package_path)

            elif tag == XmlTagName.PACKAGE:
                if XmlAttributeName.NAME not in node.attrib:
                    node.set(XmlAttributeName.NAME, self.project_name)
                if XmlAttributeName.ROOT_DIR not in node.attrib:
                    node.set(XmlAttributeName.ROOT_DIR, self.project_path)

            elif tag in (XmlTagName.FOLDER, XmlTagName.INCLUDE):
                if XmlAttributeName.NO_RECURSE not in node.attrib:
                    node.set(XmlAttributeName.NO_RECURSE, 'False')
                if tag == XmlTagName.INCLUDE and XmlAttributeName.PATH not in node.attrib:
                    node.set(XmlAttributeName.PATH, '')

            elif tag == XmlTagName.ZIP_FILES:
                if XmlAttributeName.OUTPUT not in node.attrib:
                    node.set(XmlAttributeName.OUTPUT, self.options.zip_output_path)

            elif tag == XmlTagName.ZIP_FILE:
                if XmlAttributeName.NAME not in node.attrib:
                    node.set(XmlAttributeName.NAME, self.project_name)
                if XmlAttributeName.ROOT_DIR not in node.attrib:
                    node.set(XmlAttributeName.ROOT_DIR, self.project_path)
                if XmlAttributeName.COMPRESSION not in node.attrib:
                    node.set(XmlAttributeName.COMPRESSION, 'deflate')
                else:
                    node.set(XmlAttributeName.COMPRESSION, node.get(XmlAttributeName.COMPRESSION).casefold())

            elif tag == XmlTagName.PRE_BUILD_EVENT or tag == XmlTagName.POST_BUILD_EVENT:
                if XmlAttributeName.DESCRIPTION not in node.attrib:
                    node.set(XmlAttributeName.DESCRIPTION, '')
                if XmlAttributeName.USE_IN_BUILD not in node.attrib:
                    node.set(XmlAttributeName.USE_IN_BUILD, 'True')

            # parse values
            for key, value in node.attrib.items():
                value = value.casefold() in ('true', '1') if key in ppj_bool_keys + other_bool_keys else self.parse(value)
                node.set(key, str(value))

    def _calculate_object_name(self, psc_path: str) -> str:
        return PathHelper.calculate_relative_object_name(psc_path, self.import_paths)

    @staticmethod
    def _can_remove_folder(import_path: str, object_name: str, script_path: str) -> bool:
        import_path = import_path.casefold()
        object_name = object_name.casefold()
        script_path = script_path.casefold()
        return startswith(script_path, import_path) and os.path.join(import_path, object_name) != script_path

    def _find_missing_script_paths(self) -> dict:
        """Returns list of script paths for compiled scripts that do not exist"""
        results: dict = {}

        for object_name, script_path in self.psc_paths.items():
            pex_path: str = os.path.join(self.options.output_path, object_name.replace('.psc', '.pex'))

            if not os.path.isfile(pex_path) and script_path not in results:
                object_name = script_path if not os.path.isabs(script_path) else self._calculate_object_name(script_path)
                results[object_name] = script_path

        return results

    def _get_import_paths(self) -> list:
        """Returns absolute import paths from Papyrus Project"""
        results: list = []

        if not self.has_imports_node:
            return []

        for import_node in filter(is_import_node, self.imports_node):
            if startswith(import_node.text, self.remote_schemas, ignorecase=True):
                local_path = self._get_remote_path(import_node)
                PapyrusProject.log.info(f'Adding import path from remote: "{local_path}"...')
                results.append(local_path)
                continue

            import_path = os.path.normpath(import_node.text)

            if import_path == os.pardir:
                self.log.warning(f'Import paths cannot be equal to "{os.pardir}"')
                continue

            if import_path == os.curdir:
                import_path = self.project_path
            elif not os.path.isabs(import_path):
                # relative import paths should be relative to the project
                import_path = os.path.normpath(os.path.join(self.project_path, import_path))

            if os.path.isdir(import_path):
                results.append(import_path)
            else:
                self.log.error(f'Import path does not exist: "{import_path}"')
                sys.exit(1)

        return PathHelper.uniqify(results)

    def _get_implicit_folder_imports(self) -> list:
        """Returns absolute implicit import paths from Folder node paths"""
        implicit_paths: list = []

        if not self.has_folders_node:
            return []

        for folder_node in filter(is_folder_node, self.folders_node):
            folder_path: str = os.path.normpath(folder_node.text)

            if os.path.isabs(folder_path):
                if os.path.isdir(folder_path) and folder_path not in self.import_paths:
                    implicit_paths.append(folder_path)
            else:
                test_path = os.path.join(self.project_path, folder_path)
                if os.path.isdir(test_path) and test_path not in self.import_paths:
                    implicit_paths.append(test_path)

        return PathHelper.uniqify(implicit_paths)

    def _get_implicit_script_imports(self) -> list:
        """Returns absolute implicit import paths from Script node paths"""
        implicit_paths: list = []

        for object_name, script_path in self.psc_paths.items():
            script_folder_path = os.path.dirname(script_path)

            for import_path in self.import_paths:
                # TODO: figure out how to handle imports on different drives
                try:
                    relpath = os.path.relpath(script_folder_path, import_path)
                except ValueError as e:
                    PapyrusProject.log.warning(f'{e} (path: "{script_folder_path}", start: "{import_path}")')
                    continue

                test_path = os.path.normpath(os.path.join(import_path, relpath))
                if os.path.isdir(test_path) and test_path not in self.import_paths:
                    implicit_paths.append(test_path)

        return PathHelper.uniqify(implicit_paths)

    def _get_pex_paths(self) -> list:
        """
        Returns absolute paths to compiled scripts that may not exist yet in output folder
        """
        pex_paths: list = []

        for object_name, script_path in self.psc_paths.items():
            pex_path = os.path.join(self.options.output_path, object_name.replace('.psc', '.pex'))

            # do not check if file exists, we do that in _find_missing_script_paths for a different reason
            if pex_path not in pex_paths:
                pex_paths.append(pex_path)

        return pex_paths

    def _get_psc_paths(self) -> dict:
        """Returns script paths from Folders and Scripts nodes"""
        object_names: dict = {}

        # try to populate paths with scripts from Folders and Scripts nodes
        if self.has_folders_node:
            for script_path in self._get_script_paths_from_folders_node():
                object_name = script_path if not os.path.isabs(script_path) else self._calculate_object_name(script_path)
                object_names[object_name] = script_path

        if self.has_scripts_node:
            for script_path in self._get_script_paths_from_scripts_node():
                object_name = script_path if not os.path.isabs(script_path) else self._calculate_object_name(script_path)
                object_names[object_name] = script_path

        # convert user paths to absolute paths
        for object_name, script_path in object_names.items():
            # ignore existing absolute paths
            if os.path.isabs(script_path) and os.path.isfile(script_path):
                continue

            # try to add existing project-relative paths
            test_path = os.path.join(self.project_path, script_path)
            if os.path.isfile(test_path):
                object_names[object_name] = test_path
                continue

            # try to add existing import-relative paths
            for import_path in self.import_paths:
                if not os.path.isabs(import_path):
                    import_path = os.path.join(self.project_path, import_path)

                test_path = os.path.join(import_path, script_path)
                if os.path.isfile(test_path):
                    object_names[object_name] = test_path
                    break

        PapyrusProject.log.info(f'{len(object_names)} unique script paths resolved to absolute paths.')

        return object_names

    def _get_remote_path(self, node: etree.ElementBase) -> str:
        url_hash = hashlib.sha1(node.text.encode()).hexdigest()[:8]
        temp_path = os.path.join(self.options.remote_temp_path, url_hash)

        if self.options.force_overwrite or not os.path.exists(temp_path):
            try:
                for message in self.remote.fetch_contents(node.text, temp_path):
                    if message:
                        if not startswith(message, 'Failed to load'):
                            PapyrusProject.log.info(message)
                        else:
                            PapyrusProject.log.error(message)
                            sys.exit(1)
            except PermissionError as e:
                PapyrusProject.log.error(e)
                sys.exit(1)

        url_path = self.remote.create_local_path(node.text)

        local_path = os.path.join(temp_path, url_path)

        return local_path

    def _get_script_paths_from_folders_node(self) -> typing.Generator:
        """Returns script paths from the Folders element array"""
        for folder_node in filter(is_folder_node, self.folders_node):
            if folder_node.text == os.pardir:
                PapyrusProject.log.warning(f'Folder paths cannot be equal to "{os.pardir}"')
                continue

            no_recurse: bool = folder_node.get(XmlAttributeName.NO_RECURSE) == 'True'

            if not os.path.isabs(folder_node.text) and ':' in folder_node.text:
                folder_node.text = folder_node.text.replace(':', os.sep)

            # try to add project path
            if folder_node.text == os.curdir:
                yield from PathHelper.find_script_paths_from_folder(self.project_path, no_recurse)
                continue

            if startswith(folder_node.text, self.remote_schemas, ignorecase=True):
                local_path = self._get_remote_path(folder_node)
                PapyrusProject.log.info(f'Adding import path from remote: "{local_path}"...')
                self.import_paths.insert(0, local_path)
                PapyrusProject.log.info(f'Adding folder path from remote: "{local_path}"...')
                yield from PathHelper.find_script_paths_from_folder(local_path, no_recurse)
                continue

            folder_path: str = os.path.normpath(folder_node.text)

            # try to add absolute path
            if os.path.isabs(folder_path) and os.path.isdir(folder_path):
                yield from PathHelper.find_script_paths_from_folder(folder_path, no_recurse)
                continue

            # try to add project-relative folder path
            test_path = os.path.join(self.project_path, folder_path)
            if os.path.isdir(test_path):
                # count scripts to avoid issue where an errant `test_path` may exist and contain no sources
                # this can be a problem if that folder contains sources but user error is hard to fix
                search_path: str = os.path.join(test_path, '*' if no_recurse else r'**\*')
                script_count: int = sum(1 for f in glob.iglob(search_path, recursive=not no_recurse)
                                        if endswith(f, '.psc', ignorecase=True))
                if script_count > 0:
                    yield from PathHelper.find_script_paths_from_folder(test_path, no_recurse)
                    continue

            # try to add import-relative folder path
            for import_path in self.import_paths:
                test_path = os.path.join(import_path, folder_path)
                if os.path.isdir(test_path):
                    yield from PathHelper.find_script_paths_from_folder(test_path, no_recurse)

    def _get_script_paths_from_scripts_node(self) -> typing.Generator:
        """Returns script paths from the Scripts node"""
        for script_node in filter(is_script_node, self.scripts_node):
            if not os.path.isabs(script_node.text) and ':' in script_node.text:
                script_node.text = script_node.text.replace(':', os.sep)

            yield os.path.normpath(script_node.text)

    def _try_exclude_unmodified_scripts(self) -> dict:
        psc_paths: dict = {}

        for object_name, script_path in self.psc_paths.items():
            script_name, _ = os.path.splitext(os.path.basename(script_path))

            # if pex exists, compare time_t in pex header with psc's last modified timestamp
            matching_path: str = ''
            for pex_path in self.pex_paths:
                if pex_path.endswith(f'{script_name}.pex'):
                    matching_path = pex_path
                    break

            if not os.path.isfile(matching_path):
                continue

            try:
                header = PexReader.get_header(matching_path)
            except ValueError:
                PapyrusProject.log.warning(f'Cannot determine compilation time due to unknown magic: "{matching_path}"')
                continue

            compiled_time: int = header.compilation_time.value
            if os.path.getmtime(script_path) < compiled_time:
                continue

            if script_path not in psc_paths:
                psc_paths[object_name] = script_path

        return psc_paths

    def build_commands(self) -> list:
        """
        Builds list of commands for compiling scripts
        """
        commands: list = []

        arguments = CommandArguments()

        compiler_path: str = self.options.compiler_path
        flags_path: str = self.options.flags_path
        output_path: str = self.options.output_path

        if self.options.no_incremental_build:
            psc_paths: dict = self.psc_paths
        else:
            psc_paths = self._try_exclude_unmodified_scripts()

        # add .psc scripts whose .pex counterparts do not exist
        for object_name, script_path in self.missing_scripts.items():
            if object_name not in psc_paths.keys():
                psc_paths[object_name] = script_path

        source_import_paths = deepcopy(self.import_paths)

        # TODO: depth sorting solution is not foolproof! parse psc files for imports to determine command order
        for object_name, script_path in psc_paths.items():
            import_paths: list = self.import_paths

            if self.options.game_type != GameType.FO4:
                object_name = script_path

            # remove unnecessary import paths for script
            if self.options.game_type == GameType.FO4:
                for import_path in reversed(self.import_paths):
                    if self._can_remove_folder(import_path, object_name, script_path):
                        import_paths.remove(import_path)

            arguments.clear()
            arguments.append(compiler_path, enquote_value=True)
            arguments.append(object_name, enquote_value=True)
            arguments.append(flags_path, key='f', enquote_value=True)
            arguments.append(';'.join(import_paths), key='i', enquote_value=True)
            arguments.append(output_path, key='o', enquote_value=True)

            if self.options.game_type == GameType.FO4:
                # noinspection PyUnboundLocalVariable
                if self.release:
                    arguments.append('-release')

                # noinspection PyUnboundLocalVariable
                if self.final:
                    arguments.append('-final')

            if self.optimize:
                arguments.append('-op')

            arg_s = arguments.join()
            commands.append(arg_s)

        self.import_paths = source_import_paths

        return commands
