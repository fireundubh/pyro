import multiprocessing
import os
import subprocess
import sys

from collections import OrderedDict

try:
    from lxml import etree
except ImportError:
    subprocess.call([sys.executable, '-m', 'pip', 'install', 'lxml'])
    # noinspection PyUnresolvedReferences
    from lxml import etree

from Arguments import Arguments
from GameType import GameType
from Project import Project
from TimeElapsed import TimeElapsed


class PapyrusProject:
    def __init__(self, prj: Project):
        self.project = prj
        self.compiler_path = prj.get_compiler_path()
        self.game_type = prj.game_type
        self.input_path = prj.input_path
        self.root_node = etree.parse(prj.input_path, etree.XMLParser(remove_blank_text=True)).getroot()

    @staticmethod
    def _get_children_nodes(parent_node: etree.Element, tag: str, ns: str = 'PapyrusProject.xsd') -> list:
        node = parent_node.find('ns:%s' % tag, {'ns': '%s' % ns})
        return node.findall('ns:%s' % tag[:-1], {'ns': '%s' % ns})

    @staticmethod
    def _get_children_values(parent_node: etree.Element, tag: str) -> list:
        child_nodes = PapyrusProject._get_children_nodes(parent_node, tag)

        if child_nodes is None or len(child_nodes) == 0:
            raise Exception('No child nodes exist for tag:', tag)

        return [str(field.text) for field in child_nodes if field.text is not None and field.text != '']

    @staticmethod
    def _open_process(command: list) -> int:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, universal_newlines=True)

        try:
            while process.poll() is None:
                line = process.stdout.readline().strip()
                exclude_lines = not line.startswith(('Starting', 'Assembly', 'Compilation', 'Batch')) and 'error(s)' not in line
                print('[COMPILER]', line) if line != '' and exclude_lines else None
            return 0

        except KeyboardInterrupt:
            try:
                process.terminate()
            except OSError:
                pass
            return 0

    @staticmethod
    def _unique_list(items: list) -> list:
        return list(OrderedDict.fromkeys(items))

    def _get_imports_from_root_node(self) -> list:
        return self._get_children_values(self.root_node, 'Imports')

    def _get_imports_from_script_paths(self) -> list:
        """Generate list of unique import paths from script paths"""
        script_paths = self.get_script_paths()
        xml_import_paths = self._get_imports_from_root_node()

        script_import_paths = [os.path.join(xml_import_path, os.path.dirname(script_path))
                               for xml_import_path in xml_import_paths
                               for script_path in script_paths]

        script_import_paths = [script_import_path for script_import_path in script_import_paths
                               if os.path.exists(script_import_path)]

        return self._unique_list(script_import_paths + xml_import_paths)

    def _build_commands(self, output_path: str, quiet: bool) -> list:
        commands = list()

        arguments = Arguments()
        unique_imports = self._get_imports_from_script_paths()

        for script_path in self.get_script_paths():
            arguments.clear()
            arguments.append_quoted(self.compiler_path)
            arguments.append_quoted(script_path)
            arguments.append_quoted(output_path, 'o')
            arguments.append_quoted(';'.join(unique_imports), 'i')
            arguments.append_quoted(self.root_node.get('Flags'), 'f')

            if self.game_type == GameType.Fallout4:
                release = self.root_node.get('Release')
                if release and release.casefold() == 'true':
                    arguments.append('-release')

                final = self.root_node.get('Final')
                if final and final.casefold() == 'true':
                    arguments.append('-final')

            if quiet:
                arguments.append('-q')

            commands.append(arguments.join())

        return commands

    def get_script_paths(self) -> list:
        script_paths = self._get_children_values(self.root_node, 'Scripts')
        return self._unique_list(script_paths)

    def get_output_path(self) -> str:
        return self.root_node.get('Output')

    def compile(self, quiet: bool) -> None:
        output_path = self.get_output_path()

        commands = self._build_commands(output_path, quiet)

        p = multiprocessing.Pool(processes=os.cpu_count())
        p.map(self._open_process, commands)
        p.close()
        p.join()

    def validate_project(self, time_elapsed: TimeElapsed) -> None:
        output_path = self.get_output_path()
        script_paths = self.get_script_paths()

        compiled_script_paths = map(lambda x: os.path.join(output_path, x.replace('.psc', '.pex')), script_paths)

        if not self.project.is_fallout4:
            compiled_script_paths = map(lambda x: os.path.join(output_path, os.path.basename(x)), compiled_script_paths)

        for compiled_script_path in compiled_script_paths:
            self.project.validate_script(compiled_script_path, time_elapsed)
