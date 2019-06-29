import binascii
import json
import os
import posixpath

from Pyro.Logger import Logger
from Pyro.PathHelper import PathHelper
from Pyro.Project import Project


class Checksum:
    def __init__(self, file_path: str, crc32: str):
        # use only forward slashes in json
        self.file_path: str = posixpath.join(*file_path.split('\\')) if '\\' in file_path else file_path
        self.crc32: str = crc32


class Indexer:
    """
    The index is used to exclude unchanged scripts from compilation. It does this by writing an
    index of CRC32 hashes after verification and comparing those hashes before compilation.
    """
    logger = Logger()

    def __init__(self, project: Project, project_name: str, script_paths: tuple):
        self.project: Project = project
        self.project_name: str = project_name
        self.script_paths: tuple = script_paths

        table_path: str = os.path.join(PathHelper.parse(self.project._ini['Pyro']['CachePath']), '{}.json'.format(project_name))
        self.table_path: str = os.path.normpath(table_path)

        os.makedirs(os.path.dirname(self.table_path), exist_ok=True)

        self.checksums: list = []

        # ensure table file exists
        if not os.path.exists(self.table_path):
            open(self.table_path, mode='wb').close()

        # ensure table file has a checksums list
        with open(self.table_path, mode='r') as f:
            try:
                json.load(f)
            except json.decoder.JSONDecodeError:
                self._create_table_file()

        # load checksums list
        with open(self.table_path, mode='r') as f:
            table = json.load(f)
            self.checksums = table['checksums']

    def _create_table_file(self) -> None:
        with open(self.table_path, mode='w') as o:
            json.dump({'checksums': []}, o, indent=4)

    @staticmethod
    def _get_crc32(file_path: str) -> str:
        buffer: bytes = open(file_path, 'rb').read()
        return "{:08X}".format(binascii.crc32(buffer) & 0xFFFFFFFF)

    @staticmethod
    def _find_file(rows: list, file_path: str) -> tuple:
        for i, row in enumerate(rows):
            if PathHelper.compare(row['file_path'], file_path):
                return i, row
        raise FileNotFoundError(f'Cannot find file at path: {file_path}')

    def compare(self, target_path: str) -> bool:
        """Returns True if the checksum matches"""
        script_path: str = ''.join([x for x in self.script_paths if PathHelper.compare(x, target_path)])

        if not script_path:
            # self.log.idxr(f'Found no results for "{target_path}"')
            return False

        row_hashes: list = [row['crc32'] for row in self.checksums if PathHelper.compare(row['file_path'], target_path)]

        if len(row_hashes) == 0:
            # self.log.idxr(f'Found no results in checksums for "{target_path}"')
            return False

        # if there is more than one result, the problem was created by the user... right?
        if len(row_hashes) > 1:
            self.logger.idxr(f'Found more than one result for "{target_path}"')
            return False

        if row_hashes[0] == self._get_crc32(script_path):
            return True

        return False

    def write_row(self, script_path: str) -> None:
        new_row: Checksum = Checksum(script_path, self._get_crc32(script_path))

        os.makedirs(os.path.dirname(self.table_path), exist_ok=True)

        # ensure we can read table and there is a checksums list
        with open(self.table_path, mode='r') as f:
            try:
                json.load(f)
            except json.decoder.JSONDecodeError:
                self._create_table_file()

        with open(self.table_path, mode='r') as f:
            table: dict = json.load(f)

            # check if there's an existing row for the file path
            try:
                row_index, row_data = self._find_file(table['checksums'], new_row.file_path)
            except FileNotFoundError:
                # if there isn't an existing row, add one
                table['checksums'].append(new_row.__dict__)

            # if there is an existing row, update the crc32
            # this will never run unless Project.validate_script() returns True in PapyrusProject.validate_project()
            # that is, this will run when a previously indexed script has been changed and compiled
            else:
                if row_data['crc32'] != new_row.crc32:
                    table['checksums'][row_index]['crc32'] = new_row.crc32

            with open(self.table_path, mode='w') as o:
                json.dump(table, o, indent=4)

    def write(self) -> None:
        def checksum_dict(script_path: str) -> dict:
            return Checksum(posixpath.normpath(script_path), self._get_crc32(script_path)).__dict__

        results: list = [checksum_dict(script_path) for script_path in [os.path.normpath(x) for x in self.script_paths]]

        os.makedirs(os.path.dirname(self.table_path), exist_ok=True)

        with open(self.table_path, mode='w') as f:
            json.dump({'checksums': results}, f, indent=4)
