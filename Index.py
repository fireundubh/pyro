import binascii
import json
import os
from Logger import Logger


class Index:
    """
    The index is used to exclude unchanged scripts from compilation. It does this by writing an
    index of CRC32 hashes after verification and comparing those hashes before compilation.
    """
    log = Logger()

    def __init__(self, project_name: str, script_paths: list):
        self.project_name = project_name
        self.script_paths = script_paths

        table_path = os.path.join(os.path.dirname(__file__), 'Database', '{}.json'.format(project_name))
        self.table_path = os.path.normpath(table_path)

        os.makedirs(os.path.dirname(self.table_path), exist_ok=True)

        self.checksums = []

        # ensure table exists
        if not os.path.exists(self.table_path):
            open(self.table_path, mode='w').close()

        # ensure table has a checksums list
        with open(self.table_path, mode='r') as f:
            try:
                json.load(f)
            except json.decoder.JSONDecodeError:
                with open(self.table_path, mode='w') as o:
                    json.dump({'checksums': list()}, o, indent=4)

        # load checksums list
        with open(self.table_path, mode='r') as f:
            table = json.load(f)
            self.checksums = table['checksums']

    @staticmethod
    def _get_crc32(file_path: str) -> str:
        buffer = open(file_path, 'rb').read()
        buffer = (binascii.crc32(buffer) & 0xFFFFFFFF)
        return "{:08X}".format(buffer)

    @staticmethod
    def _find_file(rows: list, file_path: str) -> tuple:
        for i, row in enumerate(rows):
            if row['file_path'] == file_path:
                return i, row
        return None, None

    def compare(self, target_path: str) -> bool:
        """Returns True if the checksum matches"""
        script_path = ''.join([x for x in self.script_paths if x.endswith(target_path)])

        if script_path == '':
            self.log.idxr(f'Found no results for "{target_path}"')
            return False

        table_rows = [x['crc32'] for x in self.checksums if x['file_path'].endswith(target_path)]

        if len(table_rows) == 0:
            self.log.idxr(f'Found no results in checksums for "{target_path}"')
            return False

        # if there is more than one result, the problem was created by the user... right?
        if len(table_rows) > 1:
            self.log.idxr(f'Found more than one result for "{target_path}"')
            return False

        if table_rows[0] == self._get_crc32(script_path):
            return True

        return False

    def write_file(self, script_path: str) -> None:
        crc32 = self._get_crc32(script_path)
        new_row = {'file_path': script_path, 'crc32': crc32}

        os.makedirs(os.path.dirname(self.table_path), exist_ok=True)

        # ensure we can read table and there is a checksums list
        with open(self.table_path, mode='r') as f:
            try:
                json.load(f)
            except json.decoder.JSONDecodeError:
                with open(self.table_path, mode='w') as o:
                    json.dump({'checksums': list()}, o, indent=4)

        with open(self.table_path, mode='r') as f:
            table = json.load(f)

            # check if there's an existing row for the file path
            row_index, row_data = self._find_file(table['checksums'], new_row['file_path'])

            # if there isn't an existing row, add one
            if row_data is None:
                table['checksums'].append(new_row)

            # if there is an existing row, update the crc32
            # this will never run unless Project.validate_script() returns True in PapyrusProject.validate_project()
            # that is, this will run when a previously indexed script has been changed and compiled
            else:
                if row_data['crc32'] != new_row['crc32']:
                    table['checksums'][row_index]['crc32'] = new_row['crc32']

            with open(self.table_path, mode='w') as o:
                json.dump(table, o, indent=4)

    def write(self) -> None:
        results = list()

        for script_path in map(lambda x: os.path.normpath(x), self.script_paths):
            crc32 = self._get_crc32(script_path)
            results.append({'file_path': script_path, 'crc32': crc32})

        os.makedirs(os.path.dirname(self.table_path), exist_ok=True)

        with open(self.table_path, mode='w') as f:
            json.dump({'checksums': results}, f, indent=4)
