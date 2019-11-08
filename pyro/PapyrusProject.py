import glob
import multiprocessing
import os
import re
import shutil
import subprocess
import sys
import time
from collections import OrderedDict

from lxml import etree

from pyro.Anonymizer import Anonymizer
from pyro.Arguments import Arguments
from pyro.Indexer import Indexer
from pyro.Logger import Logger
from pyro.PathHelper import PathHelper
from pyro.Project import Project
from pyro.TimeElapsed import TimeElapsed
from pyro.enums import GameType


class PapyrusProject:
    log = Logger()

    def __init__(self, prj: Project):
        self.project = prj

        self.root_node = etree.parse(prj.options.input_path, etree.XMLParser(remove_blank_text=True)).getroot()
        self.output_path = self.root_node.get('Output')
        self.flags_path = self.root_node.get('Flags')
        self.game_attr = self.root_node.get('Game')
        self.use_bsarch = self.root_node.get('CreateArchive')
        self.use_anonymizer = self.root_node.get('Anonymize')

        self.game_type = prj.options.game_type

        if self.game_type == GameType.Unknown:
            flags_file = os.path.basename(self.flags_path)
            if self.game_attr:
                self.game_type = GameType.from_str(self.game_attr)
                self.log.pyro("Game type set by Game attribute in PPJ to " + self.game_attr)
            elif flags_file.startswith('Institute'):
                self.game_type = GameType.Fallout4
                self.log.warn("Game type inferred from flags file to be Fallout 4")
            elif flags_file.startswith('TESV'):
                self.game_type = GameType.SkyrimSpecialEdition
                self.log.warn("Game type guessed from flags file to be Skyrim Special Edition but can't tell for sure.")
            else:
                self.log.error("Cannot determine game type. Please add Game attribute to PPJ or specify in options.")

        prj.options.game_type = self.game_type
        prj.game_type = self.game_type
        self.game_path = prj.get_game_path()
        self.compiler_path = prj.get_compiler_path()
        self.input_path = prj.options.input_path



    @staticmethod
    def _get_node(parent_node: etree.Element, tag: str, ns: str = 'PapyrusProject.xsd') -> etree.Element:
        return parent_node.find('ns:%s' % tag, {'ns': '%s' % ns})

    @staticmethod
    def _get_node_children(parent_node: etree.Element, tag: str, ns: str = 'PapyrusProject.xsd') -> list:
        return parent_node.findall('ns:%s' % tag[:-1], {'ns': '%s' % ns})

    @staticmethod
    def _get_node_children_values(parent_node: etree.Element, tag: str) -> list:
        node = PapyrusProject._get_node(parent_node, tag)

        if node is None:
            exit(PapyrusProject.log.pyro('The PPJ file is missing the following tag: {0}'.format(tag)))

        child_nodes = PapyrusProject._get_node_children(node, tag)

        if child_nodes is None or len(child_nodes) == 0:
            sys.tracebacklimit = 0
            raise Exception('No child nodes exist for <%s> tag' % tag)

        return [str(field.text) for field in child_nodes if field.text is not None and field.text != '']

    @staticmethod
    def _open_process(command: str, use_bsarch: bool = False) -> int:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, universal_newlines=True)

        exclusions = ('Starting', 'Assembly', 'Compilation', 'Batch', 'Copyright', 'Papyrus', 'Failed', 'No output')

        line_error = re.compile('\(\d+,\d+\)')

        try:
            while process.poll() is None:
                line = process.stdout.readline().strip()
                if not use_bsarch:
                    exclude_lines = not line.startswith(exclusions)
                    PapyrusProject.log.compiler(line) if line != '' and exclude_lines and 'error(s)' not in line else None
                    if line_error.match(line) is not None:
                        process.terminate()
                        return -1
                else:
                    PapyrusProject.log.bsarch(line) if line != '' else None
            return 0

        except KeyboardInterrupt:
            try:
                process.terminate()
            except OSError:
                pass
            return -1

    @staticmethod
    def _unique_list(items: list) -> tuple:
        return tuple(OrderedDict.fromkeys(items))

    def _build_commands(self, index: Indexer) -> tuple:
        commands: list = list()

        unique_imports: tuple = self._get_imports_from_script_paths()
        script_paths: tuple = self.get_script_paths()

        arguments: Arguments = Arguments()

        for script_path in script_paths:
            if not self.project.options.disable_indexer:
                if index.compare(script_path):
                    continue

            arguments.clear()
            arguments.append_quoted(self.compiler_path)
            arguments.append_quoted(script_path)
            arguments.append_quoted(self.output_path, 'o')
            arguments.append_quoted(';'.join(unique_imports), 'i')
            arguments.append_quoted(self.flags_path, 'f')

            if self.project.is_fallout4:
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
        bsarch_path = self.project.get_bsarch_path()

        arguments = Arguments()

        arguments.append_quoted(bsarch_path)
        arguments.append('pack')
        arguments.append_quoted(script_folder)
        arguments.append_quoted(archive_path)

        if self.project.is_fallout4:
            arguments.append('-fo4')
        elif self.project.is_skyrim_special_edition:
            arguments.append('-sse')
        else:
            arguments.append('-tes5')

        return arguments.join()

    def _get_imports_from_script_paths(self) -> tuple:
        """Generate list of unique import paths from script paths"""
        script_paths: tuple = self.get_script_paths()

        xml_import_paths: list = self._get_node_children_values(self.root_node, 'Imports')

        script_import_paths = list()

        for script_path in script_paths:
            for xml_import_path in xml_import_paths:
                test_path = os.path.join(xml_import_path, os.path.dirname(script_path))

                if os.path.exists(test_path):
                    script_import_paths.append(test_path)

        return self._unique_list(script_import_paths + xml_import_paths)

    def _copy_scripts_to_temp_path(self, script_paths: tuple, tmp_scripts_path: str) -> None:
        output_path = self.output_path

        if any(dots in output_path.split(os.sep) for dots in ['.', '..']):
            output_path = os.path.normpath(os.path.join(os.path.dirname(self.input_path), output_path))

        compiled_script_paths: list = [os.path.join(output_path, script_path.replace('.psc', '.pex')) for script_path in script_paths]

        if not self.project.is_fallout4:
            compiled_script_paths = [os.path.join(output_path, os.path.basename(script_path)) for script_path in compiled_script_paths]

        for compiled_script_path in compiled_script_paths:
            abs_compiled_script_path = os.path.abspath(compiled_script_path)
            tmp_destination_path = os.path.join(tmp_scripts_path, os.path.basename(abs_compiled_script_path))

            shutil.copy2(abs_compiled_script_path, tmp_destination_path)

    def _get_absolute_script_path(self, target_path: str) -> str:
        xml_import_paths = self._get_node_children_values(self.root_node, 'Imports')

        script_paths = list()
        for xml_import_path in xml_import_paths:
            source_paths = glob.glob(os.path.join(xml_import_path, '**\*.psc'), recursive=True)
            script_paths.extend(source_paths)

        for script_path in script_paths:
            source_path = target_path.replace('.pex', '.psc')
            if script_path.endswith(source_path):
                return script_path

        raise FileExistsError('Cannot find absolute path to file:', target_path)

    def _get_script_paths_from_folders_node(self) -> tuple:
        """Retrieves script paths from the Folders node"""
        script_paths: list = list()

        folders_node = self._get_node(self.root_node, 'Folders')

        if folders_node is None:
            return ()

        # defaults to False if the attribute does not exist
        no_recurse = bool(folders_node.get('NoRecurse'))

        for folder in self._get_node_children_values(self.root_node, 'Folders'):
            # fix relative paths
            if folder == '.' or folder == '..':
                # TODO: may not have parity with how the Papyrus Compiler handles these paths
                folder = os.path.join(os.path.dirname(self.input_path), folder)
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
        for import_path in self._get_node_children_values(self.root_node, 'Imports'):
            test_path = os.path.join(import_path, folder)
            if os.path.exists(test_path):
                return test_path
        return folder

    def _get_script_paths_from_scripts_node(self) -> tuple:
        """Retrieves script paths from the Scripts node"""
        script_paths: list = list()

        scripts_node = self._get_node(self.root_node, 'Scripts')

        if scripts_node is None:
            return ()

        # "support" colons by replacing them with path separators so they're proper path parts
        # but watch out for absolute paths and use the path parts directly instead
        def fix_path(script_path: str) -> str:
            if os.path.isabs(script_path):
                namespace, file_name = map(lambda x: os.path.basename(x), [os.path.dirname(script_path), script_path])
                return os.path.join(namespace, file_name)
            return script_path.replace(':', os.sep)

        scripts = [fix_path(script_path) for script_path in self._get_node_children_values(self.root_node, 'Scripts')]

        script_paths.extend(scripts)

        return self._unique_list(script_paths)

    def _get_include_paths_from_includes_node(self) -> tuple:
        # TODO: support includes for multiple archives

        include_paths: list = list()

        includes = self._get_node(self.root_node, 'Includes')
        if includes is None:
            return ()

        try:
            includes.get('Root')
        except AttributeError:
            return ()

        includes_root = includes.get('Root')

        if not os.path.exists(includes_root) or not os.path.isabs(includes_root):
            return ()

        if includes is not None:
            include_paths = self._get_node_children_values(self.root_node, 'Includes')

        # ensure all include paths are relative
        # TODO: support absolute include paths, requires new XML attribute to specify destination path in archive
        relative_include_paths = [include_path for include_path in include_paths if not os.path.isabs(include_path)]
        if len(include_paths) != len(relative_include_paths):
            self.log.warn('Some include paths were removed. Reason: Only relative paths are supported.')

        include_paths = [os.path.join(includes_root, include_path) for include_path in include_paths]

        return self._unique_list(include_paths)

    def _parallelize(self, commands: tuple) -> None:
        multiprocessing.freeze_support()
        p = multiprocessing.Pool(processes=os.cpu_count())
        p.imap(self._open_process, commands)
        p.close()
        p.join()

    def _unparallelize(self, commands: tuple) -> None:
        """emergency deparallelize just for debugging and such"""
        for command in commands:
            print('Executing: %s' % command)
            self._open_process(command, self.use_bsarch)

    def anonymize_scripts(self, script_paths: tuple, output_path: str) -> None:
        if self.project.options.disable_anonymizer:
            self.log.warn('Anonymizer disabled by user.')
        elif not self.use_anonymizer:
            self.log.warn('Anonymizer not enabled in PPJ.')
        else:
            anon = Anonymizer(self.project)
            for relative_path in script_paths:
                pex_path = os.path.join(output_path, relative_path)
                self.log.anon('INFO: Anonymizing: ' + pex_path)
                anon.anonymize_script(pex_path)

    def compile_custom(self, index: Indexer, time_elapsed: TimeElapsed) -> None:
        commands = self._build_commands(index)
        time_elapsed.start_time = time.time()
        if self.project.options.disable_parallel:
            self._unparallelize(commands)
        else:
            self._parallelize(commands)
        time_elapsed.end_time = time.time()

    def get_output_path(self) -> str:
        output_path = self.output_path

        if any(dots in output_path.split(os.sep) for dots in ['.', '..']):
            input_folder = os.path.dirname(self.input_path)
            output_path = os.path.join(input_folder, output_path)

        return output_path

    def get_script_paths(self, absolute_paths: bool = False) -> tuple:
        """Retrieves script paths both Folders and Scripts nodes"""
        paths: list = list()

        folders_node_paths = self._get_script_paths_from_folders_node()
        if len(folders_node_paths) > 0:
            paths.extend(folders_node_paths)

        scripts_node_paths = self._get_script_paths_from_scripts_node()
        if len(scripts_node_paths) > 0:
            paths.extend(scripts_node_paths)

        results = list(map(lambda x: os.path.normpath(x), paths))

        if absolute_paths:
            # TODO: soooo many loops... :(
            xml_import_paths = self._get_node_children_values(self.root_node, 'Imports')
            results = [os.path.join(xml_import_path, script_path) for script_path in results for xml_import_path in xml_import_paths]
            results = [absolute_script_path for absolute_script_path in results if os.path.exists(absolute_script_path)]

        return self._unique_list(results)

    def get_script_paths_compiled(self) -> tuple:
        output_path = self.get_output_path()

        # only fo4 supports namespaced script names
        psc_paths = [script_path if self.project.is_fallout4 else os.path.basename(script_path)
                     for script_path in self.get_script_paths()]

        # return paths to compiled scripts
        pex_paths = [os.path.join(output_path, script_path).replace('.psc', '.pex') for script_path in psc_paths]

        return tuple(os.path.normpath(pex_path) for pex_path in pex_paths if os.path.exists(pex_path))

    def index_scripts(self, script_paths: tuple, index: Indexer) -> None:
        for relative_path in script_paths:
            try:
                source_path = self._get_absolute_script_path(relative_path)
            except FileExistsError:
                source_path = ''.join([x for x in self.get_script_paths(True) if x.endswith(relative_path)])
                if source_path == '' or not os.path.exists(source_path):
                    raise

            index.write_row(source_path)

    def pack_archive(self) -> None:
        if self.project.options.disable_bsarch:
            self.log.warn('BSA/BA2 packing disabled by user.')
            return

        if not self.use_bsarch:
            self.log.warn('BSA/BA2 packing not enabled in PPJ.')
            return

        # create temporary folder
        tmp_path: str = PathHelper.parse(self.project._ini['Pyro']['TempPath'])
        tmp_scripts_path = os.path.join(tmp_path, 'Scripts')

        # clear temporary data
        if os.path.exists(tmp_path):
            shutil.rmtree(tmp_path)

        os.makedirs(tmp_path, exist_ok=True)
        os.makedirs(tmp_scripts_path, exist_ok=True)

        script_paths = self.get_script_paths()

        self._copy_scripts_to_temp_path(script_paths, tmp_scripts_path)

        # copy includes to archive
        include_paths = self._get_include_paths_from_includes_node()

        if len(include_paths) > 0:
            root_path = os.path.dirname(self.output_path)

            for include_path in include_paths:
                relative_include_path = os.path.relpath(include_path, root_path)
                target_path = os.path.join(tmp_path, relative_include_path)
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                shutil.copy2(include_path, target_path)

        archive_path = self.root_node.get('Archive')

        if archive_path is None:
            PapyrusProject.log.error('Cannot pack archive because Archive attribute not set')
            return

        commands = self._build_commands_bsarch(*map(lambda x: os.path.normpath(x), [tmp_path, archive_path]))

        self._open_process(commands, use_bsarch=True)

        # clear temporary data
        if os.path.exists(tmp_path):
            shutil.rmtree(tmp_path)

    def validate_project(self, index: Indexer, time_elapsed: TimeElapsed) -> tuple:
        output_path = self.get_output_path()

        pex_paths = self.get_script_paths_compiled()

        # return relative paths to indexable scripts
        validated_paths = list()
        validation_states = set()

        for script_path in pex_paths:
            validation_state = self.project.validate_script(script_path, time_elapsed)
            validation_states.add(validation_state)

            if validation_state.FILE_MODIFIED:
                relative_script_path = os.path.relpath(script_path, output_path)
                validated_paths.append(relative_script_path)

        if len(validated_paths) == 0:
            self.log.warn('No source scripts were indexed. Possible reason: No source scripts were recently modified.')
            return tuple()

        if self.project.options.disable_indexer:
            self.log.warn('No source scripts were indexed. Indexing disabled by user.')
            return tuple()

        self.index_scripts(tuple(validated_paths), index)

        return validated_paths, validation_states
