import logging
import os
import sys
import time

from lxml import etree

from pyro.CommandArguments import CommandArguments
from pyro.Comparators import (endswith,
                              is_variable_node,
                              is_namespace_path,
                              startswith)
from pyro.Constants import (GameName,
                            GameType,
                            XmlAttributeName,
                            XmlTagName)
from pyro.Enums.Event import (Event)
from pyro.EventHandler import EventHandler
from pyro.ImportHandler import ImportHandler
from pyro.PapyrusXmlHandler import PapyrusXmlHandler
from pyro.ProjectBase import ProjectBase
from pyro.ProjectOptions import ProjectOptions
from pyro.Remotes.RemoteBase import RemoteBase
from pyro.ScriptHandler import ScriptHandler
from pyro.XmlRoot import XmlRoot


class PapyrusProject(ProjectBase):
    log: logging.Logger = logging.getLogger('pyro')

    ppj_root: XmlRoot
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

    remote: RemoteBase
    remote_schemas: tuple = ('https:', 'http:')

    zip_file_name: str = ''
    zip_root_path: str = ''

    missing_scripts: dict = {}
    pex_paths: list = []
    psc_paths: dict = {}

    xml_handler: PapyrusXmlHandler
    import_handler: ImportHandler
    script_handler: ScriptHandler
    event_handler: EventHandler

    def __init__(self, options: ProjectOptions) -> None:
        super(PapyrusProject, self).__init__(options)

        self.xml_handler = PapyrusXmlHandler(self.options.input_path, self.program_path)

        if self.options.create_project:
            sys.exit(1)

        self.xml_handler.variables_node = self.xml_handler.ppj_root.find(XmlTagName.VARIABLES)
        if self.xml_handler.variables_node is not None:
            self._parse_variables(self.xml_handler.variables_node)

        self.xml_handler.update_attributes(self.parse)

        if self.options.resolve_project:
            xml_output = etree.tostring(self.xml_handler.ppj_root.node, encoding='utf-8', xml_declaration=True, pretty_print=True)  # type: ignore[assignment]
            PapyrusProject.log.debug(f'Resolved PPJ. Text output:{os.linesep * 2}{xml_output.decode()}')
            sys.exit(1)

        self.options.flags_path = self.xml_handler.flags_path
        self.options.output_path = self.xml_handler.output_path

        if self.options.output_path and not os.path.isabs(self.options.output_path):
            self.options.output_path = self.get_output_path()

        self.optimize = self.xml_handler.get_boolean_attribute(self.xml_handler.ppj_root, XmlAttributeName.OPTIMIZE)
        self.release = self.xml_handler.get_boolean_attribute(self.xml_handler.ppj_root, XmlAttributeName.RELEASE)
        self.final = self.xml_handler.get_boolean_attribute(self.xml_handler.ppj_root, XmlAttributeName.FINAL)

        self.options.anonymize = self.xml_handler.get_boolean_attribute(self.xml_handler.ppj_root, XmlAttributeName.ANONYMIZE)
        self.options.package = self.xml_handler.get_boolean_attribute(self.xml_handler.ppj_root, XmlAttributeName.PACKAGE)
        self.options.zip = self.xml_handler.get_boolean_attribute(self.xml_handler.ppj_root, XmlAttributeName.ZIP)

        self.imports_node = self.xml_handler.imports_node
        self.scripts_node = self.xml_handler.scripts_node
        self.folders_node = self.xml_handler.folders_node
        self.packages_node = self.xml_handler.packages_node
        self.zip_files_node = self.xml_handler.zip_files_node

        self.pre_build_node = self.xml_handler.pre_build_node
        self.use_pre_build_event = self.xml_handler.use_pre_build_event

        self.post_build_node = self.xml_handler.post_build_node
        self.use_post_build_event = self.xml_handler.use_post_build_event

        self.pre_import_node = self.xml_handler.pre_import_node
        self.use_pre_import_event = self.xml_handler.use_pre_import_event

        self.post_import_node = self.xml_handler.post_import_node
        self.use_post_import_event = self.xml_handler.use_post_import_event

        self.pre_compile_node = self.xml_handler.pre_compile_node
        self.use_pre_compile_event = self.xml_handler.use_pre_compile_event

        self.post_compile_node = self.xml_handler.post_compile_node
        self.use_post_compile_event = self.xml_handler.use_post_compile_event

        self.pre_anonymize_node = self.xml_handler.pre_anonymize_node
        self.use_pre_anonymize_event = self.xml_handler.use_pre_anonymize_event

        self.post_anonymize_node = self.xml_handler.post_anonymize_node
        self.use_post_anonymize_event = self.xml_handler.use_post_anonymize_event

        self.pre_package_node = self.xml_handler.pre_package_node
        self.use_pre_package_event = self.xml_handler.use_pre_package_event

        self.post_package_node = self.xml_handler.post_package_node
        self.use_post_package_event = self.xml_handler.use_post_package_event

        self.pre_zip_node = self.xml_handler.pre_zip_node
        self.use_pre_zip_event = self.xml_handler.use_pre_zip_event

        self.post_zip_node = self.xml_handler.post_zip_node
        self.use_post_zip_event = self.xml_handler.use_post_zip_event

        self.import_handler = ImportHandler(self)
        self.script_handler = ScriptHandler(self)
        self.event_handler = EventHandler(self)

        if self.options.package and self.packages_node is not None:
            if not self.options.package_path:
                self.options.package_path = self.xml_handler.packages_output

        if self.options.zip and self.zip_files_node is not None:
            if not self.options.zip_output_path:
                self.options.zip_output_path = self.xml_handler.zip_output

    @staticmethod
    def try_fix_namespace_path(node: etree.ElementBase) -> None:
        if is_namespace_path(node):
            node.text = node.text.replace(':', os.sep)

    def try_initialize_remotes(self) -> None:
        self.import_handler.try_initialize_remotes()
        self.remote = self.import_handler.remote

    def try_populate_imports(self) -> None:
        # we need to populate the list of import paths before we try to determine the game type
        # because the game type can be determined from import paths
        self.import_paths = self.import_handler.get_import_paths()
        if not self.import_paths:
            PapyrusProject.log.error('Failed to build list of import paths')
            sys.exit(1)

        # prepend project path
        self.import_paths.insert(0, self.project_path)

        self.psc_paths = self.script_handler.get_psc_paths()
        if not self.psc_paths:
            PapyrusProject.log.error('Failed to build list of script paths')
            sys.exit(1)

    def try_set_game_type(self) -> None:
        # we need to set the game type after imports are populated but before pex paths are populated
        # allow xml to set game type but defer to passed argument
        if self.options.game_type not in GameType.values():
            attr_game_type: str = self.xml_handler.game_type
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
        self.pex_paths = self.script_handler.get_pex_paths()

        # these are relative paths to psc scripts whose pex counterparts are missing
        self.missing_scripts: dict = self.script_handler.find_missing_scripts()

    def try_set_game_path(self) -> None:
        # game type must be set before we call this
        if not self.options.game_path:
            self.options.game_path = self.get_game_path(self.options.game_type)

    def _parse_variables(self, variables_node: etree.ElementBase) -> None:
        reserved_characters: tuple = ('!', '#', '^', '&', '*')

        # noinspection PyTypeChecker
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

        self.variables.update({
            'UNIXTIME': str(int(time.time())),
            'PROGRAM_PATH': self.program_path,
            'PROJECT_PATH': self.project_path,
            'O_BSARCH_PATH': self.options.bsarch_path,
            'O_COMPILER_PATH': self.options.compiler_path,
            'O_COMPILER_CONFIG_PATH': self.options.compiler_config_path,
            'O_FLAGS_PATH': self.options.flags_path,
            'O_GAME_PATH': self.options.game_path,
            'O_LOG_PATH': self.options.log_path,
            'O_OUTPUT_PATH': self.options.output_path,
            'O_PACKAGE_PATH': self.options.package_path,
            'O_REGISTRY_PATH': self.options.registry_path,
            'O_REMOTE_TEMP_PATH': self.options.remote_temp_path,
            'O_TEMP_PATH': self.options.temp_path,
            'O_ZIP_OUTPUT_PATH': self.options.zip_output_path
        })

        # allow variables to reference other variables
        for key, value in self.variables.items():
            self.variables.update({key: self.parse(value)})

        # complete round trip so that order does not matter
        for key in reversed(self.variables.keys()):
            value = self.variables[key]
            self.variables.update({key: self.parse(value)})

    def build_commands(self) -> tuple[int, list]:
        """
        Builds list of commands for compiling scripts
        """
        commands: list = []

        arguments = CommandArguments()

        if self.options.no_incremental_build:
            psc_paths: dict = self.psc_paths
        else:
            psc_paths = self.script_handler.try_exclude_unmodified_scripts()

        # add .psc scripts whose .pex counterparts do not exist
        for object_name, script_path in self.missing_scripts.items():
            if object_name not in psc_paths.keys():
                psc_paths[object_name] = script_path

        # do not try to compile nothing
        if psc_paths is None or psc_paths == {}:
            return 0, []

        if endswith(self.get_compiler_path(), 'Caprica.exe', ignorecase=True):
            arguments.append(self.get_compiler_path(), enquote_value=True)

            object_names = ';'.join(psc_paths.keys())

            with open(self.get_compiler_config_path(), encoding='utf-8') as f:
                options = f.read().splitlines()

            # disable parallel compilation if the user overrides the default
            if self.options.no_parallel and 'parallel-compile=1' in options:
                for i, option in enumerate(options):
                    if startswith(option, 'parallel-compile', ignorecase=True):
                        options.pop(i)
                        break

            use_config_file_for_input_paths = False

            if len(object_names) > 32486:  # 32766 total - 280 chars for all arguments
                use_config_file_for_input_paths = True
                options.append(f'input-file={object_names.strip()}\n')

            config_dir_path = os.path.dirname(self.get_compiler_config_path())
            config_file_path = os.path.join(config_dir_path, f'caprica_{str(int(time.time()))}.cfg')

            with open(config_file_path, mode='w', encoding='utf-8') as f:
                f.write('\n'.join(options))

            arguments.append(config_file_path, key='-config-file', enquote_value=True)

            # caprica defaults to starfield
            game_name = 'starfield'
            if self.options.game_type == GameType.FO4:
                game_name = 'fallout4'
            elif self.options.game_type in [GameType.TES5, GameType.SSE]:
                game_name = 'skyrim'

            arguments.append(game_name, key='g', enquote_value=True)

            arguments.append(self.get_flags_path(), key='f', enquote_value=True)
            arguments.append(';'.join(self.import_paths), key='i', enquote_value=True)
            arguments.append(self.get_output_path(), key='o', enquote_value=True)

            if not use_config_file_for_input_paths:
                arguments.append(object_names, enquote_value=True)

            arg_s = arguments.join()
            commands.append(arg_s)

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

        return len(psc_paths.keys()), commands

    def try_run_event(self, event: Event) -> None:
        self.event_handler.try_run_event(event)
