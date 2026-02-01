from __future__ import annotations

import configparser
import hashlib
import logging
import os
import sys
from typing import TYPE_CHECKING

from lxml import etree

from pyro.Comparators import (endswith,
                              startswith,
                              is_import_node,
                              is_folder_node)
from pyro.Remotes.GenericRemote import GenericRemote
from pyro.Remotes.RemoteBase import RemoteBase
from pyro.PathUtils import normalize_path

from wcmatch import wcmatch

if TYPE_CHECKING:
    from pyro.PapyrusProject import PapyrusProject


class ImportHandler:
    log: logging.Logger = logging.getLogger('pyro')

    def __init__(self, papyrus_project: PapyrusProject) -> None:
        self.project = papyrus_project
        self.imports_node = papyrus_project.xml_handler.imports_node
        self.folders_node = papyrus_project.xml_handler.folders_node
        self.remote: RemoteBase | None = None
        self.remote_schemas = ('https:', 'http:')

    @property
    def remote_paths(self) -> list[str]:
        """
        Collects list of remote paths from Import and Folder nodes
        """
        results: list[str] = []

        if self.imports_node is not None:
            results.extend([node.text for node in filter(is_import_node, self.imports_node)
                            if startswith(node.text, self.remote_schemas, ignorecase=True)])

        if self.folders_node is not None:
            results.extend([node.text for node in filter(is_folder_node, self.folders_node)
                            if startswith(node.text, self.remote_schemas, ignorecase=True)])

        return results

    def try_initialize_remotes(self) -> None:
        # initialize remote if needed
        if self.remote_paths:
            if not self.project.options.remote_temp_path:
                self.project.options.remote_temp_path = self.project.get_remote_temp_path()

            if self.project.options.worker_limit == 0:
                self.project.options.worker_limit = self.project.get_worker_limit()

            self.remote = GenericRemote(access_token=self.project.options.access_token,
                                        worker_limit=self.project.options.worker_limit,
                                        force_overwrite=self.project.options.force_overwrite)

            if not self.project.options.access_token:
                cfg_parser = configparser.ConfigParser()
                cfg_path = os.path.join(self.project.program_path, '.secrets')

                try:
                    parsed_files = cfg_parser.read(cfg_path)
                except configparser.DuplicateSectionError:
                    self.log.error('Cannot proceed while ".secrets" contains duplicate sections')
                    sys.exit(1)
                except configparser.MissingSectionHeaderError:
                    self.log.error('Cannot proceed while ".secrets" contains no sections')
                    sys.exit(1)

                if cfg_path in parsed_files:
                    self.remote = GenericRemote(config=cfg_parser,
                                                worker_limit=self.project.options.worker_limit,
                                                force_overwrite=self.project.options.force_overwrite)

            # validate remote paths
            for path in self.remote_paths:
                if not self.remote.validate_url(path):
                    self.log.error(f'Cannot proceed while node contains invalid URL: "{path}"')
                    sys.exit(1)

    def get_import_paths(self) -> list[str]:
        """Returns absolute import paths from Papyrus Project"""
        results: list[str] = []

        if self.imports_node is None:
            return []

        for import_node in filter(is_import_node, self.imports_node):
            import_path: str = import_node.text

            if startswith(import_path, self.remote_schemas, ignorecase=True):
                local_path = self._get_remote_path(import_node)
                self.log.info(f'Adding import path from remote: "{local_path}"...')
                results.append(local_path)
            else:
                import_path = str(normalize_path(import_path, base=self.project.project_path))
                if not os.path.isdir(import_path):
                    self.log.error(f'Import path does not exist: "{import_path}"')
                    sys.exit(1)
                results.append(import_path)

        # Remove duplicates while preserving order
        return list(dict.fromkeys(results))

    def _get_remote_path(self, node: etree.ElementBase) -> str:
        import_path: str = node.text

        url_hash = hashlib.sha1(import_path.encode()).hexdigest()[:8]
        temp_path = os.path.join(self.project.options.remote_temp_path, url_hash)

        if self.project.options.force_overwrite or not os.path.isdir(temp_path):
            try:
                for message in self.remote.fetch_contents(import_path, temp_path):
                    if message:
                        if not startswith(message, 'Failed to load'):
                            self.log.info(message)
                        else:
                            self.log.error(message)
                            sys.exit(1)
            except PermissionError as e:
                self.log.error(e)
                sys.exit(1)

        if endswith(import_path, '.git', ignorecase=True):
            url_path = self.remote.create_local_path(import_path[:-4])
        else:
            url_path = self.remote.create_local_path(import_path)

        local_path = os.path.join(temp_path, url_path)

        matcher = wcmatch.WcMatch(local_path, '*.psc', flags=wcmatch.IGNORECASE | wcmatch.RECURSIVE)

        for f in matcher.imatch():
            return str(os.path.dirname(f))

        return str(local_path)
