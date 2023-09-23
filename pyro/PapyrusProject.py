import configparser
import hashlib
import io
import os
import sys
import time
import typing
from copy import deepcopy

from lxml import etree
from wcmatch import wcmatch

from pyro.Enums.Event import (Event,
                              BuildEvent,
                              ImportEvent,
                              CompileEvent,
                              AnonymizeEvent,
                              PackageEvent,
                              ZipEvent)
from pyro.CommandArguments import CommandArguments
from pyro.Comparators import (endswith,
                              is_folder_node,
                              is_import_node,
                              is_script_node,
                              is_variable_node,
                              is_namespace_path,
                              startswith)
from pyro.Constants import (GameName,
                            GameType,
                            XmlAttributeName,
                            XmlTagName)
from pyro.PathHelper import PathHelper
from pyro.PexReader import PexReader
from pyro.ProcessManager import ProcessManager
from pyro.ProjectBase import ProjectBase
from pyro.ProjectOptions import ProjectOptions
from pyro.Remotes.RemoteBase import RemoteBase
from pyro.Remotes.GenericRemote import GenericRemote
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
    pre_import_node: etree.ElementBase = None
    post_import_node: etree.ElementBase = None
    pre_compile_node: etree.ElementBase = None
    post_compile_node: etree.ElementBase = None
    pre_anonymize_node: etree.ElementBase = None
    post_anonymize_node: etree.ElementBase = None
    pre_package_node: etree.ElementBase = None
    post_package_node: etree.ElementBase = None
    pre_zip_node: etree.ElementBase = None
    post_zip_node: etree.ElementBase = None

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

        if self.options.create_project:
            sys.exit(1)

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

        if self.options.resolve_project:
            xml_output = etree.tostring(self.ppj_root.node, encoding='utf-8', xml_declaration=True, pretty_print=True)
            PapyrusProject.log.debug(f'Resolved PPJ. Text output:{os.linesep * 2}{xml_output.decode()}')
            sys.exit(1)

        self.options.flags_path = self.ppj_root.get(XmlAttributeName.FLAGS)
        self.options.output_path = self.ppj_root.get(XmlAttributeName.OUTPUT)

        if self.options.output_path and not os.path.isabs(self.options.output_path):
            self.options.output_path = self.get_output_path()

        def bool_attr(element: etree.Element, attr_name: str) -> bool:
            return element is not None and element.get(attr_name) == 'True'

        self.optimize = bool_attr(self.ppj_root, XmlAttributeName.OPTIMIZE)
        self.release = bool_attr(self.ppj_root, XmlAttributeName.RELEASE)
        self.final = bool_attr(self.ppj_root, XmlAttributeName.FINAL)

        self.options.anonymize = bool_attr(self.ppj_root, XmlAttributeName.ANONYMIZE)
        self.options.package = bool_attr(self.ppj_root, XmlAttributeName.PACKAGE)
        self.options.zip = bool_attr(self.ppj_root, XmlAttributeName.ZIP)

        self.imports_node = self.ppj_root.find(XmlTagName.IMPORTS)
        self.scripts_node = self.ppj_root.find(XmlTagName.SCRIPTS)
        self.folders_node = self.ppj_root.find(XmlTagName.FOLDERS)
        self.packages_node = self.ppj_root.find(XmlTagName.PACKAGES)
        self.zip_files_node = self.ppj_root.find(XmlTagName.ZIP_FILES)

        self.pre_build_node = self.ppj_root.find(XmlTagName.PRE_BUILD_EVENT)
        self.use_pre_build_event = bool_attr(self.pre_build_node, XmlAttributeName.USE_IN_BUILD)

        self.post_build_node = self.ppj_root.find(XmlTagName.POST_BUILD_EVENT)
        self.use_post_build_event = bool_attr(self.post_build_node, XmlAttributeName.USE_IN_BUILD)

        self.pre_import_node = self.ppj_root.find(XmlTagName.PRE_IMPORT_EVENT)
        self.use_pre_import_event = bool_attr(self.pre_import_node, XmlAttributeName.USE_IN_BUILD)

        self.post_import_node = self.ppj_root.find(XmlTagName.POST_IMPORT_EVENT)
        self.use_post_import_event = bool_attr(self.post_import_node, XmlAttributeName.USE_IN_BUILD)

        self.pre_compile_node = self.ppj_root.find(XmlTagName.PRE_COMPILE_EVENT)
        self.use_pre_compile_event = bool_attr(self.pre_compile_node, XmlAttributeName.USE_IN_BUILD)

        self.post_compile_node = self.ppj_root.find(XmlTagName.POST_COMPILE_EVENT)
        self.use_post_compile_event = bool_attr(self.post_compile_node, XmlAttributeName.USE_IN_BUILD)

        self.pre_anonymize_node = self.ppj_root.find(XmlTagName.PRE_ANONYMIZE_EVENT)
        self.use_pre_anonymize_event = bool_attr(self.pre_anonymize_node, XmlAttributeName.USE_IN_BUILD)

        self.post_anonymize_node = self.ppj_root.find(XmlTagName.POST_ANONYMIZE_EVENT)
        self.use_post_anonymize_event = bool_attr(self.post_anonymize_node, XmlAttributeName.USE_IN_BUILD)

        self.pre_package_node = self.ppj_root.find(XmlTagName.PRE_PACKAGE_EVENT)
        self.use_pre_package_event = bool_attr(self.pre_package_node, XmlAttributeName.USE_IN_BUILD)

        self.post_package_node = self.ppj_root.find(XmlTagName.POST_PACKAGE_EVENT)
        self.use_post_package_event = bool_attr(self.post_package_node, XmlAttributeName.USE_IN_BUILD)

        self.pre_zip_node = self.ppj_root.find(XmlTagName.PRE_ZIP_EVENT)
        self.use_pre_zip_event = bool_attr(self.pre_zip_node, XmlAttributeName.USE_IN_BUILD)

        self.post_zip_node = self.ppj_root.find(XmlTagName.POST_ZIP_EVENT)
        self.use_post_zip_event = bool_attr(self.post_zip_node, XmlAttributeName.USE_IN_BUILD)

        if self.options.package and self.packages_node is not None:
            if not self.options.package_path:
                self.options.package_path = self.packages_node.get(XmlAttributeName.OUTPUT)

        if self.options.zip and self.zip_files_node is not None:
            if not self.options.zip_output_path:
                self.options.zip_output_path = self.zip_files_node.get(XmlAttributeName.OUTPUT)

    def try_initialize_remotes(self) -> None:
        # initialize remote if needed
        if self.remote_paths:
            if not self.options.remote_temp_path:
                self.options.remote_temp_path = self.get_remote_temp_path()

            if self.options.worker_limit == 0:
                self.options.worker_limit = self.get_worker_limit()

            self.remote = GenericRemote(access_token=self.options.access_token,
                                        worker_limit=self.options.worker_limit,
                                        force_overwrite=self.options.force_overwrite)

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
                                                worker_limit=self.options.worker_limit,
                                                force_overwrite=self.options.force_overwrite)

            # validate remote paths
            for path in self.remote_paths:
                if not self.remote.validate_url(path):
                    PapyrusProject.log.error(f'Cannot proceed while node contains invalid URL: "{path}"')
                    sys.exit(1)

    def try_populate_imports(self) -> None:
        # we need to populate the list of import paths before we try to determine the game type
        # because the game type can be determined from import paths
        self.import_paths = self._get_import_paths()
        if not self.import_paths:
            PapyrusProject.log.error('Failed to build list of import paths')
            sys.exit(1)

        # remove project path, if added by user
        self.import_paths = [p for p in self.import_paths if not startswith(p, self.project_path, ignorecase=True)]

        # prepend project path
        self.import_paths.insert(0, self.project_path)

        self.psc_paths = self._get_psc_paths()
        if not self.psc_paths:
            PapyrusProject.log.error('Failed to build list of script paths')
            sys.exit(1)

    def try_set_game_type(self) -> None:
        # we need to set the game type after imports are populated but before pex paths are populated
        # allow xml to set game type but defer to passed argument
        if self.options.game_type not in GameType.values():
            attr_game_type: str = self.ppj_root.get(XmlAttributeName.GAME, default='')
            self.options.game_type = GameType.get(attr_game_type)

            if self.options.game_type:
                PapyrusProject.log.info(f'Using game type: {GameName.get(attr_game_type)} (determined from Papyrus Project)')

        if not self.options.game_type:
            self.options.game_type = self.get_game_type()

        if not self.options.game_type:
            PapyrusProject.log.error('Cannot determine game type from arguments or Papyrus Project')
            sys.exit(1)

    def find_missing_scripts(self) -> None:
        # get expected pex paths - these paths may not exist and that is okay!
        self.pex_paths = self._get_pex_paths()

        # these are relative paths to psc scripts whose pex counterparts are missing
        self.missing_scripts: dict = self._find_missing_script_paths()

    def try_set_game_path(self) -> None:
        # game type must be set before we call this
        if not self.options.game_path:
            self.options.game_path = self.get_game_path(self.options.game_type)

    @property
    def remote_paths(self) -> list:
        """
        Collects list of remote paths from Import and Folder nodes
        """
        results: list = []

        if self.imports_node is not None:
            results.extend([node.text for node in filter(is_import_node, self.imports_node)
                            if startswith(node.text, self.remote_schemas, ignorecase=True)])

        if self.folders_node is not None:
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

        # allow variables to reference other variables
        for key, value in self.variables.items():
            self.variables.update({key: self.parse(value)})

        # complete round trip so that order does not matter
        for key in reversed(self.variables.keys()):
            value = self.variables[key]
            self.variables.update({key: self.parse(value)})

        self.variables.update({
            'UNIXTIME': str(int(time.time()))
        })

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

            elif tag in (XmlTagName.FOLDER, XmlTagName.INCLUDE, XmlTagName.MATCH):
                if XmlAttributeName.NO_RECURSE not in node.attrib:
                    node.set(XmlAttributeName.NO_RECURSE, 'False')
                if tag in (XmlTagName.INCLUDE, XmlTagName.MATCH):
                    if XmlAttributeName.PATH not in node.attrib:
                        node.set(XmlAttributeName.PATH, '')
                if tag == XmlTagName.MATCH:
                    if XmlAttributeName.IN not in node.attrib:
                        node.set(XmlAttributeName.IN, os.curdir)
                    if XmlAttributeName.EXCLUDE not in node.attrib:
                        node.set(XmlAttributeName.EXCLUDE, '')

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

            elif tag in (XmlTagName.PRE_BUILD_EVENT, XmlTagName.POST_BUILD_EVENT,
                         XmlTagName.PRE_IMPORT_EVENT, XmlTagName.POST_IMPORT_EVENT):
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

    def _find_missing_script_paths(self) -> dict:
        """Returns list of script paths for compiled scripts that do not exist"""
        results: dict = {}

        for object_name, script_path in self.psc_paths.items():
            pex_path: str = os.path.join(self.get_output_path(), object_name.replace('.psc', '.pex'))

            if not os.path.isfile(pex_path) and script_path not in results:
                results[object_name] = script_path

        return results

    def _get_import_paths(self) -> list:
        """Returns absolute import paths from Papyrus Project"""
        results: list = []

        if self.imports_node is None:
            return []

        for import_node in filter(is_import_node, self.imports_node):
            import_path: str = import_node.text

            if startswith(import_path, self.remote_schemas, ignorecase=True):
                local_path = self._get_remote_path(import_node)
                PapyrusProject.log.info(f'Adding import path from remote: "{local_path}"...')
                results.append(local_path)
                continue

            if import_path == os.pardir or startswith(import_path, os.pardir):
                import_path = import_path.replace(os.pardir, os.path.normpath(os.path.join(self.project_path, os.pardir)), 1)
            elif import_path == os.curdir or startswith(import_path, os.curdir):
                import_path = import_path.replace(os.curdir, self.project_path, 1)

            # relative import paths should be relative to the project
            if not os.path.isabs(import_path):
                import_path = os.path.join(self.project_path, import_path)

            import_path = os.path.normpath(import_path)

            if os.path.isdir(import_path):
                results.append(import_path)
            else:
                PapyrusProject.log.error(f'Import path does not exist: "{import_path}"')
                sys.exit(1)

        return PathHelper.uniqify(results)

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

    def get_object_item(self, path: str) -> tuple:
        object_name = path if not os.path.isabs(path) else self._calculate_object_name(path)
        object_path = path if endswith(path, '.psc', ignorecase=True) else f'{path}.psc'
        return object_name, object_path

    def _get_psc_paths(self) -> dict:
        """Returns script paths from Folders and Scripts nodes"""
        object_names: dict = {}

        # populate object names dictionary
        if self.folders_node is not None:
            for path in self._get_script_paths_from_folders_node():
                k, v = self.get_object_item(path)
                object_names[k] = v

        if self.scripts_node is not None:
            for path in self._get_script_paths_from_scripts_node():
                k, v = self.get_object_item(path)
                object_names[k] = v

        # convert user paths to absolute paths
        for k, v in object_names.items():
            # ignore existing absolute paths
            if os.path.isabs(v) and os.path.isfile(v):
                continue

            # try to add existing import-relative paths
            for import_path in self.import_paths:
                if not os.path.isabs(import_path):
                    import_path = os.path.join(self.project_path, import_path)

                # test for shallow matches
                test_path = os.path.join(import_path, v)
                if os.path.isfile(test_path):
                    object_names[k] = test_path
                    break

                # go deep
                matcher = wcmatch.WcMatch(import_path, '*.psc', flags=wcmatch.IGNORECASE | wcmatch.RECURSIVE)

                flag = False

                for f in matcher.imatch():
                    if endswith(f, os.path.basename(v), ignorecase=True):
                        object_names[k] = f
                        flag = True
                        break

                if flag:
                    break

        PapyrusProject.log.info(f'{len(object_names)} unique script paths resolved to absolute paths.')

        return object_names

    def _get_remote_path(self, node: etree.ElementBase) -> str:
        import_path: str = node.text

        url_hash = hashlib.sha1(import_path.encode()).hexdigest()[:8]
        temp_path = os.path.join(self.options.remote_temp_path, url_hash)

        if self.options.force_overwrite or not os.path.isdir(temp_path):
            try:
                for message in self.remote.fetch_contents(import_path, temp_path):
                    if message:
                        if not startswith(message, 'Failed to load'):
                            PapyrusProject.log.info(message)
                        else:
                            PapyrusProject.log.error(message)
                            sys.exit(1)
            except PermissionError as e:
                PapyrusProject.log.error(e)
                sys.exit(1)

        if endswith(import_path, '.git', ignorecase=True):
            url_path = self.remote.create_local_path(import_path[:-4])
        else:
            url_path = self.remote.create_local_path(import_path)

        local_path = os.path.join(temp_path, url_path)

        matcher = wcmatch.WcMatch(local_path, '*.psc', flags=wcmatch.IGNORECASE | wcmatch.RECURSIVE)

        for f in matcher.imatch():
            return os.path.dirname(f)

        return local_path

    @staticmethod
    def try_fix_namespace_path(node: etree.ElementBase) -> None:
        if is_namespace_path(node):
            node.text = node.text.replace(':', os.sep)

    # noinspection DuplicatedCode
    def _get_script_paths_from_folders_node(self) -> typing.Generator:
        """Returns script paths from the Folders element array"""
        for folder_node in filter(is_folder_node, self.folders_node):
            self.try_fix_namespace_path(folder_node)

            attr_no_recurse: bool = folder_node.get(XmlAttributeName.NO_RECURSE) == 'True'

            folder_path: str = folder_node.text

            # handle . and .. in path
            if folder_path == os.pardir or startswith(folder_path, os.pardir):
                folder_path = folder_path.replace(os.pardir, os.path.normpath(os.path.join(self.project_path, os.pardir)), 1)
                yield from PathHelper.find_script_paths_from_folder(folder_path,
                                                                    no_recurse=attr_no_recurse)
                continue

            if folder_path == os.curdir or startswith(folder_path, os.curdir):
                folder_path = folder_path.replace(os.curdir, self.project_path, 1)
                yield from PathHelper.find_script_paths_from_folder(folder_path,
                                                                    no_recurse=attr_no_recurse)
                continue

            if startswith(folder_path, self.remote_schemas, ignorecase=True):
                local_path = self._get_remote_path(folder_node)
                PapyrusProject.log.info(f'Adding import path from remote: "{local_path}"...')
                self.import_paths.insert(0, local_path)
                PapyrusProject.log.info(f'Adding folder path from remote: "{local_path}"...')
                yield from PathHelper.find_script_paths_from_folder(local_path,
                                                                    no_recurse=attr_no_recurse)
                continue

            folder_path = os.path.normpath(folder_path)

            # try to add absolute path
            if os.path.isabs(folder_path) and os.path.isdir(folder_path):
                yield from PathHelper.find_script_paths_from_folder(folder_path,
                                                                    no_recurse=attr_no_recurse)
                continue

            # try to add import-relative folder path
            for import_path in self.import_paths:
                test_path = os.path.join(import_path, folder_path)
                if os.path.isdir(test_path):
                    yield from PathHelper.find_script_paths_from_folder(test_path,
                                                                        no_recurse=attr_no_recurse)

    # noinspection DuplicatedCode
    def _get_script_paths_from_scripts_node(self) -> typing.Generator:
        """Returns script paths from the Scripts node"""
        for script_node in filter(is_script_node, self.scripts_node):
            self.try_fix_namespace_path(script_node)

            script_path: str = script_node.text

            if script_path == os.pardir or script_path == os.curdir:
                PapyrusProject.log.error(f'Script path at line {script_node.sourceline} in project file is not a file path')
                sys.exit(1)

            # handle . and .. in path
            if startswith(script_path, os.pardir):
                script_path = script_path.replace(os.pardir, os.path.normpath(os.path.join(self.project_path, os.pardir)), 1)
            elif startswith(script_path, os.curdir):
                script_path = script_path.replace(os.curdir, self.project_path, 1)

            if os.path.isdir(script_path):
                PapyrusProject.log.error(f'Script path at line {script_node.sourceline} in project file is not a file path')
                sys.exit(1)

            yield os.path.normpath(script_path)

    def _try_exclude_unmodified_scripts(self) -> dict:
        psc_paths: dict = {}

        for object_name, script_path in self.psc_paths.items():
            script_name, _ = os.path.splitext(os.path.basename(script_path))

            # if pex exists, compare time_t in pex header with psc's last modified timestamp
            matching_path: str = ''
            for pex_path in self.pex_paths:
                if endswith(pex_path, f'{script_name}.pex', ignorecase=True):
                    matching_path = pex_path
                    break

            if not os.path.isfile(matching_path):
                continue

            try:
                header = PexReader.get_header(matching_path)
            except ValueError:
                PapyrusProject.log.error(f'Cannot determine compilation time due to unknown magic: "{matching_path}"')
                sys.exit(1)

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

        if self.options.no_incremental_build:
            psc_paths: dict = self.psc_paths
        else:
            psc_paths = self._try_exclude_unmodified_scripts()

        # add .psc scripts whose .pex counterparts do not exist
        for object_name, script_path in self.missing_scripts.items():
            if object_name not in psc_paths.keys():
                psc_paths[object_name] = script_path

        if endswith(self.get_compiler_path(), 'Caprica.exe', ignorecase=True):
            arguments.append(self.get_compiler_path(), enquote_value=True)

            arguments.append(os.path.join(self.program_path, 'tools', 'caprica.cfg'), key='-config-file', enquote_value=True)

            if self.options.game_type == GameType.SF1:
                arguments.append('starfield', key='g', enquote_value=True)
            elif self.options.game_type == GameType.FO4:
                arguments.append('fallout4', key='g', enquote_value=True)
            elif self.options.game_type in [GameType.TES5, GameType.SSE]:
                arguments.append('skyrim', key='g', enquote_value=True)

            arguments.append(self.get_flags_path(), key='f', enquote_value=True)
            arguments.append(';'.join(self.import_paths), key='i', enquote_value=True)
            arguments.append(self.get_output_path(), key='o', enquote_value=True)

            object_names = ';'.join(psc_paths.keys())
            arguments.append(object_names, enquote_value=True)

        else:
            for object_name, script_path in psc_paths.items():
                arguments.clear()
                arguments.append(self.get_compiler_path(), enquote_value=True)
                arguments.append(object_name if self.options.game_type == GameType.FO4 else script_path, enquote_value=True)
                arguments.append(self.get_flags_path(), key='f', enquote_value=True)
                arguments.append(';'.join(self.import_paths), key='i', enquote_value=True)
                arguments.append(self.get_output_path(), key='o', enquote_value=True)

                if self.options.game_type in [GameType.FO4, GameType.SF1]:
                    if self.release:
                        arguments.append('-release')

                    if self.final:
                        arguments.append('-final')

                if self.optimize:
                    arguments.append('-op')

        arg_s = arguments.join()
        commands.append(arg_s)

        return commands

    def try_run_event(self, event: Event) -> None:
        if event == ImportEvent.PRE:
            ProcessManager.run_event(self.pre_import_node, self.project_path)
        elif event == ImportEvent.POST:
            ProcessManager.run_event(self.post_import_node, self.project_path)
        elif event == BuildEvent.PRE:
            ProcessManager.run_event(self.pre_build_node, self.project_path)
        elif event == BuildEvent.POST:
            ProcessManager.run_event(self.post_build_node, self.project_path)
        elif event == CompileEvent.PRE:
            ProcessManager.run_event(self.pre_compile_node, self.project_path)
        elif event == CompileEvent.POST:
            ProcessManager.run_event(self.post_compile_node, self.project_path)
        elif event == AnonymizeEvent.PRE:
            ProcessManager.run_event(self.pre_anonymize_node, self.project_path)
        elif event == AnonymizeEvent.POST:
            ProcessManager.run_event(self.post_anonymize_node, self.project_path)
        elif event == PackageEvent.PRE:
            ProcessManager.run_event(self.pre_package_node, self.project_path)
        elif event == PackageEvent.POST:
            ProcessManager.run_event(self.post_package_node, self.project_path)
        elif event == ZipEvent.PRE:
            ProcessManager.run_event(self.pre_zip_node, self.project_path)
        elif event == ZipEvent.POST:
            ProcessManager.run_event(self.post_zip_node, self.project_path)
        else:
            raise NotImplementedError
