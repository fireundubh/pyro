import logging
import os
import sys
import typing

from wcmatch import wcmatch

from pyro.Comparators import (endswith,
                              startswith,
                              is_folder_node, is_script_node)
from pyro.Constants import (XmlAttributeName)
from pyro.PathHelper import PathHelper
from pyro.PexReader import PexReader


class ScriptHandler:
    log: logging.Logger = logging.getLogger('pyro')

    def __init__(self, papyrus_project) -> None:
        self.project = papyrus_project
        self.scripts_node = papyrus_project.xml_handler.scripts_node
        self.folders_node = papyrus_project.xml_handler.folders_node
        self.psc_paths: dict = {}
        self.pex_paths: list = []
        self.missing_scripts: dict = {}

    def get_psc_paths(self) -> dict:
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
            for import_path in self.project.import_paths:
                if not os.path.isabs(import_path):
                    import_path = os.path.join(self.project.project_path, import_path)

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

        self.log.info(f'{len(object_names)} unique script paths resolved to absolute paths.')

        self.psc_paths = object_names
        return object_names

    def get_object_item(self, path: str) -> tuple:
        object_name = path if not os.path.isabs(path) else self._calculate_object_name(path)
        object_path = path if endswith(path, '.psc', ignorecase=True) else f'{path}.psc'
        return object_name, object_path

    def _calculate_object_name(self, psc_path: str) -> str:
        return PathHelper.calculate_relative_object_name(psc_path, self.project.import_paths)

    def _get_script_paths_from_folders_node(self) -> typing.Generator:
        """Returns script paths from the Folders element array"""
        for folder_node in filter(is_folder_node, self.folders_node):
            self.project.try_fix_namespace_path(folder_node)

            attr_no_recurse: bool = folder_node.get(XmlAttributeName.NO_RECURSE) == 'True'

            folder_path: str = folder_node.text

            if startswith(folder_path, self.project.import_handler.remote_schemas, ignorecase=True):
                local_path = self.project.import_handler._get_remote_path(folder_node)
                self.log.info(f'Adding import path from remote: "{local_path}"...')
                self.project.import_paths.insert(0, local_path)
                self.log.info(f'Adding folder path from remote: "{local_path}"...')
                yield from PathHelper.find_script_paths_from_folder(local_path, no_recurse=attr_no_recurse)
                continue

            folder_path = PathHelper.normalize_relative_path(folder_path, self.project.project_path)

            # try to add absolute path
            if os.path.isabs(folder_path) and os.path.isdir(folder_path):
                yield from PathHelper.find_script_paths_from_folder(folder_path, no_recurse=attr_no_recurse)
                continue

            # try to add import-relative folder path
            for import_path in self.project.import_paths:
                test_path = os.path.join(import_path, folder_path)
                if os.path.isdir(test_path):
                    yield from PathHelper.find_script_paths_from_folder(test_path, no_recurse=attr_no_recurse)

    def _get_script_paths_from_scripts_node(self) -> typing.Generator:
        """Returns script paths from the Scripts node"""
        for script_node in filter(is_script_node, self.scripts_node):
            self.project.try_fix_namespace_path(script_node)

            script_path: str = script_node.text

            if script_path in (os.pardir, os.curdir):
                self.log.error(f'Script path at line {script_node.sourceline} in project file is not a file path')
                sys.exit(1)

            script_path = PathHelper.normalize_relative_path(script_path, self.project.project_path)

            if os.path.isdir(script_path):
                self.log.error(f'Script path at line {script_node.sourceline} in project file is not a file path')
                sys.exit(1)

            yield script_path

    def get_pex_paths(self) -> list:
        """
        Returns absolute paths to compiled scripts that may not exist yet in output folder
        """
        pex_paths: list = []

        for object_name, script_path in self.psc_paths.items():
            # noinspection PyTypeChecker
            pex_path = os.path.join(self.project.options.output_path, os.path.basename(script_path).replace('.psc', '.pex'))

            # do not check if file exists, we do that in _find_missing_script_paths for a different reason
            if pex_path not in pex_paths:
                pex_paths.append(pex_path)

        self.pex_paths = pex_paths
        return pex_paths

    def find_missing_scripts(self) -> dict:
        """Returns list of script paths for compiled scripts that do not exist"""
        results: dict = {}

        for object_name, script_path in self.psc_paths.items():
            if endswith(object_name, '.pex', ignorecase=True):
                pex_path = os.path.join(self.project.get_output_path(), object_name)
            elif endswith(object_name, '.psc', ignorecase=True):
                pex_path = os.path.join(self.project.get_output_path(), object_name.replace('.psc', '.pex'))
            else:
                pex_path = os.path.join(self.project.get_output_path(), object_name + '.pex')

            if not os.path.isfile(pex_path) and script_path not in results:
                results[object_name] = script_path

        self.missing_scripts = results
        return results

    def try_exclude_unmodified_scripts(self) -> dict:
        psc_paths: dict = {}

        for object_name, script_path in self.psc_paths.items():
            if endswith(object_name, '.pex', ignorecase=True):
                script_name = object_name
            elif endswith(object_name, '.psc', ignorecase=True):
                script_name = object_name.replace('.psc', '.pex')
            else:
                script_name = object_name + '.pex'

            # if pex exists, compare time_t in pex header with psc's last modified timestamp
            matching_path: str = ''
            for pex_path in self.pex_paths:
                if endswith(pex_path, script_name, ignorecase=True):
                    matching_path = pex_path
                    break

            if not os.path.isfile(matching_path):
                continue

            try:
                header = PexReader.get_header(matching_path)
            except ValueError:
                self.log.error(f'Cannot determine compilation time due to unknown magic: "{matching_path}"')
                sys.exit(1)

            compiled_time: int = header.compilation_time.value
            if os.path.getmtime(script_path) < compiled_time:
                continue

            if script_path not in psc_paths:
                psc_paths[object_name] = script_path

        return psc_paths
